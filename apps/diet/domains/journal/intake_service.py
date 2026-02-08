import datetime
from django.db import transaction
from bson import ObjectId
from apps.diet.models import DailyIntake, Recipe, Restaurant
from apps.common.utils import normalize_ingredient_name
# 关键依赖：Pantry Service
from apps.diet.domains.pantry.services import PantryService

def classify_meal_type(dt=None):
    if not dt: dt = datetime.datetime.now()
    h = dt.hour
    if 6 <= h < 10: return 'breakfast'
    elif 10 <= h < 14: return 'lunch'
    elif 14 <= h < 17: return 'snack'
    elif 17 <= h < 21: return 'dinner'
    else: return 'night_snack'

class IntakeService:
    @staticmethod
    def log_intake(user, source_type, source_id, portion=1.0, deduct_fridge=True, 
                   meal_type=None, meal_time_str=None, macros=None, custom_calories=0):
        # 1. 准备数据
        current_dt = datetime.datetime.now()
        exact_time_obj = None
        if meal_time_str:
             try:
                 exact_time_obj = datetime.datetime.strptime(meal_time_str, "%H:%M").time()
                 if not meal_type:
                     check_dt = datetime.datetime.combine(current_dt.date(), exact_time_obj)
                     meal_type = classify_meal_type(check_dt)
             except ValueError: pass
        
        if not meal_type: meal_type = classify_meal_type(current_dt)
        if not exact_time_obj: exact_time_obj = current_dt.time()

        # 2. 解析来源
        food_name = "未知食物"
        base_cals = 0
        base_nuts = {"carbohydrates": 0, "protein": 0, "fat": 0}
        ingredients_to_deduct = []

        if source_type == 1: # 菜谱
            if ObjectId.is_valid(source_id):
                recipe = Recipe.objects.get(id=source_id)
                food_name = recipe.name
                base_cals = getattr(recipe, 'calories', 350)
                mongo_nut = getattr(recipe, 'nutrition', {})
                base_nuts = {
                    "carbohydrates": mongo_nut.get('carb', 0),
                    "protein": mongo_nut.get('protein', 0),
                    "fat": mongo_nut.get('fat', 0)
                }
                if recipe.ingredients_search:
                    ingredients_to_deduct = [normalize_ingredient_name(i) for i in recipe.ingredients_search]
        elif source_type == 2: # 外卖
            shop = Restaurant.objects(amap_id=source_id).first()
            if shop:
                food_name = f"外卖: {shop.name}"
                base_cals = getattr(shop, 'estimated_calories', 600)
        elif source_type == 3: # 自定义
            food_name = "自定义录入"
            base_cals = int(custom_calories)

        # 3. 计算最终数值
        final_cals = int(base_cals * portion)
        final_macros = macros if macros else {k: float(v)*portion for k, v in base_nuts.items()}

        # 4. 事务执行
        with transaction.atomic():
            intake = DailyIntake.objects.create(
                user=user, source_type=source_type, source_id=str(source_id),
                food_name=food_name, meal_time=meal_type, exact_time=exact_time_obj,
                calories=final_cals, macros=final_macros
            )
            
            # [核心解耦] 调用库存服务扣减
            if source_type == 1 and deduct_fridge and ingredients_to_deduct:
                PantryService.deduct_inventory(user, ingredients_to_deduct, portion)

            return intake
            
    @staticmethod
    def delete_intake(user, log_id):
        try:
            DailyIntake.objects.get(id=log_id, user=user).delete()
            return True
        except DailyIntake.DoesNotExist:
            return False