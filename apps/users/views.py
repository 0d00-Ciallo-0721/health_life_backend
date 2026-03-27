from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Profile
from apps.common.utils import WeChatService
from django.db import transaction
from django.utils import timezone
import datetime
from rest_framework.permissions import IsAuthenticated, AllowAny 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Profile
import time
from django.shortcuts import get_object_or_404
from apps.common.exceptions import BusinessException
from .serializers_users import PublicProfileSerializer
from .services import UserFollowService



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
                defaults={'username': f"wx_{openid[:8]}_{int(time.time())}"} # 加时间戳防冲突
            )
            # 兼容旧逻辑：如果之前没 Profile，这里补一个
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

# [新增] 用户元数据接口
class UserMetaView(APIView):
    """
    获取用户元数据 (v3.1 增强版)
    GET /user/meta/
    """
    permission_classes = [IsAuthenticated]

    # [修改] 更新 UserMetaView 中的 get 方法
    def get(self, request):
        user = request.user
        profile, _ = Profile.objects.get_or_create(user=user)

        # 1. 计算加入天数
        days_joined = (timezone.now().date() - user.date_joined.date()).days + 1

        # 2. 转换 goal_type 为中文
        goal_map = {'lose': '减脂', 'maintain': '维持', 'gain': '增肌'}
        goal_display = goal_map.get(profile.goal_type, '未知')

        data = {
            "nickname": user.nickname,
            "avatar": profile.avatar.url if profile.avatar else (user.avatar or ""),
            "days_joined": days_joined, 
            "goal_type": goal_display,
            "daily_limit": profile.daily_kcal_limit,
            
            # [新增] 扩展返回字段，确保多端视图数据一致性
            "water_goal_cups": profile.water_goal_cups,
            "follow_count": 0,       # 待阶段四接入逻辑
            "fans_count": 0,         # 待阶段四接入逻辑
            "like_count": 0,         # 待阶段四接入逻辑
            "badges": [],            # 待阶段二接入逻辑
            "featured_badges": []    # 待阶段二接入逻辑
        }
        return Response({"code": 200, "data": data})
    


# [新增] 他人公开主页视图
class UserProfileView(APIView):
    """
    获取他人公开主页
    GET /user/{userId}/profile/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id)
        # 确保能获取到目标的 Profile，如果不存则获取并创建默认态
        profile, _ = Profile.objects.get_or_create(user=target_user)
        
        # 传递 request 进 context，是为了让 Serializer 可以判断 is_following
        serializer = PublicProfileSerializer(profile, context={'request': request})
        return Response({
            'code': 200,
            'msg': 'success',
            'data': serializer.data
        })

# [新增] 关注与取消关注视图
class UserFollowView(APIView):
    """
    关注与取消关注
    POST /user/{userId}/follow/
    DELETE /user/{userId}/follow/
    """
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