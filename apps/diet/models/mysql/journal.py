from django.db import models
from django.conf import settings
from django.utils import timezone

class DailyIntake(models.Model):
    """
    每日摄入日志 (MySQL)
    """
    SOURCE_CHOICES = (
        (1, '自制(菜谱)'),
        (2, '外卖(商家)'),
        (3, '自定义录入'),
    )
    
    MEAL_CHOICES = (
        ('breakfast', '早餐'), 
        ('lunch', '午餐'), 
        ('dinner', '晚餐'), 
        ('snack', '加餐'),
        ('night_snack', '夜宵')
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='intake_logs'
    )
    record_date = models.DateField(auto_now_add=True, db_index=True, verbose_name="记录日期")
    meal_time = models.CharField(
        max_length=20, 
        choices=MEAL_CHOICES,
        default='lunch',
        verbose_name="餐次"
    )
    exact_time = models.TimeField(null=True, blank=True, verbose_name="用餐时间")
    source_type = models.SmallIntegerField(choices=SOURCE_CHOICES, verbose_name="来源类型")
    source_id = models.CharField(max_length=64, null=True, blank=True, help_text="关联 MongoDB 中的 ID")
    food_name = models.CharField(max_length=128, verbose_name="食物名称")
    
    calories = models.IntegerField(default=0, verbose_name="卡路里(kcal)")
    
    # 使用 JSONField 存储碳水、蛋白质、脂肪等详细数据
    macros = models.JSONField(
        default=dict,
        verbose_name="宏量营养素",
        help_text='{"carbohydrates": 12.0, "protein": 8.0, "fat": 10.0}'
    )

    class Meta:
        db_table = 'diet_dailyintake'
        verbose_name = "饮食记录"
        ordering = ['-record_date', 'meal_time', 'id']


class WorkoutRecord(models.Model):
    """
    运动消耗记录 (MySQL)
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workout_records')
    type = models.CharField(max_length=32, verbose_name="运动类型") # running, swimming
    duration = models.IntegerField(verbose_name="时长(分钟)")
    calories_burned = models.IntegerField(verbose_name="消耗热量")
    date = models.DateField(default=timezone.now, verbose_name="日期") 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'diet_workoutrecord'
        verbose_name = "运动记录"
        ordering = ['-date', '-created_at']


class WeightRecord(models.Model):
    """体重记录 (MySQL)"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='weight_records')
    date = models.DateField(default=timezone.now, verbose_name="记录日期")
    weight = models.FloatField(verbose_name="体重(kg)")
    bmi = models.FloatField(verbose_name="BMI", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'diet_weightrecord'
        unique_together = ('user', 'date')
        ordering = ['-date']