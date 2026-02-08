from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from apps.admin_management.models import Menu
from apps.admin_management.serializers.system_s import MenuTreeSerializer
from apps.admin_management.permissions import RBACPermission
from apps.admin_management.models import AdminRole
from apps.admin_management.serializers.system_s import AdminRoleSerializer
from apps.admin_management.models.audit import AuditLog
from apps.admin_management.serializers.system_s import AuditLogSerializer
from apps.admin_management.serializers.system_s import (
    MenuTreeSerializer, 
    AdminRoleSerializer, 
    AuditLogSerializer  # 👈 必须与 system_s.py 中的类名一致
)
from apps.admin_management.models.notification import Notification
from apps.admin_management.serializers.system_s import NotificationSerializer
from apps.admin_management.models.config import SystemConfig
from apps.admin_management.serializers.system_s import SystemConfigSerializer


class CurrentUserMenuView(APIView):
    """
    获取当前登录用户的动态路由菜单
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        user = request.user
        
        # 1. 判断是否为超级管理员 (拥有所有权限)
        # 这里我们在 Login 接口里硬编码了 super_admin 标识，或者直接用 Django 的 is_superuser
        if user.is_superuser:
            # 获取所有根菜单 (parent=None)
            root_menus = Menu.objects.filter(parent=None).order_by('sort_order')
        else:
            # 2. 普通管理员：获取角色关联的菜单
            # 使用 distinct() 去重
            user_menus = Menu.objects.filter(
                adminrole__users=user
            ).distinct()
            
            # 过滤出根菜单，序列化器会自动递归找子节点
            # 注意：这里逻辑简化了，严谨逻辑需要先拿到所有ID构建内存树，防止子菜单有权但父菜单无权导致断层
            # 简单起见，假设分配权限时父子必选
            root_menus = user_menus.filter(parent=None).order_by('sort_order')

        serializer = MenuTreeSerializer(root_menus, many=True)
        
        return Response({
            "code": 200,
            "msg": "success",
            "data": serializer.data
        })
    


class MenuViewSet(viewsets.ModelViewSet):
    """
    菜单管理接口 (增删改查)
    """
    # 1. 基础查询集保留 all()，确保 retrieve/update/delete 能找到子菜单
    queryset = Menu.objects.all().order_by('sort_order')
    serializer_class = MenuTreeSerializer
    permission_classes = [IsAuthenticated, IsAdminUser, RBACPermission] 
    
    perms_map = {
        'list': 'system:menu:list',
        'create': 'system:menu:add',
        'update': 'system:menu:edit',
        'destroy': 'system:menu:delete'
    }

    # 🚀 [关键修改] 重写 list 方法，只返回根菜单
    def list(self, request, *args, **kwargs):
        # 过滤出 parent 为空的菜单 (即顶级菜单)
        # MenuTreeSerializer 会自动递归加载 children，所以不用担心丢失子菜单
        queryset = self.get_queryset().filter(parent__isnull=True)
        
        serializer = self.get_serializer(queryset, many=True)
        # 这里的 Response 结构会被 Render 包装为 {code:200, data: [...]}
        return Response(serializer.data) 


class RoleViewSet(viewsets.ModelViewSet):
    """
    角色管理接口
    """
    queryset = AdminRole.objects.all().order_by('-created_at')
    serializer_class = AdminRoleSerializer
    permission_classes = [IsAuthenticated, IsAdminUser, RBACPermission] # 🔒 挂载权限锁
    
    # 🔑 定义权限映射 (与数据库中 init_menus.py 初始化的 permission_code 对应)
    perms_map = {
        'list': 'system:role:list',      # 查看角色列表
        'create': 'system:role:add',     # 新增角色
        'update': 'system:role:edit',    # 修改角色
        'destroy': 'system:role:delete'  # 删除角色
    }




class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    操作日志查询 (只读)
    """
    queryset = AuditLog.objects.all().order_by('-created_at')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdminUser, RBACPermission]
    
    perms_map = {
        'list': 'system:log:list',
        'retrieve': 'system:log:list'
    }

    def get_queryset(self):
        qs = super().get_queryset()
        # 筛选：操作人
        operator = self.request.query_params.get('operator', '')
        if operator:
            qs = qs.filter(operator_name__icontains=operator)
        
        # 筛选：模块
        module = self.request.query_params.get('module', '')
        if module:
            qs = qs.filter(module__icontains=module)
            
        return qs
    

class NotificationViewSet(viewsets.ModelViewSet):
    """
    消息通知管理 (管理员侧)
    """
    queryset = Notification.objects.all().order_by('-created_at')
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, IsAdminUser, RBACPermission]
    
    perms_map = {
        'list': 'system:notify:list',
        'create': 'system:notify:add',     # 发布公告
        'destroy': 'system:notify:delete', # 删除记录
    }

    def perform_create(self, serializer):
        # 管理员手动创建时，通常是发全员公告，或者是指定用户的私信
        # 这里不需要特殊逻辑，直接保存
        serializer.save()    



class SystemConfigViewSet(viewsets.ModelViewSet):
    """
    系统参数配置
    """
    queryset = SystemConfig.objects.all().order_by('key')
    serializer_class = SystemConfigSerializer
    permission_classes = [IsAuthenticated, IsAdminUser, RBACPermission]
    
    perms_map = {
        'list': 'system:config:list',
        'create': 'system:config:add',
        'update': 'system:config:edit',
        'partial_update': 'system:config:edit',
        'destroy': 'system:config:delete',
    }        