from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.users.models import Profile
from apps.diet.models.mongo.restaurant import Restaurant 
from apps.diet.models.mysql.gamification import ChallengeTask, Remedy, Achievement

User = get_user_model()

# --- 1. 用户管理相关 ---
class ProfileSerializer(serializers.ModelSerializer):
    """用户档案详情"""
    class Meta:
        model = Profile
        fields = ['gender', 'height', 'weight', 'age', 'goal_type', 'bmr', 'daily_kcal_limit']
        read_only_fields = ['bmr', 'daily_kcal_limit']

class AdminUserSerializer(serializers.ModelSerializer):
    """管理员查看的用户列表"""
    profile = ProfileSerializer(read_only=True) # 嵌套显示档案
    
    class Meta:
        model = User
        fields = ['id', 'username', 'nickname', 'phone', 'avatar', 'is_active', 'date_joined', 'profile']
        read_only_fields = ['username', 'date_joined']

# --- 2. 菜谱审核相关 (MongoDB) ---
class MongoRecipeAuditSerializer(serializers.Serializer):
    """
    MongoDB 菜谱审核序列化器
    """
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()        # ✅ 修正: 使用 name 而非 title
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.IntegerField(default=0) # ✅ 新增: 审核状态
    image_url = serializers.CharField(required=False, allow_blank=True)
    calories = serializers.IntegerField(required=False)
    created_at = serializers.DateTimeField(required=False)


class MongoRestaurantSerializer(serializers.Serializer):
    """
    商家管理序列化器 (MongoDB)
    """
    id = serializers.CharField(read_only=True)
    amap_id = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField()
    address = serializers.CharField(required=False, allow_blank=True)
    type = serializers.CharField(required=False, allow_blank=True)
    rating = serializers.FloatField(default=0.0)
    cost = serializers.FloatField(default=0.0)
    
    # 🌍 修改点 1: 增加 write_only=True，防止读取时自动序列化导致报错
    location = serializers.ListField(
        child=serializers.FloatField(), 
        min_length=2, 
        max_length=2, 
        required=True,
        write_only=True, # 👈 关键修改
        help_text="[经度, 纬度]"
    )
    
    photos = serializers.ListField(child=serializers.CharField(), required=False)
    menu = serializers.ListField(child=serializers.DictField(), required=False)
    cached_at = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        return Restaurant.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    # 🌍 修改点 2: 重写序列化输出方法，手动处理 GeoJSON
    def to_representation(self, instance):
        # 先获取基础字段数据
        data = super().to_representation(instance)
        
        # 手动提取 location 的 coordinates
        loc = getattr(instance, 'location', None)
        if loc:
            # 情况A: 它是 GeoJSON 字典 {'type': 'Point', 'coordinates': [x, y]}
            if isinstance(loc, dict) and 'coordinates' in loc:
                data['location'] = loc['coordinates']
            # 情况B: 它已经是列表 (很少见，但为了健壮性)
            elif isinstance(loc, (list, tuple)):
                data['location'] = loc
            # 情况C: 它是对象且有 coordinates 属性
            elif hasattr(loc, 'coordinates'):
                data['location'] = loc.coordinates
        
        return data
    

# --- 3. 挑战任务管理 ---
class ChallengeTaskSerializer(serializers.ModelSerializer):
    """健康挑战任务序列化器"""
    class Meta:
        model = ChallengeTask
        fields = '__all__'

# --- 4. 补救方案管理 ---
class RemedySerializer(serializers.ModelSerializer):
    """补救方案序列化器"""
    # 增加一个 display 字段，方便前端显示中文场景名 (如 'overeat' -> '暴食')
    scenario_display = serializers.CharField(source='get_scenario_display', read_only=True)

    class Meta:
        model = Remedy
        fields = ['id', 'scenario', 'scenario_display', 'title', 'desc', 'order']    


# --- 5. 成就字典管理 (MySQL) ---
class AchievementSerializer(serializers.ModelSerializer):
    """成就字典管理序列化器"""
    class Meta:
        model = Achievement
        fields = '__all__'


# --- 6. 社区内容审核 (MongoDB) ---
class MongoCommunityFeedSerializer(serializers.Serializer):
    """社区动态序列化器 (后台查看/审核用)"""
    id = serializers.CharField(read_only=True)
    user_id = serializers.IntegerField()
    content = serializers.CharField()
    images = serializers.ListField(child=serializers.CharField(), required=False)
    feed_type = serializers.CharField()
    likes_count = serializers.IntegerField()
    comments_count = serializers.IntegerField()
    created_at = serializers.DateTimeField(read_only=True)

class MongoCommentSerializer(serializers.Serializer):
    """社区评论序列化器 (后台查看/审核用)"""
    id = serializers.CharField(read_only=True)
    user_id = serializers.IntegerField()
    content = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)
    
    # 提取关联的帖子 ID
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # 兼容 ReferenceField 对象取值
        data['feed_id'] = str(instance.feed_id.id) if instance.feed_id else None
        return data