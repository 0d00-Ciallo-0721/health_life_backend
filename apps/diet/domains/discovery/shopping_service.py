from apps.diet.models import Recipe
from apps.diet.domains.pantry.selectors import PantrySelector
from apps.common.utils import normalize_ingredient_name

class ShoppingService:
    @staticmethod
    def generate_list(user, recipe_ids):
        if not recipe_ids: return []
            
        recipes = Recipe.objects(id__in=recipe_ids)
        needed_ingredients = set()
        ingredient_source_map = {} 
        
        # 1. 聚合需求
        for r in recipes:
            raw_ings = getattr(r, 'ingredients_search', [])
            for ing in raw_ings:
                std_name = normalize_ingredient_name(ing)
                if not std_name: continue
                needed_ingredients.add(std_name)
                if std_name not in ingredient_source_map:
                    ingredient_source_map[std_name] = []
                ingredient_source_map[std_name].append(r.name)

        # 2. 对比库存 (调用 PantrySelector)
        fridge_qs = PantrySelector.get_user_ingredients_set(user)
        
        # 3. 生成清单
        shopping_list = []
        for name in needed_ingredients:
            status = "check" if name in fridge_qs else "missing"
            shopping_list.append({
                "name": name,
                "status": status,
                "related_recipes": list(set(ingredient_source_map.get(name, [])))[:3]
            })
            
        shopping_list.sort(key=lambda x: x['status'], reverse=True)
        return shopping_list