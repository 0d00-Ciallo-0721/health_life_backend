from rest_framework import serializers
from apps.users.models import Profile 
from apps.diet.models import UserPreference

class ProfileSerializer(serializers.ModelSerializer):
    # 显式声明 nickname 字段，关联到 user.nickname
    nickname = serializers.CharField(source='user.nickname', required=False)

    class Meta:
        model = Profile
        fields = [
            'nickname', 'gender', 'height', 'weight', 'age', 
            'activity_level', 'diet_tags', 'allergens', 
            'daily_kcal_limit', 'goal_type'
        ]
        read_only_fields = ['daily_kcal_limit']

    def update(self, instance, validated_data):
        # 提取 nickname (因为它属于 User 表)
        user_data = validated_data.pop('user', {})
        nickname = user_data.get('nickname')
        
        if nickname:
            instance.user.nickname = nickname
            instance.user.save() # 保存到 User 表

        return super().update(instance, validated_data)

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