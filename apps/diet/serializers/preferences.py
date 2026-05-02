from rest_framework import serializers
from apps.users.models import Profile 
from apps.diet.models import UserPreference
from apps.diet.domains.community.services import CommunityService
from apps.diet.domains.gamification.services import GamificationService
from apps.users.models import UserFollow

class ProfileSerializer(serializers.ModelSerializer):
    # 显式声明 nickname 字段，关联到 user.nickname
    nickname = serializers.CharField(source='user.nickname', required=False)
    follow_count = serializers.SerializerMethodField()
    fans_count = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    badges = serializers.SerializerMethodField()
    featured_badges = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        # [核心修复] 将 avatar、signature 及其他新增的身体档案字段全量加入白名单
        fields = [
            'nickname', 'avatar', 'signature', 'gender', 'height', 'weight', 'age', 
            'activity_level', 'diet_tags', 'allergens', 
            'daily_kcal_limit', 'goal_type', 'target_weight', 
            'water_goal_cups', 'water_goal_ml', 'bmr',
            'follow_count', 'fans_count', 'like_count', 'badges', 'featured_badges'
        ]
        # BMR 和 每日推荐摄入量由后端公式自动计算，不允许前端直接篡改
        read_only_fields = [
            'daily_kcal_limit', 'bmr', 'follow_count', 'fans_count',
            'like_count', 'badges', 'featured_badges'
        ]

    def get_follow_count(self, instance):
        return UserFollow.objects.filter(follower=instance.user).count()

    def get_fans_count(self, instance):
        return UserFollow.objects.filter(followed=instance.user).count()

    def get_like_count(self, instance):
        try:
            profile = CommunityService.get_user_profile(instance.user_id, instance.user_id)
            return profile.get("like_count", 0) if profile else 0
        except Exception:
            return 0

    def get_badges(self, instance):
        try:
            achievements = GamificationService.get_merged_achievements(instance.user)
        except Exception:
            return []
        return [
            {
                "id": achievement.get("id"),
                "name": achievement.get("name"),
                "icon": achievement.get("icon"),
            }
            for achievement in achievements
            if achievement.get("unlocked")
        ]

    def get_featured_badges(self, instance):
        try:
            return GamificationService.get_user_featured_badges(instance.user_id)
        except Exception:
            return []

    def update(self, instance, validated_data):
        # 提取 nickname
        user_data = validated_data.pop('user', {})
        nickname = user_data.get('nickname')
        
        user_updated = False
        if nickname and instance.user.nickname != nickname:
            instance.user.nickname = nickname
            user_updated = True

        # [核心修复] 处理前端传来的默认头像字符串
        if getattr(self, '_passed_avatar_string', None):
            new_avatar_str = self._passed_avatar_string
            # 只有当新传来的头像字符串和当前不一样，且不是同一张图的相对路径时，才执行更新
            if new_avatar_str != instance.user.avatar and not (instance.user.avatar and instance.user.avatar.endswith(new_avatar_str)):
                instance.user.avatar = new_avatar_str
                # 既然换成了默认头像（纯字符串），清空旧的物理文件关联，防止产生数据混乱
                instance.avatar = None
                user_updated = True

        if user_updated:
            instance.user.save()

        return super().update(instance, validated_data)

    def to_internal_value(self, data):
        if hasattr(data, 'copy'):
            _data = data.copy()
        else:
            _data = dict(data)
            
        avatar_val = _data.get('avatar')
        
        # [逻辑修正]
        # 如果前端传的是字符串（即切换自带的默认头像URL），这不是文件。
        # 为了防止 ImageField 报 '不是一个文件' 的 400 错误，我们将其弹出，
        # 并暂存到序列化器实例属性中，稍后在 update 方法中单独更新给 User 模型。
        if isinstance(avatar_val, str):
            self._passed_avatar_string = avatar_val
            _data.pop('avatar', None)
        else:
            self._passed_avatar_string = None
            
        return super().to_internal_value(_data)

    def to_representation(self, instance):
        """
        拦截序列化输出
        确保无论用户使用的是物理上传的头像还是系统默认的URL头像，
        前端都能准确收到完整字符串，而不是 null
        """
        data = super().to_representation(instance)
        
        # 如果 Profile 层的物理文件 avatar 为空 (或者序列化结果为 null)
        # 则说明当前使用的是默认头像，我们需要从 User 表中把 URL 拿出来补齐给前端
        if not data.get('avatar') and instance.user.avatar:
            data['avatar'] = instance.user.avatar

        avatar_url = data.get('avatar')
        request = self.context.get('request')
        if avatar_url and request and not str(avatar_url).startswith(('http://', 'https://')):
            data['avatar'] = request.build_absolute_uri(avatar_url)
            
        return data


class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ['target_id', 'target_type', 'action']


# [新增] 统一多态收藏对象序列化器，追加在文件末尾
class FavoriteItemSerializer(serializers.Serializer):
    """
    统一收藏列表出参序列化
    确保前端接收到的数据具有严格规范的归一化结构
    """
    id = serializers.CharField(help_text="目标ID (Mongo Object ID)")
    type = serializers.CharField(help_text="类型: recipe/restaurant/feed/sport")
    name = serializers.CharField(help_text="展示名称或动态内容截取")
    image = serializers.CharField(allow_blank=True, required=False, help_text="瀑布流封面图")
    calories = serializers.IntegerField(allow_null=True, required=False, help_text="卡路里(针对菜谱或运动帖)")
    rating = serializers.FloatField(allow_null=True, required=False, help_text="评分(针对商家)")        
