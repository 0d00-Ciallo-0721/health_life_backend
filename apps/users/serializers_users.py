from rest_framework import serializers

from apps.diet.domains.community.services import CommunityService
from apps.diet.domains.gamification.services import GamificationService

from .models import Profile, User, UserFollow


class ProfileSerializer(serializers.ModelSerializer):
    nickname = serializers.CharField(source="user.nickname", required=False)
    avatar = serializers.SerializerMethodField()
    follow_count = serializers.SerializerMethodField()
    fans_count = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    badges = serializers.SerializerMethodField()
    featured_badges = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "nickname",
            "avatar",
            "signature",
            "gender",
            "height",
            "weight",
            "target_weight",
            "age",
            "activity_level",
            "diet_tags",
            "allergens",
            "daily_kcal_limit",
            "bmr",
            "goal_type",
            "water_goal_cups",
            "water_goal_ml",
            "follow_count",
            "fans_count",
            "like_count",
            "badges",
            "featured_badges",
        ]
        read_only_fields = [
            "daily_kcal_limit",
            "bmr",
            "follow_count",
            "fans_count",
            "like_count",
            "badges",
            "featured_badges",
        ]

    def get_avatar(self, obj):
        request = self.context.get("request")
        avatar_url = ""
        if obj.avatar:
            avatar_url = obj.avatar.url
        elif obj.user.avatar:
            avatar_url = obj.user.avatar

        if avatar_url and request:
            return request.build_absolute_uri(avatar_url)
        return avatar_url

    def get_follow_count(self, obj):
        return UserFollow.objects.filter(follower=obj.user).count()

    def get_fans_count(self, obj):
        return UserFollow.objects.filter(followed=obj.user).count()

    def get_like_count(self, obj):
        profile = CommunityService.get_user_profile(obj.user_id, obj.user_id)
        return profile.get("like_count", 0) if profile else 0

    def get_badges(self, obj):
        achievements = GamificationService.get_merged_achievements(obj.user)
        return [
            {"id": achievement["id"], "name": achievement["name"], "icon": achievement["icon"]}
            for achievement in achievements
            if achievement.get("unlocked")
        ]

    def get_featured_badges(self, obj):
        return GamificationService.get_user_featured_badges(obj.user_id)

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        if "nickname" in user_data:
            instance.user.nickname = user_data["nickname"]
            instance.user.save(update_fields=["nickname"])
        return super().update(instance, validated_data)


class PublicProfileSerializer(serializers.ModelSerializer):
    nickname = serializers.CharField(source="user.nickname", read_only=True)
    avatar = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    follow_count = serializers.SerializerMethodField()
    fans_count = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "nickname",
            "avatar",
            "signature",
            "gender",
            "follow_count",
            "fans_count",
            "like_count",
            "is_following",
        ]

    def get_avatar(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return obj.user.avatar if hasattr(obj.user, "avatar") else ""

    def get_follow_count(self, obj):
        return UserFollow.objects.filter(follower=obj.user).count()

    def get_fans_count(self, obj):
        return UserFollow.objects.filter(followed=obj.user).count()

    def get_like_count(self, obj):
        profile = CommunityService.get_user_profile(obj.user_id, obj.user_id)
        return profile.get("like_count", 0) if profile else 0

    def get_is_following(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            from .services import UserFollowService

            return UserFollowService.is_following(request.user, obj.user)
        return False
