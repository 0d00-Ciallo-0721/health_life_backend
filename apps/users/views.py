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

    def get(self, request):
        user = request.user
        profile, _ = Profile.objects.get_or_create(user=user)

        # 1. 计算加入天数
        # 注意处理时区问题，这里简化为日期差
        days_joined = (timezone.now().date() - user.date_joined.date()).days + 1

        # 2. 转换 goal_type 为中文
        goal_map = {'lose': '减脂', 'maintain': '维持', 'gain': '增肌'}
        goal_display = goal_map.get(profile.goal_type, '未知')

        data = {
            "nickname": user.nickname,
            "avatar": profile.avatar.url if profile.avatar else (user.avatar or ""),
            "days_joined": days_joined, # [v3.1 确认]
            "goal_type": goal_display,
            "daily_limit": profile.daily_kcal_limit
        }
        return Response({"code": 200, "data": data})