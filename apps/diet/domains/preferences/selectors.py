from apps.diet.models import UserPreference, Recipe, Restaurant

class PreferenceSelector:
    @staticmethod
    def get_blocked_ids(user):
        """获取黑名单 ID 列表"""
        return list(UserPreference.objects.filter(
            user=user, action='block'
        ).values_list('target_id', flat=True))

    @staticmethod
    def get_user_favorites(user, type_filter='all', page=1, page_size=20):
        """获取收藏列表 (MySQL + MongoDB 聚合)"""
        qs = UserPreference.objects.filter(user=user, action='like')
        
        if type_filter == 'recipe':
            qs = qs.filter(target_type='recipe')
        elif type_filter == 'restaurant':
            qs = qs.filter(target_type='restaurant')
            
        total = qs.count()
        start = (page - 1) * page_size
        fav_records = qs.order_by('-created_at')[start : start+page_size]
        
        # 聚合 ID
        recipe_ids = [f.target_id for f in fav_records if f.target_type == 'recipe']
        restaurant_ids = [f.target_id for f in fav_records if f.target_type == 'restaurant']
        
        # 批量查询 Mongo
        recipes_map = {}
        if recipe_ids:
            for r in Recipe.objects(id__in=recipe_ids):
                recipes_map[str(r.id)] = {
                    "id": str(r.id), "type": "recipe", "name": r.name,
                    "image": getattr(r, 'image_url', ""), "calories": getattr(r, 'calories', 350)
                }
                
        restaurants_map = {}
        if restaurant_ids:
            for r in Restaurant.objects(amap_id__in=restaurant_ids):
                restaurants_map[r.amap_id] = {
                    "id": r.amap_id, "type": "restaurant", "name": r.name,
                    "image": r.photos[0] if r.photos else "", "address": r.address, "rating": r.rating
                }

        items = []
        for fav in fav_records:
            item = None
            if fav.target_type == 'recipe':
                item = recipes_map.get(fav.target_id)
            elif fav.target_type == 'restaurant':
                item = restaurants_map.get(fav.target_id)
            
            if item:
                item['favorited_at'] = fav.created_at.isoformat()
                items.append(item)
                
        return {"items": items, "total": total, "has_more": (start + page_size) < total}