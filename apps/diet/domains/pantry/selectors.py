import datetime
from django.utils import timezone
from apps.diet.models import FridgeItem
from apps.common.utils import normalize_ingredient_name

class PantrySelector:
    @staticmethod
    def get_user_ingredients_set(user):
        """获取用户拥有的食材标准名集合 (用于推荐算法)"""
        fridge_qs = FridgeItem.objects.filter(user=user)
        names = list(fridge_qs.values_list('name', flat=True))
        return {normalize_ingredient_name(i) for i in names}

    @staticmethod
    def get_priority_ingredients(user, cleanup_mode=False, scrap_mode=False):
        """获取优先消耗食材集合 (临期/边角料)"""
        priority_set = set()
        fridge_qs = FridgeItem.objects.filter(user=user)

        if cleanup_mode:
            # 3天内过期
            deadline = datetime.date.today() + datetime.timedelta(days=3)
            expiring_names = fridge_qs.filter(expiry_date__lte=deadline).values_list('name', flat=True)
            priority_set.update({normalize_ingredient_name(i) for i in expiring_names})
        
        if scrap_mode:
            scrap_names = fridge_qs.filter(is_scrap=True).values_list('name', flat=True)
            priority_set.update({normalize_ingredient_name(i) for i in scrap_names})
            
        return priority_set