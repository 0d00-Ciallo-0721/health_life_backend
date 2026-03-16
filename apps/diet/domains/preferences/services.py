from apps.diet.models import UserPreference

class PreferenceService:
    @staticmethod
    def toggle_preference(user, target_id, target_type, action_cmd):
        """
        action_cmd: 'favorite', 'unfavorite', 'block', 'unblock'
        """
        db_action = 'like'
        is_delete = False
        
        if action_cmd in ['favorite', 'like']:
            db_action = 'like'
        elif action_cmd in ['unfavorite', 'unlike']:
            db_action = 'like'; is_delete = True
        elif action_cmd in ['block']:
            db_action = 'block'
        elif action_cmd in ['unblock']:
            db_action = 'block'; is_delete = True
        else:
            return False

        if is_delete:
            UserPreference.objects.filter(
                user=user, target_id=target_id, target_type=target_type, action=db_action
            ).delete()
            return "removed"
        else:
            UserPreference.objects.get_or_create(
                user=user, target_id=target_id, target_type=target_type, action=db_action
            )
            return "added"
        
    # [新增] 在 PreferenceService 类中追加 get_favorites 方法
    @staticmethod
    def get_favorites(user, filter_type='all'):
        """
        跨库多类型收藏聚合引擎
        统一出参结构，支持前端「我的收藏」瀑布流直接渲染
        """
        from apps.diet.models import UserPreference
        from apps.diet.models.mongo.recipe import Recipe
        from apps.diet.models.mongo.restaurant import Restaurant
        from apps.diet.models.mongo.community import CommunityFeed

        # 1. 查询 MySQL 获取收藏索引 (action_cmd 'favorite' 在底层映射为 'like')
        qs = UserPreference.objects.filter(user=user, action='like')
        if filter_type != 'all':
            qs = qs.filter(target_type=filter_type)

        prefs = list(qs)
        recipe_ids = [p.target_id for p in prefs if p.target_type == 'recipe']
        restaurant_ids = [p.target_id for p in prefs if p.target_type == 'restaurant']
        feed_ids = [p.target_id for p in prefs if p.target_type in ['feed', 'post', 'sport']]

        results = []

        # 2. 批量查询 MongoDB 菜谱并归一化
        if recipe_ids:
            recipes = Recipe.objects.filter(id__in=recipe_ids)
            for r in recipes:
                results.append({
                    "id": str(r.id),
                    "type": "recipe",
                    "name": getattr(r, 'name', "未知菜谱"),
                    "image": getattr(r, 'cover_image', getattr(r, 'image', "")),
                    "calories": getattr(r, 'calories', None),
                    "rating": None
                })

        # 3. 批量查询 MongoDB 餐厅并归一化
        if restaurant_ids:
            restaurants = Restaurant.objects.filter(id__in=restaurant_ids)
            for r in restaurants:
                results.append({
                    "id": str(r.id),
                    "type": "restaurant",
                    "name": getattr(r, 'name', "未知餐厅"),
                    "image": getattr(r, 'image_url', getattr(r, 'image', "")),
                    "calories": None,
                    "rating": getattr(r, 'rating', 5.0)
                })

        # 4. 批量查询 MongoDB 社区动态并归一化
        if feed_ids:
            feeds = CommunityFeed.objects.filter(id__in=feed_ids)
            for f in feeds:
                # 提取运动卡路里（若存在）
                cal = f.sport_info.get('calories') if getattr(f, 'sport_info', None) else None
                results.append({
                    "id": str(f.id),
                    "type": f.feed_type if hasattr(f, 'feed_type') else "feed",
                    "name": (f.content[:20] + "...") if f.content else "分享动态",
                    "image": f.images[0] if getattr(f, 'images', None) else "",
                    "calories": cal,
                    "rating": None
                })

        return results        