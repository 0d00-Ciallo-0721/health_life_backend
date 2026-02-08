from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    """
    操作审计日志
    仅记录写操作 (POST/PUT/DELETE)，不记录 GET 查询
    """
    METHOD_CHOICES = (
        ('POST', '新增'),
        ('PUT', '修改'),
        ('PATCH', '部分修改'),
        ('DELETE', '删除'),
    )

    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="操作人"
    )
    operator_name = models.CharField(max_length=64, verbose_name="操作人快照", help_text="防止用户删除后无法追溯")
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, verbose_name="请求方法")
    path = models.CharField(max_length=255, verbose_name="请求路径")
    module = models.CharField(max_length=64, verbose_name="功能模块", null=True, blank=True)
    ip_address = models.GenericIPAddressField(verbose_name="IP地址", null=True)
    
    # 使用 JSONField 存储请求参数，自动处理 JSON 序列化
    body = models.JSONField(verbose_name="请求参数", default=dict)
    
    response_code = models.IntegerField(verbose_name="响应状态码", default=200)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="操作时间")

    class Meta:
        db_table = 'admin_audit_log'
        verbose_name = "操作日志"
        ordering = ['-created_at']