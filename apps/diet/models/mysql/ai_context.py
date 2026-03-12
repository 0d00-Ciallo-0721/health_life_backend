from django.db import models
from django.conf import settings

class AIChatContext(models.Model):
    """持久化 AI 多轮对话上下文"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_chats')
    role = models.CharField(max_length=20, choices=[('user', '用户'), ('assistant', 'AI')], verbose_name="角色")
    content = models.TextField(verbose_name="对话内容")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'diet_aichatcontext'
        verbose_name = "AI 对话历史"
        ordering = ['created_at']  # 保证按时间顺序拼接