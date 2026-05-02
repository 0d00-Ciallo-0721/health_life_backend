import logging

import requests
from django.conf import settings
from mongoengine.errors import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.utils import normalize_ingredient_name
from apps.diet.domains.discovery.lbs_service import LBSService
from apps.diet.domains.discovery.matching_service import MatchingService
from apps.diet.domains.discovery.recommendation_service import RecommendationService
from apps.diet.domains.discovery.shopping_service import ShoppingService
from apps.diet.domains.discovery.wheel_engine import WheelEngine
from apps.diet.domains.journal.selectors import JournalSelector
from apps.diet.domains.pantry.selectors import PantrySelector
from apps.diet.domains.preferences.selectors import PreferenceSelector
from apps.diet.models import Recipe, Restaurant


logger = logging.getLogger(__name__)


class RecommendSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        mode = request.data.get("mode", "cook")
        filters = request.data.get("filters", {})
        for key in ["cleanup_mode", "scrap_mode", "tools"]:
            if key in request.data:
                filters[key] = request.data[key]

        if mode == "cook":
            try:
                page = int(request.data.get("page", 1))
                page_size = int(request.data.get("page_size", 20))
            except (TypeError, ValueError):
                page = 1
                page_size = 20
            page_size = max(1, min(page_size, 50))
            data = RecommendationService.get_recommendations(
                request.user,
                page=page,
                page_size=page_size,
                sort_by=request.data.get("sort_by", "match_score"),
                strategy=request.data.get("strategy", "hybrid"),
                filters=filters,
            )
            return Response({"code": 200, "data": {"recommendations": data, "has_more": len(data) == page_size}})

        if mode == "restaurant":
            lng, lat = request.data.get("lng"), request.data.get("lat")
            if not lng or not lat:
                return Response({"code": 400, "msg": "需要经纬度"}, status=400)
            data = LBSService.get_recommendations(float(lng), float(lat))
            return Response({"code": 200, "data": {"recommendations": data}})

        return Response({"code": 400, "msg": "无效参数"}, status=400)


class RecipeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        try:
            recipe = Recipe.objects.get(id=id)

            fav_data = PreferenceSelector.get_user_favorites(request.user, "recipe")
            fav_ids = [str(item.get("id", "")) for item in fav_data.get("items", [])]
            is_favorite = str(recipe.id) in fav_ids

            user_ingredients = PantrySelector.get_user_ingredients_set(request.user)
            ingredients_detail = []
            raw_ingredients = getattr(recipe, "ingredients", getattr(recipe, "ingredients_search", []))

            for ingredient in raw_ingredients:
                name = ingredient.get("name", "") if isinstance(ingredient, dict) else str(ingredient)
                amount = ingredient.get("amount", "") if isinstance(ingredient, dict) else ""
                if not name:
                    continue

                standard_name = normalize_ingredient_name(name)
                ingredients_detail.append(
                    {
                        "name": name,
                        "amount": amount,
                        "in_fridge": standard_name in user_ingredients,
                        "substitutes": MatchingService.get_recipe_substitutes(name),
                    }
                )

            data = {
                "id": str(recipe.id),
                "name": recipe.name,
                "image": getattr(recipe, "image_url", ""),
                "calories": getattr(recipe, "calories", 350),
                "cooking_time": getattr(recipe, "cooking_time", 15),
                "difficulty": getattr(recipe, "difficulty", "简单"),
                "tags": getattr(recipe, "keywords", []),
                "steps": getattr(recipe, "steps", []),
                "is_favorite": is_favorite,
                "ingredients": ingredients_detail,
                "cook_count": JournalSelector.get_recipe_stats(request.user, id).get("cook_count", 0),
            }
            return Response({"code": 200, "msg": "success", "data": data})
        except Recipe.DoesNotExist:
            return Response({"code": 404, "msg": "菜谱不存在"}, status=404)
        except ValidationError:
            return Response({"code": 400, "msg": "无效的菜谱ID格式"}, status=400)


class WheelOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        step = int(request.data.get("step", 1))
        data = WheelEngine.get_wheel_options(step, request.data.get("cuisine"), request.data.get("flavor"), request.user)
        key_map = {1: "cuisines", 2: "flavors", 3: "recommendations"}
        if step in [1, 2]:
            return Response({"code": 200, "data": {key_map[step]: [item["value"] for item in data]}})
        return Response({"code": 200, "data": {key_map[step]: data}})


class ShoppingListGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        result = ShoppingService.generate_list(request.user, request.data.get("recipe_ids", []))
        return Response({"code": 200, "msg": "生成成功", "data": {"total_items": len(result), "list": result}})


class RestaurantDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        try:
            shop = Restaurant.objects.get(amap_id=id)
        except Restaurant.DoesNotExist:
            return Response({"code": 404, "msg": "商家不存在"}, status=404)

        return Response(
            {
                "code": 200,
                "data": {
                    "id": shop.amap_id,
                    "name": shop.name,
                    "address": shop.address,
                    "rating": shop.rating,
                    "photos": getattr(shop, "photos", []),
                    "menu_items": shop.menu if getattr(shop, "menu", None) else [],
                },
            }
        )


class ShoppingStoreLBSView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        try:
            radius = int(request.query_params.get("radius", 3000))
        except ValueError:
            radius = 3000

        if not lat or not lng:
            return Response({"code": 400, "msg": "缺少经纬度参数"}, status=400)

        fallback_stores = [
            {"id": "mock_001", "name": "盒马鲜生", "address": "附近 450 米", "distance": 450, "type": "生鲜超市"},
            {"id": "mock_002", "name": "永辉超市", "address": "附近 1.2 公里", "distance": 1200, "type": "综合超市"},
            {"id": "mock_003", "name": "便民菜市场", "address": "附近 2.5 公里", "distance": 2500, "type": "农贸市场"},
        ]

        amap_key = getattr(settings, "AMAP_WEB_KEY", "")
        if not amap_key:
            if settings.ENABLE_LBS_MOCK_FALLBACK:
                return Response({"code": 200, "msg": "mock fallback", "data": fallback_stores})
            return Response({"code": 200, "msg": "AMAP_WEB_KEY 未配置", "data": []})

        url = "https://restapi.amap.com/v3/place/around"
        params = {
            "key": amap_key,
            "location": f"{lng},{lat}",
            "keywords": "生鲜|超市|菜市场",
            "types": "060100|060101|060102|060200",
            "radius": radius,
            "sortrule": "distance",
            "offset": 15,
            "page": 1,
            "extensions": "base",
        }

        try:
            response = requests.get(url, params=params, timeout=3)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logger.warning("LBS store lookup failed: %s", exc)
            if settings.ENABLE_LBS_MOCK_FALLBACK:
                return Response({"code": 200, "msg": "fallback", "data": fallback_stores})
            return Response({"code": 502, "msg": "商超查询失败", "data": None}, status=502)

        pois = payload.get("pois") or []
        if str(payload.get("status")) != "1" or not pois:
            if settings.ENABLE_LBS_MOCK_FALLBACK:
                return Response({"code": 200, "msg": "fallback", "data": fallback_stores})
            return Response({"code": 200, "msg": "未找到附近商超", "data": []})

        stores = [
            {
                "id": poi.get("id"),
                "name": poi.get("name"),
                "address": poi.get("address") if isinstance(poi.get("address"), str) else "未知地址",
                "distance": int(poi.get("distance", 0)),
                "type": poi.get("type", "").split(";")[0] if poi.get("type") else "生鲜超市",
            }
            for poi in pois
        ]
        return Response({"code": 200, "msg": "success", "data": stores})
