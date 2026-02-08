from rest_framework import serializers
from .models import User, Profile

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'avatar', 'nickname']

class ProfileSerializer(serializers.ModelSerializer):
    # 1. 映射 User 表的昵称
    nickname = serializers.CharField(source='user.nickname', required=False)
    
    # 2. 头像字段 (只读，返回 URL字符串)
    # 图片上传走单独的 POST /diet/profile/avatar/ 接口
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            'nickname', 
            'avatar', 
            'signature',        # [新增] 个性签名
            'gender', 
            'height', 
            'weight', 
            'target_weight',    # [新增] 目标体重
            'age', 
            'activity_level', 
            'diet_tags', 
            'allergens', 
            'daily_kcal_limit', 
            'bmr',              # [新增] 基础代谢率 (自动计算)
            'goal_type'         # [新增] 目标类型
        ]
        # 自动计算字段设为只读
        read_only_fields = ['daily_kcal_limit', 'bmr']

    def get_avatar(self, obj):
        """
        优先返回 Profile 中上传的头像，如果没有则返回 User 中的微信头像
        """
        if obj.avatar:
            # 返回完整的媒体文件 URL (需配置 MEDIA_URL)
            return obj.avatar.url
        # 兜底：返回微信头像 (如果 User 模型里有存的话)
        return obj.user.avatar if hasattr(obj.user, 'avatar') else ""

    def update(self, instance, validated_data):
        """
        重写 update 以支持嵌套字段 (nickname) 的更新
        """
        # 提取 user 字典 (因为 source='user.nickname')
        user_data = validated_data.pop('user', {})
        
        # 1. 更新 User 表字段 (昵称)
        if 'nickname' in user_data:
            instance.user.nickname = user_data['nickname']
            instance.user.save()

        # 2. 更新 Profile 表字段
        return super().update(instance, validated_data)