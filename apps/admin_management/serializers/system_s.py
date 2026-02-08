from rest_framework import serializers
from apps.admin_management.models import Menu, AdminRole
from apps.admin_management.models.audit import AuditLog
from apps.admin_management.models.notification import Notification
from apps.admin_management.models.config import SystemConfig

# --- 1. 菜单树形序列化器 (核心) ---
class MenuTreeSerializer(serializers.ModelSerializer):
    """
    递归序列化器，返回 children 嵌套结构
    """
    children = serializers.SerializerMethodField()

    class Meta:
        model = Menu
        fields = ['id', 'name', 'icon', 'path', 'component', 'permission_code', 'sort_order', 'children', 'parent']

    def get_children(self, obj):
        # 查找当前菜单的子菜单
        children = obj.children.all().order_by('sort_order')
        if children.exists():
            # 递归调用自身
            return MenuTreeSerializer(children, many=True).data
        return []

# --- 2. 角色管理序列化器 ---
class AdminRoleSerializer(serializers.ModelSerializer):
    """
    角色管理序列化器
    """
    # 显示关联的菜单ID列表，用于前端树形勾选回显
    menus = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Menu.objects.all(),
        required=False
    )

    class Meta:
        model = AdminRole
        fields = ['id', 'role_name', 'role_key', 'menus', 'created_at']
        read_only_fields = ['created_at']

# --- 3. 审计日志序列化器 ---
class AuditLogSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")

    class Meta:
        model = AuditLog
        fields = '__all__'

# --- 4. 通知序列化器 ---
class NotificationSerializer(serializers.ModelSerializer):
    target_username = serializers.CharField(source='target_user.username', read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'title', 'content', 'type', 'target_user', 'target_username', 'is_read', 'created_at']

# --- 5. 系统配置序列化器 ---
class SystemConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemConfig
        fields = '__all__'
        read_only_fields = ['updated_at']