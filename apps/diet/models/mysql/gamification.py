from django.db import models
from django.conf import settings

class ChallengeTask(models.Model):
    """健康挑战任务库"""
    title = models.CharField(max_length=64, verbose_name="任务标题")
    desc = models.CharField(max_length=255, verbose_name="任务描述")
    reward_points = models.IntegerField(default=10, verbose_name="奖励积分")
    
    # 任务类型: daily (每日), weekly (每周)
    task_type = models.CharField(max_length=20, default='daily', verbose_name="类型")
    
    # 判定条件 (简单起见用字符串标记，如 'log_breakfast', 'no_sugar')
    condition_code = models.CharField(max_length=64, verbose_name="条件代码")
    
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        db_table = 'diet_challengetask'
        verbose_name = "挑战任务"

    def __str__(self):
        return self.title

class Remedy(models.Model):
    """补救方案库"""
    SCENARIO_CHOICES = (
        ('overeat', '暴食'),
        ('stay_up', '熬夜'),
        ('constipation', '便秘'),
        ('hangover', '宿醉'),
    )
    
    scenario = models.CharField(max_length=32, choices=SCENARIO_CHOICES, db_index=True, verbose_name="场景")
    title = models.CharField(max_length=64, verbose_name="方案标题")
    desc = models.TextField(verbose_name="方案详情")
    order = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = 'diet_remedy'
        verbose_name = "补救方案"
        ordering = ['order']

    def __str__(self):
        return f"[{self.get_scenario_display()}] {self.title}"