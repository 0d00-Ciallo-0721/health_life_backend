from django.db import models
from django.conf import settings

class FridgeItem(models.Model):
    """
    冰箱库存 (MySQL)
    存储用户现有的食材，用于匹配菜谱
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='fridge_items'
    )
    name = models.CharField(max_length=64, db_index=True, verbose_name="食材名称")
    category = models.CharField(max_length=32, null=True, blank=True, verbose_name="分类")
    quantity = models.CharField(max_length=32, null=True, blank=True, verbose_name="数量描述")
    
    # [v3.0 新增] 效期与状态管理
    expiry_date = models.DateField(null=True, blank=True, verbose_name="过期日期")
    is_scrap = models.BooleanField(default=False, verbose_name="是否边角料")

    # [新增] 结构化数量，用于计算 (如 2.5)
    amount = models.FloatField(default=1.0, verbose_name="数量数值")
    # [v3.1 新增] 子分类 (如: 瓜果类, 叶菜类)
    sub_category = models.CharField(max_length=32, null=True, blank=True, verbose_name="子分类")
    # [新增] 单位 (如 "个", "kg", "g")
    unit = models.CharField(max_length=10, default="个", verbose_name="单位")  

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="入库时间")

    def __str__(self):
        return f"{self.user.username} 的冰箱 - {self.name} ({self.amount}{self.unit})"

    class Meta:
        db_table = 'diet_fridgeitem'
        verbose_name = "冰箱食材"
        indexes = [
            models.Index(fields=['user', 'name']), 
            models.Index(fields=['expiry_date']),  # 加速临期查询
        ]