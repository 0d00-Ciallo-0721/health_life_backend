from rest_framework.permissions import BasePermission


class RBACPermission(BasePermission):
    """
    基于 RBAC 模型的动态权限检查。
    """

    def _get_required_perm(self, request, view):
        perms_map = getattr(view, "perms_map", None)
        if not perms_map:
            return None

        action = getattr(view, "action", None)
        if action:
            return perms_map.get(action)

        return perms_map.get(request.method.lower())

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True

        if not hasattr(view, "perms_map"):
            return True

        required_perm = self._get_required_perm(request, view)
        if not required_perm:
            return False

        user_perms = request.user.admin_roles.values_list("menus__permission_code", flat=True)
        return required_perm in user_perms


class IsGameAdmin(RBACPermission):
    """游戏化管理专属权限判定"""

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True

        required_perm = self._get_required_perm(request, view)
        if required_perm and super().has_permission(request, view):
            return True

        user_perms = request.user.admin_roles.values_list("menus__permission_code", flat=True)
        if required_perm:
            return any(perm and perm.startswith("game:") for perm in user_perms)
        if hasattr(view, "perms_map"):
            return False
        return any(perm and perm.startswith("game:") for perm in user_perms)


class IsCommunityAdmin(RBACPermission):
    """社区与社交审核专属权限判定"""

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True

        required_perm = self._get_required_perm(request, view)
        if required_perm and super().has_permission(request, view):
            return True

        user_perms = request.user.admin_roles.values_list("menus__permission_code", flat=True)
        if required_perm:
            return any(perm and perm.startswith("social:") for perm in user_perms)
        if hasattr(view, "perms_map"):
            return False
        return any(perm and perm.startswith("social:") for perm in user_perms)


class IsJournalAdmin(RBACPermission):
    """日志与健康数据专属权限判定"""

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True

        required_perm = self._get_required_perm(request, view)
        if required_perm and super().has_permission(request, view):
            return True

        user_perms = request.user.admin_roles.values_list("menus__permission_code", flat=True)
        if required_perm:
            return any(perm and perm.startswith("health:") for perm in user_perms)
        if hasattr(view, "perms_map"):
            return False
        return any(perm and perm.startswith("health:") for perm in user_perms)
