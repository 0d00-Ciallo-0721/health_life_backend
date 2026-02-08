from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()

class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        # 1. Django 标准认证
        user = authenticate(username=username, password=password)

        if not user:
            raise serializers.ValidationError("用户名或密码错误")

        # 2. 权限隔离：非员工禁止登录后台
        if not user.is_staff:
            raise serializers.ValidationError("该账号无权访问管理后台")

        if not user.is_active:
            raise serializers.ValidationError("账号已被禁用")

        # 3. 生成 JWT
        refresh = RefreshToken.for_user(user)
        
        # 4. 获取用户的所有角色标识 (如 ['super_admin', 'editor'])
        roles = list(user.admin_roles.values_list('role_key', flat=True))
        
        # 如果是超级管理员，自动追加标识
        if user.is_superuser and 'super_admin' not in roles:
            roles.append('super_admin')

        return {
            'user': user,
            'roles': roles,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }