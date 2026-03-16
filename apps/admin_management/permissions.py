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
    

class IsGameAdmin(RBACPermission):
    """游戏化管理专有权限判定"""
    def has_permission(self, request, view):
        # 1. 超级管理员放行
        if request.user.is_superuser:
            return True
        
        # 2. 如果视图配置了具体的 perms_map，优先走严格匹配校验
        if hasattr(view, 'perms_map') and super().has_permission(request, view):
            return True
            
        # 3. 宽泛校验：只要角色拥有 'game:' 域的权限，即可访问游戏化模块通用接口
        user_perms = request.user.admin_roles.values_list('menus__permission_code', flat=True)
        return any(perm and perm.startswith('game:') for perm in user_perms)


class IsCommunityAdmin(RBACPermission):
    """社区与社交审核专有权限判定"""
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
            
        if hasattr(view, 'perms_map') and super().has_permission(request, view):
            return True
            
        user_perms = request.user.admin_roles.values_list('menus__permission_code', flat=True)
        return any(perm and perm.startswith('social:') for perm in user_perms)


class IsJournalAdmin(RBACPermission):
    """日志与健康数据专有权限判定"""
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
            
        if hasattr(view, 'perms_map') and super().has_permission(request, view):
            return True
            
        user_perms = request.user.admin_roles.values_list('menus__permission_code', flat=True)
        return any(perm and perm.startswith('health:') for perm in user_perms)    