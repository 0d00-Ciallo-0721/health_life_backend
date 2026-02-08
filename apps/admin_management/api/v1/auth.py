from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from apps.admin_management.serializers.auth_s import AdminLoginSerializer

class AdminLoginView(APIView):
    """
    后台管理系统登录接口 (JWT)
    """
    # 登录接口必须允许匿名访问
    permission_classes = [AllowAny]
    authentication_classes = [] 

    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        user = data['user']
        tokens = data['tokens']
        roles = data['roles']

        # 返回符合前端规范的数据结构
        return Response({
            'user_info': {
                'id': user.id,
                'username': user.username,
                'nickname': getattr(user, 'nickname', user.username),
                'avatar': user.avatar if hasattr(user, 'avatar') else '',
                'roles': roles
            },
            'token': tokens['access'],
            'refresh_token': tokens['refresh']
        })