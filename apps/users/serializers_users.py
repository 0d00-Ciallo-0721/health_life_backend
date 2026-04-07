
from rest_framework import serializers
from .models import Profile, User
# [修改] 完整类代码更新
class ProfileSerializer(serializers.ModelSerializer):
    # 1. 映射 User 表的昵称
    nickname = serializers.CharField(source='user.nickname', required=False)
    
    # 2. 头像字段 (只读，返回 URL字符串)
    avatar = serializers.SerializerMethodField()

    # [新增] 社交维度字段预留 (动态计算)
    follow_count = serializers.SerializerMethodField()
    fans_count = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()

    # [新增] 游戏化维度字段预留 (动态计算)
    badges = serializers.SerializerMethodField()
    featured_badges = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            'nickname', 
            'avatar', 
            'signature',        
            'gender', 
            'height', 
            'weight', 
            'target_weight',    
            'age', 
            'activity_level', 
            'diet_tags', 
            'allergens', 
            'daily_kcal_limit', 
            'bmr',              
            'goal_type',
            'water_goal_cups',   # [新增] 饮水目标
            'follow_count',      # [新增] 关注数
            'fans_count',        # [新增] 粉丝数
            'like_count',        # [新增] 获赞数
            'badges',            # [新增] 所有徽章
            'featured_badges'    # [新增] 代表徽章
        ]
        # 自动计算与关联字段设为只读
        read_only_fields = [
            'daily_kcal_limit', 'bmr', 
            'follow_count', 'fans_count', 'like_count', 
            'badges', 'featured_badges'
        ]

    def get_avatar(self, obj):
        """返回绝对路径的头像URL"""
        request = self.context.get('request')
        # 优先取 Profile 里的 avatar，其次取 User 表的 avatar 字符串
        avatar_url = ""
        if obj.avatar:
            avatar_url = obj.avatar.url
        elif obj.user.avatar:
            avatar_url = obj.user.avatar

        if avatar_url and request:
            return request.build_absolute_uri(avatar_url)
        return avatar_url

    # -------- [新增] 动态字段方法预留 --------
    
    def get_follow_count(self, obj):
        """获取关注数"""
        return UserFollow.objects.filter(follower=obj.user).count()

    def get_fans_count(self, obj):
        """获取粉丝数"""
        return UserFollow.objects.filter(followed=obj.user).count()

    def get_like_count(self, obj):
        """获取获赞总数 (聚合用户所有动态的点赞数)"""
        # 这里预留接口，需结合社区模块的 Like 模型计算
        return getattr(obj, 'prefetched_like_count', 0)

    def get_badges(self, obj):
        """获取已解锁的所有勋章简报"""
        # 联动 diet 模块的 UserAchievement 表
        return [] 

    def get_featured_badges(self, obj):
        """获取名片展示的代表徽章"""
        featured = UserFeaturedBadge.objects.filter(user=obj.user)[:3]
        # 返回 BadgeSummary 结构
        return [{"id": b.achievement_id, "name": "勋章名称", "icon": "🏅"} for b in featured]
    # ----------------------------------------

    def update(self, instance, validated_data):
        """
        重写 update 以支持嵌套字段 (nickname) 的更新
        """
        user_data = validated_data.pop('user', {})
        
        # 1. 更新 User 表字段 (昵称)
        if 'nickname' in user_data:
            instance.user.nickname = user_data['nickname']
            instance.user.save()

        # 2. 更新 Profile 表字段
        return super().update(instance, validated_data)
    

# [新增] 他人公开主页序列化器
class PublicProfileSerializer(serializers.ModelSerializer):
    """
    他人公开主页序列化器，剔除敏感隐私信息(如BMR, 日常热量限制等)
    """
    nickname = serializers.CharField(source='user.nickname', read_only=True)
    avatar = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField() # 动态计算：当前访问者是否已关注该用户
    
    # 社交维度字段预留 (动态计算)
    follow_count = serializers.SerializerMethodField()
    fans_count = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            'nickname', 
            'avatar', 
            'signature',        
            'gender', 
            'follow_count',      
            'fans_count',        
            'like_count',
            'is_following'       # [新增] 是否关注标记
        ]

    def get_avatar(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return obj.user.avatar if hasattr(obj.user, 'avatar') else ""

    def get_follow_count(self, obj):
        return getattr(obj, 'prefetched_follow_count', 0)

    def get_fans_count(self, obj):
        return getattr(obj, 'prefetched_fans_count', 0)

    def get_like_count(self, obj):
        return getattr(obj, 'prefetched_like_count', 0)

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # 引入 service 进行权限和关注状态校验，避免循环引入通常放在函数内
            from .services import UserFollowService
            return UserFollowService.is_following(request.user, obj.user)
        return False
