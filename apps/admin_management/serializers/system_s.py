from django.utils.text import slugify
from rest_framework import serializers

from apps.admin_management.models import AdminRole, Menu
from apps.admin_management.models.audit import AuditLog
from apps.admin_management.models.config import SystemConfig
from apps.admin_management.models.notification import Notification


class MenuTreeSerializer(serializers.ModelSerializer):
    """
    递归菜单树序列化器。
    """

    children = serializers.SerializerMethodField()

    class Meta:
        model = Menu
        fields = ['id', 'name', 'icon', 'path', 'component', 'permission_code', 'sort_order', 'children', 'parent']

    def get_children(self, obj):
        children = obj.children.all().order_by('sort_order')
        if children.exists():
            return MenuTreeSerializer(children, many=True).data
        return []


class AdminRoleSerializer(serializers.ModelSerializer):
    """
    角色管理序列化器，兼容前端的 `name/description` 字段。
    """

    name = serializers.CharField(source='role_name')
    description = serializers.CharField(source='role_key', required=False, allow_blank=True)
    menus = serializers.PrimaryKeyRelatedField(many=True, queryset=Menu.objects.all(), required=False)

    class Meta:
        model = AdminRole
        fields = ['id', 'name', 'description', 'role_name', 'role_key', 'menus', 'created_at']
        read_only_fields = ['created_at', 'role_name', 'role_key']

    def _build_role_key(self, name, description):
        raw = description or name or 'role'
        normalized = slugify(str(raw), allow_unicode=True).replace('-', '_')[:64]
        return normalized or 'role'

    def create(self, validated_data):
        role_name = validated_data.pop('role_name')
        role_key = validated_data.pop('role_key', '')
        validated_data['role_name'] = role_name
        validated_data['role_key'] = self._build_role_key(role_name, role_key)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        role_name = validated_data.pop('role_name', instance.role_name)
        role_key = validated_data.pop('role_key', instance.role_key)
        validated_data['role_name'] = role_name
        validated_data['role_key'] = self._build_role_key(role_name, role_key)
        return super().update(instance, validated_data)


class AuditLogSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    request_path = serializers.CharField(source='path', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'operator', 'operator_name', 'method', 'path', 'request_path', 'module', 'ip_address', 'body', 'response_code', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    target_username = serializers.CharField(source='target_user.username', read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    type = serializers.CharField(required=False)
    message_type = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Notification
        fields = ['id', 'title', 'content', 'type', 'message_type', 'target_user', 'target_username', 'is_read', 'created_at']

    def _normalize_type(self, attrs):
        incoming = attrs.pop('message_type', None)
        if incoming is None:
            incoming = attrs.pop('type', None)

        if incoming == 'public':
            attrs['type'] = 'system'
        elif incoming:
            attrs['type'] = incoming
        return attrs

    def validate(self, attrs):
        return self._normalize_type(attrs)

    def create(self, validated_data):
        validated_data = self._normalize_type(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._normalize_type(validated_data)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['type'] = 'public' if instance.type == 'system' else instance.type
        return data


class SystemConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemConfig
        fields = '__all__'
        read_only_fields = ['updated_at']
