import uuid

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from apps.users.models import Profile
from apps.diet.models.mongo.restaurant import Restaurant
from apps.diet.models.mysql.gamification import Achievement, ChallengeTask, Remedy


User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['gender', 'height', 'weight', 'age', 'goal_type', 'bmr', 'daily_kcal_limit']
        read_only_fields = ['bmr', 'daily_kcal_limit']


class AdminUserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'nickname', 'phone', 'avatar', 'is_active', 'date_joined', 'profile']
        read_only_fields = ['username', 'date_joined']


class MongoRecipeAuditSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.IntegerField(default=0)
    image_url = serializers.CharField(required=False, allow_blank=True)
    calories = serializers.IntegerField(required=False)
    created_at = serializers.DateTimeField(required=False)
    prep_time = serializers.IntegerField(source='cooking_time', required=False, read_only=True)
    tags = serializers.ListField(child=serializers.CharField(), required=False, read_only=True)
    author_name = serializers.CharField(required=False, allow_blank=True, read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        keywords = getattr(instance, 'keywords', None) or []
        if 'tags' not in data:
            data['tags'] = keywords[:3]
        if 'author_name' not in data:
            data['author_name'] = getattr(instance, 'author_name', '') or getattr(instance, 'author', '')
        return data


class MongoRestaurantSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    amap_id = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField()
    address = serializers.CharField(required=False, allow_blank=True)
    type = serializers.CharField(required=False, allow_blank=True)
    rating = serializers.FloatField(default=0.0, required=False)
    cost = serializers.FloatField(default=0.0, required=False)
    avg_price = serializers.FloatField(source='cost', default=0.0, required=False)
    location = serializers.ListField(
        child=serializers.FloatField(),
        min_length=2,
        max_length=2,
        required=False,
        write_only=True,
        help_text='[lng, lat]',
    )
    photos = serializers.ListField(child=serializers.CharField(), required=False)
    menu = serializers.ListField(child=serializers.DictField(), required=False)
    cached_at = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        validated_data.setdefault('amap_id', f'admin_{uuid.uuid4().hex}')
        validated_data.setdefault('location', [0.0, 0.0])
        return Restaurant.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        loc = getattr(instance, 'location', None)
        if loc:
            if isinstance(loc, dict) and 'coordinates' in loc:
                data['location'] = loc['coordinates']
            elif isinstance(loc, (list, tuple)):
                data['location'] = list(loc)
            elif hasattr(loc, 'coordinates'):
                data['location'] = list(loc.coordinates)
        data['avg_price'] = data.get('cost', 0.0)
        return data


class ChallengeTaskSerializer(serializers.ModelSerializer):
    desc = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(write_only=True, required=False, allow_blank=True)
    condition_code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = ChallengeTask
        fields = ['id', 'title', 'task_type', 'condition_code', 'reward_points', 'is_active', 'desc', 'description']

    def validate(self, attrs):
        description = attrs.pop('description', None)
        attrs['desc'] = description or attrs.get('desc') or attrs.get('title', '')
        attrs['condition_code'] = attrs.get('condition_code') or slugify(attrs.get('title', ''), allow_unicode=True).replace('-', '_') or 'task'
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['description'] = data.get('desc', '')
        return data


class RemedySerializer(serializers.ModelSerializer):
    scenario_display = serializers.CharField(source='get_scenario_display', read_only=True)
    desc = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Remedy
        fields = ['id', 'scenario', 'scenario_display', 'title', 'desc', 'description', 'points_cost', 'order']

    def validate(self, attrs):
        description = attrs.pop('description', None)
        attrs['desc'] = description or attrs.get('desc') or attrs.get('title', '')
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['description'] = data.get('desc', '')
        return data


class AchievementSerializer(serializers.ModelSerializer):
    category = serializers.CharField(required=False, allow_blank=True)

    def validate_category(self, value):
        valid_values = {choice for choice, _ in Achievement._meta.get_field('category').choices}
        return value if value in valid_values else 'special'

    class Meta:
        model = Achievement
        fields = '__all__'


class MongoCommunityFeedSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    user_id = serializers.IntegerField()
    content = serializers.CharField()
    images = serializers.ListField(child=serializers.CharField(), required=False)
    feed_type = serializers.CharField()
    likes_count = serializers.IntegerField()
    comments_count = serializers.IntegerField()
    is_hidden = serializers.BooleanField(required=False)
    is_pinned = serializers.BooleanField(required=False)
    created_at = serializers.DateTimeField(read_only=True)


class MongoCommentSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    user_id = serializers.IntegerField()
    content = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['feed_id'] = str(instance.feed_id.id) if instance.feed_id else None
        return data
