from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny 
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
import time
from rest_framework_simplejwt.exceptions import TokenError
from apps.common.exceptions import BusinessException
from apps.common.utils import WeChatService
from .models import User, Profile
from .serializers_users import PublicProfileSerializer
from .services import UserFollowService
from rest_framework.parsers import MultiPartParser, JSONParser
from django.core.files.storage import default_storage
import os
import uuid

# ==================== 跨模块依赖导入 (带容错机制) ====================
try:
    from apps.diet.models.mongo.community import Post
except ImportError:
    Post = None

try:
    from apps.diet.serializers.community import PostSerializer
except ImportError:
    PostSerializer = None


class LogoutView(APIView):
    """后端彻底退出登录 (作废 Refresh Token)"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # 接收前端传来的 refresh_token
            refresh_token = request.data.get("refresh_token")
            if not refresh_token:
                return Response({"code": 400, "msg": "缺少 refresh_token 参数"}, status=400)
            
            # 将该 token 加入黑名单
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({"code": 200, "msg": "退出登录成功"})
        except TokenError:
            return Response({"code": 400, "msg": "Token 无效或已过期"}, status=400)
        except Exception as e:
            return Response({"code": 500, "msg": f"退出失败: {str(e)}"}, status=500)


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
                'access_token': str(refresh.access_token), # [修改] 明确字段名
                'refresh_token': str(refresh),             # [新增] 返回 refresh_token 供前端刷新和退出使用
                'is_new_user': created,
                'user_id': user.id                         # [新增] 返回 user_id
            }
        })

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

    def get(self, request, userId):
        # 统一使用 CommunityService 以确保粉丝数、获赞数和代表勋章等字段存在
        from apps.diet.domains.community.services import CommunityService
        data = CommunityService.get_user_profile(userId, request.user.id)
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

    def get(self, request, userId):
        target_user = get_object_or_404(User, id=userId)
        
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
    
class ProfileUpdateView(APIView):
    """
    用户档案查询与更新
    GET /diet/profile/ - 获取档案及社交统计
    POST /diet/profile/ - 更新头像 (multipart/form-data)
    PATCH /diet/profile/ - 更新文本字段 (JSON)
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, JSONParser]

    def get(self, request):
        profile, created = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, context={'request': request})
        return Response({"code": 200, "data": serializer.data})

    def post(self, request):
        """兼容微信小程序 wx.uploadFile 上传头像"""
        avatar_file = request.FILES.get('avatar')
        if not avatar_file:
            return Response({"code": 400, "msg": "未检测到上传文件字段: avatar"}, status=400)

        # 1. 生成唯一文件名并存储
        ext = os.path.splitext(avatar_file.name)[1]
        file_path = f"avatars/{request.user.id}_{uuid.uuid4().hex}{ext}"
        saved_path = default_storage.save(file_path, avatar_file)
        
        # 2. 更新数据库
        profile, _ = Profile.objects.get_or_create(user=request.user)
        # 如果 Profile 的 avatar 是 FileField
        profile.avatar = saved_path
        profile.save()
        
        # 3. 实时更新 User 表冗余字段 (可选)
        request.user.avatar = default_storage.url(saved_path)
        request.user.save()

        # 返回最新档案数据
        serializer = ProfileSerializer(profile, context={'request': request})
        return Response({
            "code": 200, 
            "msg": "头像更新成功",
            "data": serializer.data
        })

    def patch(self, request):
        """更新文本档案字段"""
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"code": 200, "data": serializer.data})
        return Response({"code": 400, "msg": serializer.errors}, status=400)
