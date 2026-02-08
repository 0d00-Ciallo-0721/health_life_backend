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