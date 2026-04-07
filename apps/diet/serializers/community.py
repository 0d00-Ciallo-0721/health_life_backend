from rest_framework import serializers

class FeedCreateSerializer(serializers.Serializer):
    """社区发帖入参校验"""
    content = serializers.CharField(max_length=1000, error_messages={"blank": "内容不能为空"})
    images = serializers.ListField(
        child=serializers.URLField(), required=False, max_length=9,
        error_messages={"max_length": "最多只能上传9张图片"}
    )
    # 扩展 choices 范围支持运动
    type = serializers.ChoiceField(choices=['post', 'recipe', 'restaurant', 'meal', 'sport'], default='post')
    target_id = serializers.CharField(max_length=64, required=False, allow_blank=True)
    
    # 兼容运动记录参数解析
    sport_info = serializers.DictField(required=False, help_text="当type为sport时必填的运动属性对象")


# [新增] 动态流聚合增强器
class FeedResponseEnhancer:
    """
    社区动态流数据聚合器
    用于动态拼装 MySQL(用户、徽章、状态) 和 MongoDB(帖子) 数据，避免 N+1 查询问题
    """
    @staticmethod
    def enhance_feed_list(feed_list, current_user):
        if not feed_list:
            return []
            
        from apps.users.models import User
        from apps.diet.models.mysql.gamification import UserFeaturedBadge
        
        # 1. 批量收集 User ID
        user_ids = set()
        for item in feed_list:
            uid = item.get('user_id') or item.get('user', {}).get('id')
            if uid:
                user_ids.add(int(uid))
                
        user_ids = list(user_ids)
        if not user_ids:
            return feed_list
            
        # 2. 批量查询 MySQL 组装用户信息与徽章
        users = User.objects.filter(id__in=user_ids).select_related('profile')
        user_map = {}
        for u in users:
            avatar_url = u.avatar
            if not avatar_url and hasattr(u, 'profile') and u.profile.avatar:
                avatar_url = u.profile.avatar.url if hasattr(u.profile.avatar, 'url') else str(u.profile.avatar)
                
            user_map[u.id] = {
                "id": u.id,
                "nickname": u.nickname or u.username,
                "avatar": avatar_url,
                "signature": u.profile.signature if hasattr(u, 'profile') else ""
            }
            
        badges = UserFeaturedBadge.objects.filter(user_id__in=user_ids).select_related('achievement')
        badges_map = {uid: [] for uid in user_ids}
        for b in badges:
            badges_map[b.user_id].append({
                "id": str(b.achievement.id),
                "name": b.achievement.title,
                "icon": b.achievement.icon or "🏅"
            })
            
        # 3. 数据回填与兼容格式化
        for item in feed_list:
            uid = item.get('user_id') or item.get('user', {}).get('id')
            if uid and int(uid) in user_map:
                u_info = user_map[int(uid)].copy()
                u_info["featured_badges"] = badges_map.get(int(uid), [])
                item['user'] = u_info
                
            # 状态兜底防腐
            if 'is_saved' not in item:
                item['is_saved'] = False
            if 'is_liked' not in item:
                item['is_liked'] = False
                
            # 运动数据结构统一对外输出
            f_type = item.get('type') or item.get('feed_type')
            item['type'] = f_type
            if f_type == 'sport':
                item['sport_info'] = item.get('sport_info', {})
                
        return feed_list