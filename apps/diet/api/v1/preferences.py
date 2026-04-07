from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.users.models import Profile
from apps.diet.serializers.preferences import ProfileSerializer
from apps.diet.domains.preferences.services import PreferenceService
from apps.diet.domains.preferences.selectors import PreferenceSelector

class ProfileUpdateView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer
    def get_object(self):
        obj, _ = Profile.objects.get_or_create(user=self.request.user)
        return obj

    def post(self, request, *args, **kwargs):
        # 兼容小程序的 POST 请求
        return self.partial_update(request, *args, **kwargs)

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.calculate_and_save_daily_limit()

class PreferenceOperationView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        target_id = request.data.get('item_id') or request.data.get('target_id')
        target_type = request.data.get('item_type') or request.data.get('target_type')
        action = request.data.get('action')
        
        if not all([target_id, target_type, action]):
            return Response({"code": 400, "msg": "缺少参数"}, status=400)
            
        res = PreferenceService.toggle_preference(request.user, target_id, target_type, action)
        if res is False: return Response({"code": 400, "msg": "无效操作"}, status=400)
        return Response({"code": 200, "msg": "操作成功", "data": {"status": res == "added", "action": action}})

class FavoriteListView(APIView):
    """
    获取用户的收藏列表 (混合 MySQL 与 MongoDB 聚合查询)
    GET /diet/favorites/?type=all|recipe|restaurant
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        filter_type = request.query_params.get('type', 'all')
        
        # 1. 查询 MySQL 获取用户收藏关系
        from apps.diet.models.mysql.preference import Preference
        qs = Preference.objects.filter(user=request.user, action='favorite')
        if filter_type in ['recipe', 'restaurant']:
            qs = qs.filter(target_type=filter_type)
        
        favorites = list(qs)
        if not favorites:
            return Response({"code": 200, "msg": "success", "data": []})

        # 2. 提取 ID 批量查询 MongoDB
        recipe_ids = [fav.target_id for fav in favorites if fav.target_type == 'recipe']
        restaurant_ids = [fav.target_id for fav in favorites if fav.target_type == 'restaurant']
        
        recipe_map = {}
        restaurant_map = {}
        
        # 动态导入 MongoDB 模型防循环依赖，并执行 in 查询
        try:
            if recipe_ids:
                from apps.diet.models.mongo.recipe import Recipe
                recipes = Recipe.objects.filter(id__in=recipe_ids)
                recipe_map = {str(r.id): r for r in recipes}
        except Exception:
            pass
            
        try:
            if restaurant_ids:
                from apps.diet.models.mongo.restaurant import Restaurant
                restaurants = Restaurant.objects.filter(id__in=restaurant_ids)
                restaurant_map = {str(r.id): r for r in restaurants}
        except Exception:
            pass
        
        # 3. 组装符合前端契约的标准化列表
        result_list = []
        for fav in favorites:
            item_data = {
                "id": fav.target_id,
                "type": fav.target_type,
                "name": "已失效内容",
                "image": "",
                "created_at": fav.created_at.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            if fav.target_type == 'recipe':
                recipe = recipe_map.get(str(fav.target_id))
                if recipe:
                    item_data["name"] = getattr(recipe, 'name', item_data["name"])
                    item_data["image"] = getattr(recipe, 'cover_image', getattr(recipe, 'image', ""))
                    item_data["calories"] = getattr(recipe, 'calories', 0)
                    item_data["tags"] = getattr(recipe, 'tags', [])
                    
            elif fav.target_type == 'restaurant':
                restaurant = restaurant_map.get(str(fav.target_id))
                if restaurant:
                    item_data["name"] = getattr(restaurant, 'name', item_data["name"])
                    item_data["image"] = getattr(restaurant, 'cover_image', getattr(restaurant, 'image', ""))
                    item_data["rating"] = getattr(restaurant, 'rating', 0.0)
                    item_data["address"] = getattr(restaurant, 'address', "")
                    
            # 过滤掉 MongoDB 中被删除但收藏表中仍存在的脏数据
            if item_data["name"] != "已失效内容":
                result_list.append(item_data)
                
        # 按收藏时间倒序排列
        result_list.sort(key=lambda x: x["created_at"], reverse=True)
        
        return Response({"code": 200, "msg": "success", "data": result_list})