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
    


# [新增] 用户挑战进度表
class UserChallengeProgress(models.Model):
    STATUS_CHOICES = (
        ('pending', '进行中'),
        ('completed', '已完成'),
        ('abandoned', '已放弃'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='challenge_progresses')
    challenge = models.ForeignKey(ChallengeTask, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="状态")
    progress = models.IntegerField(default=0, verbose_name="当前进度")
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="加入时间")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")

    class Meta:
        db_table = 'diet_userchallengeprogress'
        verbose_name = "用户挑战进度"

# [新增] 用户补救计划记录表
class UserRemedyPlan(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='remedy_plans')
    remedy = models.ForeignKey(Remedy, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="添加时间")
    is_completed = models.BooleanField(default=False, verbose_name="是否完成")

    class Meta:
        db_table = 'diet_userremedyplan'
        verbose_name = "用户补救计划"

# [新增] 成就系统字典表
class Achievement(models.Model):
    code = models.CharField(max_length=64, unique=True, verbose_name="成就代码")
    title = models.CharField(max_length=64, verbose_name="成就名称")
    desc = models.CharField(max_length=255, verbose_name="成就描述")
    icon = models.CharField(max_length=255, blank=True, null=True, verbose_name="图标URL")

    class Meta:
        db_table = 'diet_achievement'
        verbose_name = "成就字典"

# [新增] 用户成就关联表
class UserAchievement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True, verbose_name="解锁时间")

    class Meta:
        db_table = 'diet_userachievement'
        verbose_name = "用户成就"    