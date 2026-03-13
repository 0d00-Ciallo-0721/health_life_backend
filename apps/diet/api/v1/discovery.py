from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import requests
from django.conf import settings
# [修改] 顶部导入区，增加 PantrySelector
from apps.diet.domains.pantry.selectors import PantrySelector

from mongoengine.errors import ValidationError
from apps.diet.domains.discovery.matching_service import MatchingService
from apps.diet.domains.discovery.lbs_service import LBSService
from apps.diet.domains.discovery.wheel_engine import WheelEngine
from apps.diet.domains.discovery.shopping_service import ShoppingService
from apps.diet.domains.journal.selectors import JournalSelector
from apps.diet.domains.preferences.selectors import PreferenceSelector
from apps.diet.models import Recipe, Restaurant
from apps.common.utils import normalize_ingredient_name

class RecommendSearchView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        mode = request.data.get("mode", "cook")
        filters = request.data.get("filters", {})
        # 兼容层
        for key in ['cleanup_mode', 'scrap_mode', 'tools']:
            if key in request.data: filters[key] = request.data[key]
            
        if mode == "cook":
            data = MatchingService.get_cook_recommendations(
                request.user, 
                page=int(request.data.get("page", 1)),
                sort_by=request.data.get("sort_by", "match_score"),
                filters=filters
            )
            return Response({"code": 200, "data": {"recommendations": data, "has_more": len(data)==20}})
        elif mode == "restaurant":
            lng, lat = request.data.get("lng"), request.data.get("lat")
            if not lng or not lat: return Response({"code": 400, "msg": "需要经纬度"}, status=400)
            data = LBSService.get_recommendations(float(lng), float(lat))
            return Response({"code": 200, "data": {"recommendations": data}})
        return Response({"code": 400, "msg": "无效参数"}, status=400)

class RecipeDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, id):
        try:
            r = Recipe.objects.get(id=id)
            
            # 1. 检查是否收藏
            fav_data = PreferenceSelector.get_user_favorites(request.user, 'recipe')
            # 安全提取 target_id 列表进行比对
            fav_ids = [str(item.get('target_id', '')) for item in fav_data.get('items', [])]
            is_fav = str(r.id) in fav_ids
            
            # 2. 获取用户冰箱库存，用于判断食材状态 (in_fridge)
            user_ingredients = PantrySelector.get_user_ingredients_set(request.user)
            
            # 3. 构建食材详情与替代品逻辑
            ingredients_detail = []
            # 兼容 MongoDB 数据结构 (有时存的是 ingredients，有时存的是 ingredients_search)
            raw_ings = getattr(r, 'ingredients', getattr(r, 'ingredients_search', []))
            
            for ing in raw_ings:
                # 兼容字典 {"name": "番茄", "amount": "2个"} 或 纯字符串 "番茄"
                ing_name = ing.get('name', '') if isinstance(ing, dict) else str(ing)
                ing_amount = ing.get('amount', '') if isinstance(ing, dict) else ''
                
                if not ing_name:
                    continue
                    
                # 归一化名称，消除 "个"、"只" 等修饰词干扰
                std_name = normalize_ingredient_name(ing_name)
                
                ingredients_detail.append({
                    "name": ing_name,
                    "amount": ing_amount,
                    "in_fridge": std_name in user_ingredients,
                    "substitutes": MatchingService.get_recipe_substitutes(ing_name)
                })

            # 4. 组装全量数据结构
            data = {
                "id": str(r.id),
                "name": r.name,
                "image": getattr(r, 'image_url', ""),
                "calories": getattr(r, 'calories', 350),
                "cooking_time": getattr(r, 'cooking_time', 15),
                "difficulty": getattr(r, 'difficulty', "简单"),
                "tags": getattr(r, 'keywords', []),
                "steps": getattr(r, 'steps', []),  # 菜谱制作步骤
                "is_favorite": is_fav,
                "ingredients": ingredients_detail,
                "cook_count": JournalSelector.get_recipe_stats(request.user, id).get('cook_count', 0)
            }
            return Response({"code": 200, "msg": "success", "data": data})
            
        except Recipe.DoesNotExist:
            return Response({"code": 404, "msg": "菜谱不存在"}, status=404)
        # [新增] 拦截无效 ID 格式导致的崩溃
        except ValidationError:
            return Response({"code": 400, "msg": "无效的菜谱ID格式，是否误传了餐厅ID？"}, status=400)
        
