from rest_framework.permissions import BasePermission

class RBACPermission(BasePermission):
    """
    基于 RBAC 模型的动态权限检查
    """
    def has_permission(self, request, view):
        # 1. 超级管理员直接放行
        if request.user.is_superuser:
            return True
            
        # 2. 获取视图定义的权限码 (需要在 ViewSet 中定义 `perms_map`)
        # 例如: perms_map = {'list': 'system:user:list', 'create': 'system:user:add'}
        if not hasattr(view, 'perms_map'):
            return True # 如果没定义权限码，默认放行(或严格模式下禁止)
            
        action = view.action # list, create, update, destroy
        required_perm = view.perms_map.get(action)
        
        if not required_perm:
            return True
            
        # 3. 检查用户是否有该权限码
        # 获取用户所有角色 -> 获取所有菜单 -> 获取 permission_code
        user_perms = request.user.admin_roles.values_list('menus__permission_code', flat=True)
        
        return required_perm in user_perms