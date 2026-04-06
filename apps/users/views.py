from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny 
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
import time

from apps.common.exceptions import BusinessException
from apps.common.utils import WeChatService
from .models import User, Profile
from .serializers_users import PublicProfileSerializer
from .services import UserFollowService

# ==================== 跨模块依赖导入 (带容错机制) ====================
try:
    from apps.diet.models.mongo.community import Post
except ImportError:
    Post = None

try:
    from apps.diet.serializers.community import PostSerializer
except ImportError:
    PostSerializer = None


class WeChatLoginView(APIView):
    permission_classes = [AllowAny] 

    def post(self, request):
        code = request.data.get('code')
        if not code:
            return Response({'code': 400, 'msg': 'missing code'}, status=400)
        
        try:
            wechat_data = WeChatService.get_openid(code)
        except Exception as e:
            return Response({'code': 400, 'msg': str(e)}, status=400)

        openid = wechat_data.get('openid')
        if not openid:
            return Response({'code': 400, 'msg': 'openid 获取失败'}, status=400)

        with transaction.atomic():
            user, created = User.objects.get_or_create(
                openid=openid,
                defaults={'username': f"wx_{openid[:8]}_{int(time.time())}"}
            )
            if not hasattr(user, 'profile'):
                Profile.objects.create(user=user)
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'code': 200,
            'msg': 'success',
            'data': {
                'token': str(refresh.access_token),
                'is_new_user': created
            }
        })


class UserMetaView(APIView):
    """获取用户元数据"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile, _ = Profile.objects.get_or_create(user=user)

        # 1. 计算加入天数
        days_joined = (timezone.now().date() - user.date_joined.date()).days + 1

        # 2. 转换 goal_type 为中文
        goal_map = {'lose': '减脂', 'maintain': '维持', 'gain': '增肌'}
        goal_display = goal_map.get(profile.goal_type, '未知')

        # 3. 统计关注与粉丝数 (采用局部导入防依赖循环，同时兼容关联反向查询)
        try:
            from .models import UserFollow
            follow_count = UserFollow.objects.filter(follower=user).count()
            fans_count = UserFollow.objects.filter(following=user).count()
        except ImportError:
            # Fallback 容错: 尝试通过常见的 Django ORM 反向关系(related_name)获取
            follow_count = user.following.count() if hasattr(user, 'following') else 0
            fans_count = user.followers.count() if hasattr(user, 'followers') else 0

        # 4. 获取徽章和代表徽章
        badges_data = []
        featured_badges_data = []
        like_count = 0
        try:
            from apps.diet.domains.gamification.services import GamificationService
            # badges: 只返回已解锁的徽章 summary
            all_achievements = GamificationService.get_merged_achievements(user)
            for a in all_achievements:
                if a.get('unlocked'):
                    badges_data.append({
                        "id": a["id"],
                        "name": a["name"],
                        "icon": a["icon"]
                    })
            
            featured_badges_data = GamificationService.get_user_featured_badges(user.id)
            from apps.diet.domains.community.services import CommunityService
            community_profile = CommunityService.get_user_profile(user.id, user.id)
            like_count = community_profile.get("like_count", 0) if community_profile else 0
        except ImportError:
            pass

        data = {
            "nickname": user.nickname,
            "avatar": profile.avatar.url if profile.avatar else (user.avatar or ""),
            "days_joined": days_joined, 
            "goal_type": goal_display,
            "daily_limit": profile.daily_kcal_limit,
            
            "water_goal_cups": profile.water_goal_cups,
            "water_goal_ml": profile.water_goal_ml,
            "follow_count": follow_count,    # [已接入] 真实关注数
            "fans_count": fans_count,        # [已接入] 真实粉丝数
            "like_count": like_count,        # [已接入] 从 MongoDB 真实聚合而来
            "badges": badges_data,
            "featured_badges": featured_badges_data
        }
        return Response({"code": 200, "data": data})
    

class UserProfileView(APIView):
    """获取他人公开主页"""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        # 统一使用 CommunityService 以确保粉丝数、获赞数和代表勋章等字段存在
        from apps.diet.domains.community.services import CommunityService
        data = CommunityService.get_user_profile(user_id, request.user.id)
        if not data:
            return Response({"code": 404, "msg": "用户不存在"}, status=404)
        return Response({
            'code': 200,
            'msg': 'success',
            'data': data
        })


class UserFollowView(APIView):
    """关注与取消关注"""
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        try:
            UserFollowService.follow(request.user, user_id)
            return Response({'code': 200, 'msg': '关注成功', 'data': None})
        except BusinessException as e:
            return Response({'code': 400, 'msg': str(e)})

    def delete(self, request, user_id):
        try:
            UserFollowService.unfollow(request.user, user_id)
            return Response({'code': 200, 'msg': '已取消关注', 'data': None})
        except BusinessException as e:
            return Response({'code': 400, 'msg': str(e)})


# ==================== 本次完善的核心业务逻辑 ====================
class UserPostsView(APIView):
    """
    获取用户的动态列表 (已对接真实 Post 模型 + 分页)
    GET /user/{userId}/posts/?page=1&size=10
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id)
        
        # 1. 获取分页参数
        try:
            page = int(request.query_params.get('page', 1))
            size = int(request.query_params.get('size', 10))
        except ValueError:
            page, size = 1, 10

        # 2. 从 CommunityService 获取该用户的动态
        from apps.diet.domains.community.services import CommunityService
        posts_data = CommunityService.get_feed_list(page=page, page_size=size, current_user_id=request.user.id, query_user_id=target_user.id)
        
        # 3. 计算 total 等
        # 注意: CommunityService 目前未返回 total, 这里仅进行近似补齐或可使用真实 count
        try:
            from apps.diet.models.mongo.community import CommunityFeed
            total = CommunityFeed.objects.filter(user_id=target_user.id).count()
        except Exception:
            total = len(posts_data) + (page-1)*size
        
        has_next = len(posts_data) == size

        return Response({
            'code': 200,
            'msg': 'success',
            'data': {
                'list': posts_data,
                'total': total,
                'page': page,
                'size': size,
                'has_next': has_next
            }
        })