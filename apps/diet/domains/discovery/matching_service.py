import datetime
from mongoengine.queryset.visitor import Q
from apps.diet.models import Recipe
from apps.common.utils import INGREDIENT_SYNONYMS, normalize_ingredient_name
# 跨域调用
from apps.diet.domains.pantry.selectors import PantrySelector

class MatchingService:
    SUBSTITUTE_RULES = {
        "葱": [{"name": "洋葱", "reason": "风味相近"}],
        "生抽": [{"name": "盐", "reason": "提供咸味"}, {"name": "老抽", "reason": "上色用"}],
        "冰糖": [{"name": "白糖", "reason": "甜味来源"}],
        "鸡胸肉": [{"name": "鸡腿肉", "reason": "口感更嫩"}],
        "西红柿": [{"name": "番茄酱", "reason": "提供酸甜味"}],
        "料酒": [{"name": "白酒", "reason": "去腥"}, {"name": "姜片", "reason": "去腥"}],
    }

    @staticmethod
    def get_cook_recommendations(user, page=1, page_size=20, sort_by='match_score', filters=None):
        if filters is None: filters = {}
        
        # 1. 调用 Pantry 域获取库存
        user_ingredients = PantrySelector.get_user_ingredients_set(user)
        
        # 2. 处理特殊模式
        cleanup_mode = filters.get('cleanup_mode', False)
        scrap_mode = filters.get('scrap_mode', False)
        priority_ingredients = PantrySelector.get_priority_ingredients(user, cleanup_mode, scrap_mode)

        # 3. 构建 MongoDB 查询
        query = Q()
        if (cleanup_mode or scrap_mode) and priority_ingredients:
            query = Q(ingredients_search__in=list(priority_ingredients))
        elif user_ingredients:
            query = Q(ingredients_search__in=list(user_ingredients))
        
        # 基础筛选
        if filters.get('tags'): query &= Q(keywords__in=filters['tags'])
        if filters.get('keyword'): query &= Q(name__icontains=filters['keyword'])
        if filters.get('difficulty'): query &= Q(difficulty=filters['difficulty'])
        
        # 热量范围
        if filters.get('calorie_min'): query &= Q(calories__gte=int(filters['calorie_min']))
        if filters.get('calorie_max'): query &= Q(calories__lte=int(filters['calorie_max']))

        # 4. 执行查询与内存排序
        skip = (page - 1) * page_size
        fetch_limit = page_size * 5 
        raw_recipes = Recipe.objects(query).skip(skip).limit(fetch_limit)
        
        processed_list = []
        for r in raw_recipes:
            try:
                raw_ings = getattr(r, 'ingredients_search', [])
                if not raw_ings: continue
                
                # 归一化比较
                recipe_ings_std = {normalize_ingredient_name(i) for i in raw_ings if i}
                matched = user_ingredients & recipe_ings_std
                missing = recipe_ings_std - user_ingredients
                
                # 计算分值
                score = 0
                if recipe_ings_std:
                    score = int((len(matched) / len(recipe_ings_std)) * 100)
                
                is_priority_hit = False
                if (cleanup_mode or scrap_mode) and priority_ingredients:
                    if priority_ingredients & recipe_ings_std:
                        score += 20
                        is_priority_hit = True
                
                score = min(100, score)

                # 匹配理由
                match_reason = "猜你喜欢"
                if is_priority_hit:
                    match_reason = "消耗临期/边角料"
                elif score >= 80: 
                    match_reason = f"匹配度高，缺{len(missing)}样"

                # 详情构建
                ings_detail = []
                for ing_name in raw_ings:
                    std_name = normalize_ingredient_name(ing_name)
                    ings_detail.append({
                        "name": ing_name,
                        "in_fridge": std_name in user_ingredients
                    })

                processed_list.append({
                    "id": str(r.id),
                    "name": r.name,
                    "match_score": score,
                    "missing_ingredients": list(missing),
                    "cooking_time": getattr(r, 'cooking_time', 15),
                    "difficulty": getattr(r, 'difficulty', "简单"),
                    "calories": getattr(r, 'calories', 350),
                    "image": getattr(r, 'image_url', ""),
                    "ingredients": ings_detail,
                    "match_reason": match_reason,
                    "tags": getattr(r, 'keywords', [])[:3]
                })
            except Exception: continue
            
        # 内存排序
        if sort_by == 'match_score':
            processed_list.sort(key=lambda x: x['match_score'], reverse=True)
        elif sort_by == 'calories':
            processed_list.sort(key=lambda x: x['calories'])
        elif sort_by == 'time':
            processed_list.sort(key=lambda x: x['cooking_time'])
            
        return processed_list[:page_size]

    @staticmethod
    def get_recipe_substitutes(ingredient_name):
        std_name = normalize_ingredient_name(ingredient_name)
        return MatchingService.SUBSTITUTE_RULES.get(std_name, [])