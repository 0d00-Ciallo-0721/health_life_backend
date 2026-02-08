from django.db import models

class SystemConfig(models.Model):
    """
    系统动态配置表
    """
    key = models.CharField(max_length=64, unique=True, verbose_name="配置键名", help_text="如: daily_reward_points")
    value = models.TextField(verbose_name="配置值", help_text="如果是JSON或列表，请存为字符串格式")
    description = models.CharField(max_length=255, verbose_name="配置说明")
    is_public = models.BooleanField(default=False, verbose_name="是否公开", help_text="若为True，可被小程序端接口获取")
    
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'sys_config'
        verbose_name = "系统配置"
        ordering = ['key']

    def __str__(self):
        return f"{self.key} = {self.value}"