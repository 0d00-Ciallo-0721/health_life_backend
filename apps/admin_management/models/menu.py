from django.db import models

class Menu(models.Model):
    """后台管理系统动态菜单"""
    name = models.CharField(max_length=64, verbose_name="菜单名称")
    icon = models.CharField(max_length=64, null=True, blank=True, verbose_name="图标样式")
    path = models.CharField(max_length=255, verbose_name="前端路由路径")
    component = models.CharField(max_length=255, verbose_name="前端组件路径")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    permission_code = models.CharField(max_length=128, unique=True, verbose_name="权限标识码")

    class Meta:
        db_table = 'admin_menu'
        verbose_name = "系统菜单"
        ordering = ['sort_order']