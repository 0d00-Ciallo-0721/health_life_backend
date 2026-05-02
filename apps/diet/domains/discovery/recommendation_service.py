from collections import defaultdict

from bson import ObjectId
from django.db.models import Count
from mongoengine.queryset.visitor import Q

from apps.diet.domains.discovery.matching_service import MatchingService
from apps.diet.models import DailyIntake, Recipe, UserPreference


class RecommendationService:
    """Contest-facing recommendation coordinator.

    It keeps the existing content matcher intact and layers popular and
    collaborative signals on top, so the API can explain why each recipe was
    recommended.
    """

    STRATEGY_LABELS = {
        "popular": "热门推荐",
        "collaborative": "协同过滤",
        "content": "冰箱食材匹配",
        "hybrid": "混合推荐",
    }

    @classmethod
    def get_recommendations(
        cls,
        user,
        strategy="hybrid",
        page=1,
        page_size=20,
        sort_by="match_score",
        filters=None,
    ):
        filters = cls._prepare_filters(user, filters or {})
        strategy = strategy if strategy in cls.STRATEGY_LABELS else "hybrid"

        if strategy == "content":
            return cls.get_content_recommendations(user, page, page_size, sort_by, filters)
        if strategy == "popular":
            return cls.get_popular_recommendations(user, page, page_size, filters)
        if strategy == "collaborative":
            items = cls.get_collaborative_recommendations(user, page, page_size, filters)
            return items or cls.get_popular_recommendations(user, page, page_size, filters)
        return cls.get_hybrid_recommendations(user, page, page_size, sort_by, filters)

    @classmethod
    def get_content_recommendations(cls, user, page, page_size, sort_by, filters):
        items = MatchingService.get_cook_recommendations(
            user,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            filters=filters,
        )
        enriched = [cls._ensure_algorithm_fields(item, "content") for item in items]
        return enriched or cls._demo_recommendation_items(page, page_size, "content", filters)

    @classmethod
    def get_popular_recommendations(cls, user, page=1, page_size=20, filters=None):
        filters = filters or {}
        score_map = defaultdict(float)

        pref_rows = (
            UserPreference.objects.filter(target_type="recipe", action__in=["like", "save"])
            .values("target_id", "action")
            .annotate(total=Count("id"))
        )
        for row in pref_rows:
            weight = 3 if row["action"] == "like" else 2
            score_map[str(row["target_id"])] += row["total"] * weight

        intake_rows = (
            DailyIntake.objects.filter(source_type=1)
            .exclude(source_id__isnull=True)
            .exclude(source_id="")
            .values("source_id")
            .annotate(total=Count("id"))
        )
        for row in intake_rows:
            score_map[str(row["source_id"])] += row["total"] * 4

        ranked_ids = [rid for rid, _ in sorted(score_map.items(), key=lambda kv: kv[1], reverse=True)]
        recipes = cls._fetch_recipes_by_ids(ranked_ids, filters)

        if not recipes:
            recipes = cls._fallback_recipes(filters, limit=max(page * page_size, page_size))
            for index, recipe in enumerate(recipes):
                score_map[str(recipe.id)] = max(1, len(recipes) - index)

        if not recipes:
            return cls._demo_recommendation_items(page, page_size, "popular", filters)

        start = max(page - 1, 0) * page_size
        selected = recipes[start : start + page_size]
        max_score = max(score_map.values(), default=1)
        return [
            cls._recipe_to_item(
                recipe,
                recommend_type="popular",
                score=round(score_map.get(str(recipe.id), 1) / max_score * 100, 1),
                match_reason="近期收藏、保存或记录较多",
                score_breakdown={"popular": round(score_map.get(str(recipe.id), 1), 2)},
            )
            for recipe in selected
        ]

    @classmethod
    def get_collaborative_recommendations(cls, user, page=1, page_size=20, filters=None):
        filters = filters or {}
        behavior_map = cls._build_user_recipe_behavior_map()
        candidate_scores = cls._compute_collaborative_scores(user.id, behavior_map)
        if not candidate_scores:
            return []

        ranked_ids = [rid for rid, _ in sorted(candidate_scores.items(), key=lambda kv: kv[1], reverse=True)]
        recipes = cls._fetch_recipes_by_ids(ranked_ids, filters)
        start = max(page - 1, 0) * page_size
        selected = recipes[start : start + page_size]
        max_score = max(candidate_scores.values(), default=1)
        return [
            cls._recipe_to_item(
                recipe,
                recommend_type="collaborative",
                score=round(candidate_scores.get(str(recipe.id), 0) / max_score * 100, 1),
                match_reason="相似用户也喜欢",
                score_breakdown={"collaborative": round(candidate_scores.get(str(recipe.id), 0), 4)},
            )
            for recipe in selected
        ]

    @classmethod
    def get_hybrid_recommendations(cls, user, page=1, page_size=20, sort_by="match_score", filters=None):
        filters = filters or {}
        fetch_size = max(page * page_size * 2, 40)
        sources = [
            ("content", cls.get_content_recommendations(user, 1, fetch_size, sort_by, filters), 0.5),
            ("collaborative", cls.get_collaborative_recommendations(user, 1, fetch_size, filters), 0.3),
            ("popular", cls.get_popular_recommendations(user, 1, fetch_size, filters), 0.2),
        ]

        merged = {}
        for source_name, items, weight in sources:
            for item in items:
                recipe_id = str(item.get("id"))
                if not recipe_id:
                    continue
                bucket = merged.setdefault(recipe_id, dict(item))
                score = float(item.get("score", item.get("match_score", 0)) or 0)
                bucket.setdefault("score_breakdown", {})
                bucket["score_breakdown"][source_name] = score
                bucket["score"] = round(float(bucket.get("score", 0) or 0) + score * weight, 2)
                bucket["recommend_type"] = "hybrid"
                bucket["algorithm_label"] = cls.STRATEGY_LABELS["hybrid"]
                if not bucket.get("match_reason"):
                    bucket["match_reason"] = "综合热门度、相似用户行为与冰箱食材匹配"

        ranked = sorted(merged.values(), key=lambda item: item.get("score", 0), reverse=True)
        if not ranked:
            return cls._demo_recommendation_items(page, page_size, "hybrid", filters)
        start = max(page - 1, 0) * page_size
        return ranked[start : start + page_size]

    @classmethod
    def _build_user_recipe_behavior_map(cls):
        behavior_map = defaultdict(set)
        pref_rows = UserPreference.objects.filter(
            target_type="recipe", action__in=["like", "save"]
        ).values_list("user_id", "target_id")
        for user_id, target_id in pref_rows:
            behavior_map[user_id].add(str(target_id))

        intake_rows = (
            DailyIntake.objects.filter(source_type=1)
            .exclude(source_id__isnull=True)
            .exclude(source_id="")
            .values_list("user_id", "source_id")
        )
        for user_id, source_id in intake_rows:
            behavior_map[user_id].add(str(source_id))
        return behavior_map

    @staticmethod
    def _prepare_filters(user, filters):
        prepared = dict(filters or {})

        exclude_ids = prepared.get("exclude_ids", [])
        if isinstance(exclude_ids, str):
            exclude_ids = [exclude_ids]
        else:
            exclude_ids = list(exclude_ids or [])

        if user and getattr(user, "is_authenticated", True):
            blocked_ids = UserPreference.objects.filter(
                user=user,
                target_type="recipe",
                action="block",
            ).values_list("target_id", flat=True)
            exclude_ids.extend(str(item) for item in blocked_ids if item)

            try:
                profile = getattr(user, "profile", None)
            except Exception:
                profile = None
            profile_allergens = getattr(profile, "allergens", []) if profile else []
            allergens = prepared.get("allergens", [])
            if isinstance(allergens, str):
                allergens = [allergens]
            else:
                allergens = list(allergens or [])
            allergens.extend(item for item in profile_allergens if item)
            prepared["allergens"] = list(dict.fromkeys(str(item) for item in allergens if item))

        prepared["exclude_ids"] = list(dict.fromkeys(str(item) for item in exclude_ids if item))
        return prepared

    @staticmethod
    def _compute_collaborative_scores(user_id, behavior_map):
        own_items = behavior_map.get(user_id, set())
        if not own_items:
            return {}

        scores = defaultdict(float)
        for other_user_id, other_items in behavior_map.items():
            if other_user_id == user_id or not other_items:
                continue
            union = own_items | other_items
            if not union:
                continue
            similarity = len(own_items & other_items) / len(union)
            if similarity <= 0:
                continue
            for recipe_id in other_items - own_items:
                scores[recipe_id] += similarity
        return dict(scores)

    @classmethod
    def _fetch_recipes_by_ids(cls, recipe_ids, filters):
        valid_ids = [ObjectId(rid) for rid in recipe_ids if ObjectId.is_valid(str(rid))]
        if not valid_ids:
            return []
        try:
            query = cls._recipe_filter_query(filters) & Q(id__in=valid_ids)
            recipe_map = {str(recipe.id): recipe for recipe in Recipe.objects(query)}
            return [recipe_map[str(rid)] for rid in recipe_ids if str(rid) in recipe_map]
        except Exception:
            return []

    @classmethod
    def _fallback_recipes(cls, filters, limit=20):
        try:
            query = cls._recipe_filter_query(filters)
            recipes = list(Recipe.objects(query & Q(status=1)).order_by("-created_at").limit(limit))
            if recipes:
                return recipes
            return list(Recipe.objects(query).order_by("-created_at").limit(limit))
        except Exception:
            return []

    @classmethod
    def _demo_recommendation_items(cls, page=1, page_size=20, recommend_type="hybrid", filters=None):
        demo_recipes = [
            {
                "id": "demo_recipe_001",
                "name": "彩蔬鸡胸能量碗",
                "calories": 430,
                "difficulty": "简单",
                "cooking_time": 18,
                "ingredients": ["鸡胸肉", "糙米", "西兰花", "胡萝卜"],
                "tags": ["高蛋白", "控脂", "午餐"],
                "score": 92.0,
            },
            {
                "id": "demo_recipe_002",
                "name": "番茄豆腐菌菇汤",
                "calories": 260,
                "difficulty": "简单",
                "cooking_time": 15,
                "ingredients": ["番茄", "豆腐", "金针菇", "鸡蛋"],
                "tags": ["低卡", "补蛋白", "晚餐"],
                "score": 88.0,
            },
            {
                "id": "demo_recipe_003",
                "name": "虾仁牛油果藜麦沙拉",
                "calories": 390,
                "difficulty": "中等",
                "cooking_time": 20,
                "ingredients": ["虾仁", "牛油果", "藜麦", "生菜"],
                "tags": ["轻食", "优质脂肪", "高纤维"],
                "score": 85.0,
            },
            {
                "id": "demo_recipe_004",
                "name": "燕麦酸奶水果杯",
                "calories": 310,
                "difficulty": "简单",
                "cooking_time": 8,
                "ingredients": ["燕麦", "酸奶", "蓝莓", "香蕉"],
                "tags": ["早餐", "高纤维", "快手"],
                "score": 82.0,
            },
        ]
        allergens = {str(item).strip() for item in (filters or {}).get("allergens", []) if item}
        if allergens:
            demo_recipes = [
                recipe for recipe in demo_recipes
                if not allergens.intersection(recipe["ingredients"])
            ]
        start = max(page - 1, 0) * page_size
        selected = demo_recipes[start : start + page_size]
        label = cls.STRATEGY_LABELS.get(recommend_type, "推荐")
        return [
            {
                "id": recipe["id"],
                "name": recipe["name"],
                "match_score": int(round(recipe["score"])),
                "missing_ingredients": [],
                "cooking_time": recipe["cooking_time"],
                "difficulty": recipe["difficulty"],
                "calories": recipe["calories"],
                "image": "",
                "ingredients": [
                    {"name": ingredient, "in_fridge": False}
                    for ingredient in recipe["ingredients"]
                ],
                "match_reason": "演示兜底推荐：当前菜谱库暂无足够可展示数据",
                "tags": recipe["tags"],
                "recommend_type": recommend_type,
                "algorithm_label": label,
                "score": recipe["score"],
                "score_breakdown": {recommend_type: recipe["score"]},
            }
            for recipe in selected
        ]

    @staticmethod
    def _recipe_filter_query(filters):
        query = Q(status=1)
        raw_tags = filters.get("tags", [])
        if isinstance(raw_tags, str):
            raw_tags = [raw_tags]
        tags = [tag for tag in raw_tags if tag]
        if tags:
            query &= Q(keywords__in=tags)
        if filters.get("keyword"):
            query &= Q(name__icontains=filters["keyword"])
        if filters.get("difficulty"):
            query &= Q(difficulty=filters["difficulty"])
        calorie_min = RecommendationService._safe_int(filters.get("calorie_min"))
        if calorie_min is not None:
            query &= Q(calories__gte=calorie_min)
        calorie_max = RecommendationService._safe_int(filters.get("calorie_max"))
        if calorie_max is not None:
            query &= Q(calories__lte=calorie_max)
        exclude_ids = [ObjectId(rid) for rid in filters.get("exclude_ids", []) if ObjectId.is_valid(str(rid))]
        if exclude_ids:
            query &= Q(id__nin=exclude_ids)
        allergens = [item for item in filters.get("allergens", []) if item]
        if allergens:
            query &= Q(ingredients_search__nin=allergens)
        return query

    @staticmethod
    def _safe_int(value):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _ensure_algorithm_fields(cls, item, recommend_type):
        score = item.get("score", item.get("match_score", 0))
        item.setdefault("recommend_type", recommend_type)
        item.setdefault("algorithm_label", cls.STRATEGY_LABELS.get(recommend_type, "推荐"))
        item.setdefault("score", score)
        item.setdefault("score_breakdown", {recommend_type: score})
        return item

    @classmethod
    def _recipe_to_item(cls, recipe, recommend_type, score, match_reason, score_breakdown=None):
        item = {
            "id": str(recipe.id),
            "name": recipe.name,
            "match_score": int(round(score)),
            "missing_ingredients": [],
            "cooking_time": getattr(recipe, "cooking_time", 15),
            "difficulty": getattr(recipe, "difficulty", "简单"),
            "calories": getattr(recipe, "calories", 350),
            "image": getattr(recipe, "image_url", ""),
            "ingredients": [
                {"name": name, "in_fridge": False}
                for name in getattr(recipe, "ingredients_search", [])
            ],
            "match_reason": match_reason,
            "tags": getattr(recipe, "keywords", [])[:3],
            "recommend_type": recommend_type,
            "algorithm_label": cls.STRATEGY_LABELS.get(recommend_type, "推荐"),
            "score": score,
            "score_breakdown": score_breakdown or {recommend_type: score},
        }
        return item
