from django.db import models
from django.conf import settings

class Notification(models.Model):
    """
    系统通知与消息
    """
    TYPE_CHOICES = (
        ('system', '全员公告'),
        ('private', '私信通知'), # 用于审核结果等
    )
    
    title = models.CharField(max_length=128, verbose_name="标题")
    content = models.TextField(verbose_name="内容")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='private', verbose_name="消息类型")
    
    # 如果是 private，必须指定 target_user；如果是 system，则为 null (表示所有人可见)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='notifications',
        verbose_name="接收用户"
    )
    
    is_read = models.BooleanField(default=False, verbose_name="是否已读")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="发送时间")

    class Meta:
        db_table = 'sys_notification'
        verbose_name = "消息通知"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_type_display()}] {self.title}"