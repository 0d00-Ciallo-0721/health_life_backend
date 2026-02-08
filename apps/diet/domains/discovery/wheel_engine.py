import random
from bson import ObjectId
from mongoengine.queryset.visitor import Q
from apps.diet.models import Recipe
from apps.diet.domains.preferences.selectors import PreferenceSelector

class WheelEngine:
    @staticmethod
    def get_wheel_options(step, cuisine=None, flavor=None, user=None):
        POPULAR_CUISINES = ["川菜", "粤菜", "湘菜", "鲁菜", "日式", "西餐", "东北菜", "西北菜"]
        
        if step == 1:
            return [{"name": c, "value": c} for c in POPULAR_CUISINES]
            
        elif step == 2:
            if not cuisine: return []
            pipeline = [
                {"$match": {"keywords": cuisine}},
                {"$unwind": "$keywords"},
                {"$group": {"_id": "$keywords", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            try:
                raw_flavors = list(Recipe.objects.aggregate(*pipeline))
                flavors = []
                for f in raw_flavors:
                    name = f['_id']
                    if name != cuisine and name not in POPULAR_CUISINES:
                        flavors.append({"name": name, "value": name})
                return flavors if len(flavors) >= 2 else [{"name": "热门", "value": "热门"}]
            except Exception:
                return [{"name": "热门", "value": "热门"}]

        elif step == 3:
            return WheelEngine._get_smart_candidates(user, cuisine, flavor)
        return []

    @staticmethod
    def _get_smart_candidates(user, cuisine, flavor):
        candidates = []
        seen_ids = set()
        
        # 1. 过滤黑名单
        blocked_ids = PreferenceSelector.get_blocked_ids(user)
        safe_blocked_ids = [bid for bid in blocked_ids if ObjectId.is_valid(bid)]
        
        # 2. 过滤过敏源
        profile = getattr(user, 'profile', None)
        allergens = set(profile.allergens) if profile else set()
        
        base_query = Q(id__nin=safe_blocked_ids)
        if cuisine: base_query &= Q(keywords=cuisine)
        if flavor and flavor not in ["热门", "家常"]: base_query &= Q(keywords=flavor)
        if allergens: base_query &= Q(ingredients_search__nin=list(allergens))

        # 3. 黄金比例: 3健康 + 2偏好 + 1放纵
        health_limit = (profile.daily_kcal_limit / 3) if profile else 600
        
        # A. 健康池
        WheelEngine._pick_from_pool(candidates, seen_ids, 
            base_query & Q(calories__lte=health_limit), count=3, reason="健康轻食")
            
        # B. 偏好池 (剩余的随机)
        WheelEngine._pick_from_pool(candidates, seen_ids, base_query, count=2, reason="口味匹配")
            
        # C. 放纵池
        WheelEngine._pick_from_pool(candidates, seen_ids, 
            base_query & Q(calories__gt=health_limit), count=1, reason="偶尔放纵")
            
        # D. 补齐
        if len(candidates) < 6:
            WheelEngine._pick_from_pool(candidates, seen_ids, base_query, count=6-len(candidates), reason="为您推荐")
            
        return candidates

    @staticmethod
    def _pick_from_pool(candidates, seen_ids, query, count, reason):
        try:
            pool = list(Recipe.objects(query).limit(50))
            pool = [r for r in pool if r.id not in seen_ids]
            if pool:
                selected = random.sample(pool, min(len(pool), count))
                for r in selected:
                    seen_ids.add(r.id)
                    candidates.append({
                        "id": str(r.id), "type": "recipe", "name": r.name,
                        "image": getattr(r, 'image_url', ""), "calories": getattr(r, 'calories', 350),
                        "match_reason": reason,
                        "difficulty": getattr(r, 'difficulty', "简单"),
                        "time": getattr(r, 'cooking_time', 15)
                    })
        except Exception: pass