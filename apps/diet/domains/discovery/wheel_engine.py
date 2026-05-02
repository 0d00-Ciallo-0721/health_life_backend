from apps.diet.models import Recipe
from apps.diet.domains.discovery.recommendation_service import RecommendationService
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
        
        # 2. 过滤过敏源
        try:
            profile = getattr(user, 'profile', None)
        except Exception:
            profile = None
        allergens = set(profile.allergens) if profile else set()

        tags = []
        if cuisine:
            tags.append(cuisine)
        if flavor and flavor not in ["热门", "家常"]:
            tags.append(flavor)

        recommendations = RecommendationService.get_recommendations(
            user,
            strategy="hybrid",
            page=1,
            page_size=60,
            filters={
                "tags": tags,
                "exclude_ids": blocked_ids,
                "allergens": list(allergens),
            },
        )

        # 3. 黄金比例: 3健康 + 2偏好 + 1放纵
        health_limit = WheelEngine._safe_health_limit(profile)
        health_pool = [item for item in recommendations if WheelEngine._safe_calories(item) <= health_limit]
        indulgent_pool = [item for item in recommendations if WheelEngine._safe_calories(item) > health_limit]
        
        # A. 健康池
        WheelEngine._pick_ranked_candidates(candidates, seen_ids, health_pool, count=3, reason="健康轻食")
            
        # B. 偏好池
        WheelEngine._pick_ranked_candidates(candidates, seen_ids, recommendations, count=2, reason="口味匹配")
            
        # C. 放纵池
        WheelEngine._pick_ranked_candidates(candidates, seen_ids, indulgent_pool, count=1, reason="偶尔放纵")
            
        # D. 补齐
        if len(candidates) < 6:
            WheelEngine._pick_ranked_candidates(candidates, seen_ids, recommendations, count=6-len(candidates), reason="为您推荐")
            
        return candidates

    @staticmethod
    def _pick_ranked_candidates(candidates, seen_ids, pool, count, reason):
        picked = 0
        for item in pool:
            if picked >= count:
                break
            recipe_id = item.get("id")
            if not recipe_id or recipe_id in seen_ids:
                continue
            seen_ids.add(recipe_id)
            picked += 1
            candidates.append({
                "id": recipe_id,
                "type": "recipe",
                "name": item.get("name"),
                "image": item.get("image", ""),
                "calories": item.get("calories", 350),
                "match_reason": reason,
                "difficulty": item.get("difficulty", "简单"),
                "time": item.get("cooking_time", item.get("time", 15)),
                "recommend_type": item.get("recommend_type", "hybrid"),
                "algorithm_label": item.get("algorithm_label", "混合推荐"),
                "score": item.get("score", item.get("match_score", 0)),
            })

    @staticmethod
    def _safe_health_limit(profile):
        if not profile:
            return 600
        try:
            return (int(getattr(profile, "daily_kcal_limit", 0)) or 1800) / 3
        except (TypeError, ValueError):
            return 600

    @staticmethod
    def _safe_calories(item):
        try:
            return int(item.get("calories", 350) or 350)
        except (TypeError, ValueError):
            return 350
