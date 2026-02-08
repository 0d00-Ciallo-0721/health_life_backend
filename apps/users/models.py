from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings # ✅ 新增引入
from django.utils.translation import gettext_lazy as _
import math
class User(AbstractUser):
    """
    自定义用户模型，支持微信登录
    """
    openid = models.CharField(
        max_length=64, 
        unique=True, 
        db_index=True, 
        verbose_name='微信OpenID',
        null=True, 
        blank=True
    )
    
    avatar = models.CharField(max_length=255, null=True, blank=True, verbose_name='头像URL')
    nickname = models.CharField(max_length=64, null=True, blank=True, verbose_name='昵称')
    phone = models.CharField(max_length=11, null=True, blank=True)

    class Meta:
        db_table = 'users_user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username

# ✅ Profile 类完全迁移至此
class Profile(models.Model):
    """
    用户画像与身体数据 (MySQL)
    存储需要强关联和事务支持的身体基本信息
    """

    # [新增] 目标类型枚举
    GOAL_CHOICES = (
        ('lose', '减脂'),
        ('maintain', '保持'),
        ('gain', '增肌'),
    )

    # ✅ [修复] 保留唯一且正确的定义
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    gender = models.SmallIntegerField(
        choices=((0, '未知'), (1, '男'), (2, '女')), 
        default=0,
        verbose_name="性别"
    )
    
    height = models.FloatField(help_text="cm", default=170)
    weight = models.FloatField(help_text="kg", default=65)
    age = models.IntegerField(default=25)
    activity_level = models.FloatField(default=1.2, help_text="1.2~1.9")
    
    # [新增] 目标设定
    goal_type = models.CharField(
        max_length=20, 
        choices=GOAL_CHOICES, 
        default='maintain',
        verbose_name="健康目标"
    )

    diet_tags = models.JSONField(default=list, blank=True, verbose_name="饮食偏好标签")
    allergens = models.JSONField(default=list, blank=True, verbose_name="过敏源")
    
    daily_kcal_limit = models.IntegerField(default=2000, verbose_name="每日推荐摄入")
    
    # [新增] 目标体重
    target_weight = models.FloatField(null=True, blank=True, verbose_name="目标体重(kg)")
    
    # [新增] 个性签名
    signature = models.TextField(null=True, blank=True, verbose_name="个性签名")
    
    # [新增] 头像 (存储路径: media/avatars/YYYY/MM/)
    avatar = models.ImageField(upload_to='avatars/%Y/%m/', null=True, blank=True, verbose_name="头像")
    
    # [新增] 基础代谢率 (BMR) - 仅做记录，不参与核心逻辑，方便前端展示
    bmr = models.IntegerField(default=0, verbose_name="基础代谢率")    
    
    class Meta:
        db_table = 'users_profile'
        verbose_name = '身体档案'


    def calculate_and_save_daily_limit(self):
        """
        核心算法：Mifflin-St Jeor 公式计算 BMR 和 TDEE
        """
        if not all([self.weight, self.height, self.age, self.gender]):
            return

        # 1. 计算 BMR (Mifflin-St Jeor 公式)
        # 男性: 10 * weight(kg) + 6.25 * height(cm) - 5 * age(y) + 5
        # 女性: 10 * weight(kg) + 6.25 * height(cm) - 5 * age(y) - 161
        base_bmr = (10 * self.weight) + (6.25 * self.height) - (5 * self.age)
        if self.gender == 1:  # 男性
            base_bmr += 5
        else:  # 女性
            base_bmr -= 161
            
        self.bmr = int(base_bmr)

        # 2. 计算 TDEE (Total Daily Energy Expenditure)
        tdee = base_bmr * self.activity_level

        # 3. 根据目标调整
        if self.goal_type == 'lose':
            # 减脂：制造 15%~20% 热量缺口，这里取 0.85
            target_cal = tdee * 0.85
        elif self.goal_type == 'gain':
            # 增肌：增加 10% 热量盈余
            target_cal = tdee * 1.1
        else:
            # 保持
            target_cal = tdee

        # 4. 更新字段 (取整)
        self.daily_kcal_limit = int(target_cal)
        # 注意：这里不调用 save()，防止递归，调用者需手动 save 或由 save() 方法触发

    def save(self, *args, **kwargs):
        # 每次保存前自动重算
        self.calculate_and_save_daily_limit()
        super().save(*args, **kwargs)