class WheelOptionsView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        step = int(request.data.get("step", 1))
        data = WheelEngine.get_wheel_options(
            step, request.data.get("cuisine"), request.data.get("flavor"), request.user
        )
        key_map = {1: "cuisines", 2: "flavors", 3: "recommendations"}
        if step in [1, 2]:
            return Response({"code": 200, "data": {key_map[step]: [d['value'] for d in data]}})
        return Response({"code": 200, "data": {key_map[step]: data}})

class ShoppingListGenerateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        res = ShoppingService.generate_list(request.user, request.data.get('recipe_ids', []))
        return Response({"code": 200, "msg": "生成成功", "data": {"total_items": len(res), "list": res}})

class RestaurantDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, id):
        try:
            shop = Restaurant.objects.get(amap_id=id)
            
            # [修改] 真实读取 menu 字段
            menu_data = shop.menu if shop.menu else []
            
            # 如果数据库没菜单，返回空列表而不是 Mock 数据
            # 前端可以展示 "暂无菜单信息"
            
            data = {
                "id": shop.amap_id, 
                "name": shop.name, 
                "address": shop.address, 
                "rating": shop.rating, 
                "photos": shop.photos,
                "menu_items": menu_data # ✅ 真实数据
            }
            return Response({"code": 200, "data": data})
        except:
            return Response({"code": 404, "msg": "商家不存在"}, status=404)
        



class ShoppingStoreLBSView(APIView):
    """附近生鲜超市推荐 (LBS): GET /diet/shopping-list/stores/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        
        try:
            radius = int(request.query_params.get('radius', 3000))
        except ValueError:
            radius = 3000

        if not lat or not lng:
            return Response({"code": 400, "msg": "缺少经纬度参数"}, status=400)

        # 模拟的兜底周边生鲜超市数据，确保前端不报错并有内容展示
        fallback_stores = [
            {
                "id": "mock_001",
                "name": "盒马鲜生 (体验店)",
                "address": "当前定位附近 450 米",
                "distance": 450,
                "type": "生鲜超市"
            },
            {
                "id": "mock_002",
                "name": "永辉超市 (综合广场店)",
                "address": "当前定位附近 1.2 公里",
                "distance": 1200,
                "type": "大型综合超市"
            },
            {
                "id": "mock_003",
                "name": "便民农贸菜市场",
                "address": "当前定位附近 2.5 公里",
                "distance": 2500,
                "type": "农贸市场"
            }
        ]

        amap_key = getattr(settings, 'AMAP_WEB_KEY', '')
        if not amap_key:
            # 未配置 Key，平滑回落到 Mock 数据
            return Response({"code": 200, "msg": "success (mock)", "data": fallback_stores})

        # 配置了 Key，调用高德 POI 周边搜索 API (060100=商场, 060101=便利店, 060102=超市, 060200=特色商业街/菜市场)
        url = "https://restapi.amap.com/v3/place/around"
        params = {
            "key": amap_key,
            "location": f"{lng},{lat}",  # 高德API要求经度在前，纬度在后
            "keywords": "生鲜|超市|菜市场",
            "types": "060100|060101|060102|060200",
            "radius": radius,
            "sortrule": "distance",
            "offset": 15,
            "page": 1,
            "extensions": "base"
        }

        try:
            res = requests.get(url, params=params, timeout=3)
            res_data = res.json()
            
            if str(res_data.get("status")) == "1" and res_data.get("pois"):
                stores = []
                for poi in res_data["pois"]:
                    stores.append({
                        "id": poi.get("id"),
                        "name": poi.get("name"),
                        "address": poi.get("address") if isinstance(poi.get("address"), str) else "未知地址",
                        "distance": int(poi.get("distance", 0)),
                        "type": poi.get("type", "").split(";")[0] if poi.get("type") else "生鲜超市"
                    })
                return Response({"code": 200, "msg": "success", "data": stores})
            else:
                # 查无数据或高德返回限制，走兜底
                return Response({"code": 200, "msg": "success (fallback)", "data": fallback_stores})
        except Exception:
            # 网络请求超时或其他异常，走兜底
            return Response({"code": 200, "msg": "success (fallback)", "data": fallback_stores})        

