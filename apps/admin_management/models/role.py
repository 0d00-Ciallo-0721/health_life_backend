from django.db import models
from django.conf import settings

class AdminRole(models.Model):
    """管理员角色定义"""
    role_name = models.CharField(max_length=64, verbose_name="角色名称")
    role_key = models.CharField(max_length=64, unique=True, verbose_name="角色标识(如 super_admin)")
    
    # 🚀 [新增] 关联用户：一个用户可以有多个角色
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='admin_roles', 
        blank=True, 
        verbose_name="关联用户"
    )
    
    menus = models.ManyToManyField('Menu', blank=True, verbose_name="拥有的菜单权限")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_role'
        verbose_name = "管理角色"