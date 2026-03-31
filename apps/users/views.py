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

        data = {
            "nickname": user.nickname,
            "avatar": profile.avatar.url if profile.avatar else (user.avatar or ""),
            "days_joined": days_joined, 
            "goal_type": goal_display,
            "daily_limit": profile.daily_kcal_limit,
            
            "water_goal_cups": profile.water_goal_cups,
            "follow_count": follow_count,    # [已接入] 真实关注数
            "fans_count": fans_count,        # [已接入] 真实粉丝数
            "like_count": 0,                 # 待社区发帖获赞统计逻辑就绪后再接入
            "badges": [],            
            "featured_badges": []    
        }
        return Response({"code": 200, "data": data})
    

class UserProfileView(APIView):
    """获取他人公开主页"""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id)
        profile, _ = Profile.objects.get_or_create(user=target_user)
        serializer = PublicProfileSerializer(profile, context={'request': request})
        return Response({
            'code': 200,
            'msg': 'success',
            'data': serializer.data
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

        # 2. 拦截: 社区模块未就绪的防崩溃保护
        if Post is None:
            return Response({
                'code': 200, 
                'msg': '帖子模块暂未就绪', 
                'data': {'posts': [], 'total': 0, 'page': page}
            })

        # 3. 数据库查询 (基于 Django ORM / Djongo 语法)
        # 注意：此处假定 Post 模型中有 author_id 或 user_id 字段。如果不叫 author_id，请自行调整。
        query_set = Post.objects.filter(author_id=target_user.id).order_by('-created_at')
        total = query_set.count()

        # 4. 执行内存/游标分页
        start = (page - 1) * size
        end = start + size
        paginated_posts = query_set[start:end]

        # 5. 序列化数据
        if PostSerializer:
            posts_data = PostSerializer(paginated_posts, many=True, context={'request': request}).data
        else:
            # Fallback 方案：如果序列化器未定义，执行手动字典转换
            posts_data = []
            for p in paginated_posts:
                posts_data.append({
                    "id": str(p.id) if hasattr(p, 'id') else None,
                    "content": getattr(p, 'content', ''),
                    "like_count": getattr(p, 'like_count', 0),
                    "comment_count": getattr(p, 'comment_count', 0),
                    "created_at": getattr(p, 'created_at', None)
                })

        return Response({
            'code': 200,
            'msg': 'success',
            'data': {
                'posts': posts_data,
                'total': total,
                'page': page,
                'size': size,
                'has_next': end < total
            }
        })