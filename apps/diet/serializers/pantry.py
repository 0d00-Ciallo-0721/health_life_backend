from rest_framework import serializers
from django.utils import timezone
import datetime
# 从新的 models 包导入
from apps.diet.models import FridgeItem

class FridgeItemSerializer(serializers.ModelSerializer):
    # 计算已存储天数 (用于前端展示新鲜度)
    days_stored = serializers.SerializerMethodField()
    
    # [v3.0 新增] 临期计算
    is_expiring = serializers.SerializerMethodField()
    
    # [v3.1 新增] 新鲜度状态
    freshness = serializers.SerializerMethodField() 
    
    class Meta:
        model = FridgeItem
        fields = [
            'id', 'name', 'category', 'sub_category',
            'quantity', 'amount', 'unit', 
            'days_stored', 'created_at',
            'expiry_date', 'is_expiring', 'is_scrap',
            'freshness'
        ]
        read_only_fields = ['id', 'created_at', 'days_stored', 'is_expiring', 'freshness']

    def get_days_stored(self, obj):
        delta = timezone.now() - obj.created_at
        return delta.days
    
    def get_is_expiring(self, obj):
        if not obj.expiry_date:
            return False
        today = datetime.date.today()
        # 如果已经过期或在3天内过期
        if obj.expiry_date <= today + datetime.timedelta(days=3):
            return True
        return False
    
    def get_freshness(self, obj):
        """
        计算新鲜度状态: fresh, expiring (<=3天), expired (<0天), unknown
        """
        if not obj.expiry_date:
            return "unknown"
        delta = (obj.expiry_date - datetime.date.today()).days
        if delta < 0:
            return "expired"
        if delta <= 3:
            return "expiring"
        return "fresh"