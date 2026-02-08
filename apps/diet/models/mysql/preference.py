from django.db import models
from django.conf import settings

class UserPreference(models.Model):
    """用户偏好：收藏与拉黑"""
    ACTION_CHOICES = (
        ('like', '收藏/喜欢'),
        ('block', '拉黑/不吃'),
    )
    TYPE_CHOICES = (
        ('recipe', '菜谱'),
        ('restaurant', '餐厅'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    target_id = models.CharField(max_length=64, help_text="MongoDB中的ID")
    target_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'diet_userpreference'
        unique_together = ('user', 'target_id', 'action') 
        indexes = [
            models.Index(fields=['user', 'action']),
        ]