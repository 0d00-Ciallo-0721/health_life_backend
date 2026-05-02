import os
import time
import uuid

from django.core.files.storage import default_storage
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.exceptions import BusinessException
from apps.common.utils import WeChatService
from apps.diet.domains.community.services import CommunityService

from .models import Profile, User, UserFollow
from .serializers_users import ProfileSerializer
from .services import UserFollowService


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response({"code": 400, "msg": "缺少 refresh_token 参数"}, status=400)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response({"code": 400, "msg": "Token 无效或已过期"}, status=400)
        except Exception as exc:
            return Response({"code": 500, "msg": f"退出失败: {exc}"}, status=500)

        return Response({"code": 200, "msg": "退出登录成功"})


class WeChatLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        code = request.data.get("code")
        if not code:
            return Response({"code": 400, "msg": "missing code"}, status=400)

        try:
            wechat_data = WeChatService.get_openid(code)
        except Exception as exc:
            return Response({"code": 400, "msg": str(exc)}, status=400)

        openid = wechat_data.get("openid")
        if not openid:
            return Response({"code": 400, "msg": "openid 获取失败"}, status=400)

        with transaction.atomic():
            user, created = User.objects.get_or_create(
                openid=openid,
                defaults={"username": f"wx_{openid[:8]}_{int(time.time())}"},
            )
            Profile.objects.get_or_create(user=user)

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "code": 200,
                "msg": "success",
                "data": {
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                    "is_new_user": created,
                    "user_id": user.id,
                },
            }
        )


class UserMetaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile, _ = Profile.objects.get_or_create(user=user)
        days_joined = (timezone.now().date() - user.date_joined.date()).days + 1
        goal_map = {"lose": "减脂", "maintain": "维持", "gain": "增肌"}
        goal_display = goal_map.get(profile.goal_type, "未知")

        follow_count = UserFollow.objects.filter(follower=user).count()
        fans_count = UserFollow.objects.filter(followed=user).count()

        badges_data = []
        featured_badges_data = []
        like_count = 0
        try:
            from apps.diet.domains.gamification.services import GamificationService

            all_achievements = GamificationService.get_merged_achievements(user)
            badges_data = [
                {"id": achievement["id"], "name": achievement["name"], "icon": achievement["icon"]}
                for achievement in all_achievements
                if achievement.get("unlocked")
            ]
            featured_badges_data = GamificationService.get_user_featured_badges(user.id)
            community_profile = CommunityService.get_user_profile(user.id, user.id)
            like_count = community_profile.get("like_count", 0) if community_profile else 0
        except Exception:
            pass

        data = {
            "nickname": user.nickname,
            "avatar": profile.avatar.url if profile.avatar else (user.avatar or ""),
            "days_joined": days_joined,
            "goal_type": goal_display,
            "daily_limit": profile.daily_kcal_limit,
            "water_goal_cups": profile.water_goal_cups,
            "water_goal_ml": profile.water_goal_ml,
            "follow_count": follow_count,
            "fans_count": fans_count,
            "like_count": like_count,
            "badges": badges_data,
            "featured_badges": featured_badges_data,
        }
        return Response({"code": 200, "data": data})


class CurrentUserAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user_id = user.id

        with transaction.atomic():
            user.delete()

        try:
            from apps.diet.models.mongo.community import Comment, CommunityFeed

            user_feeds = list(CommunityFeed.objects.filter(user_id=user_id))
            if user_feeds:
                Comment.objects.filter(feed_id__in=user_feeds).delete()
                CommunityFeed.objects.filter(user_id=user_id).delete()
            Comment.objects.filter(user_id=user_id).delete()
        except Exception:
            pass

        return Response({"code": 200, "msg": "账号已注销", "data": None})


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, userId):
        data = CommunityService.get_user_profile(userId, request.user.id)
        if not data:
            return Response({"code": 404, "msg": "用户不存在"}, status=404)
        return Response({"code": 200, "msg": "success", "data": data})


class UserFollowView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, userId):
        try:
            UserFollowService.follow(request.user, userId)
            return Response({"code": 200, "msg": "关注成功", "data": None})
        except BusinessException as exc:
            return Response({"code": 400, "msg": str(exc)}, status=400)

    def delete(self, request, userId):
        try:
            UserFollowService.unfollow(request.user, userId)
            return Response({"code": 200, "msg": "已取消关注", "data": None})
        except BusinessException as exc:
            return Response({"code": 400, "msg": str(exc)}, status=400)


class UserPostsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, userId):
        target_user = get_object_or_404(User, id=userId)
        try:
            page = int(request.query_params.get("page", 1))
            size = int(request.query_params.get("size", 10))
        except ValueError:
            page, size = 1, 10

        posts_data = CommunityService.get_feed_list(
            page=page,
            page_size=size,
            current_user_id=request.user.id,
            query_user_id=target_user.id,
        )

        try:
            from apps.diet.models.mongo.community import CommunityFeed

            total = CommunityFeed.objects.filter(user_id=target_user.id).count()
        except Exception:
            total = len(posts_data) + (page - 1) * size

        return Response(
            {
                "code": 200,
                "msg": "success",
                "data": {
                    "list": posts_data,
                    "total": total,
                    "page": page,
                    "size": size,
                    "has_next": len(posts_data) == size,
                },
            }
        )


class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, JSONParser]

    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, context={"request": request})
        return Response({"code": 200, "data": serializer.data})

    def post(self, request):
        avatar_file = request.FILES.get("avatar")
        if not avatar_file:
            return Response({"code": 400, "msg": "未检测到上传文件字段: avatar"}, status=400)

        ext = os.path.splitext(avatar_file.name)[1]
        file_path = f"avatars/{request.user.id}_{uuid.uuid4().hex}{ext}"
        saved_path = default_storage.save(file_path, avatar_file)

        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.avatar = saved_path
        profile.save()

        request.user.avatar = default_storage.url(saved_path)
        request.user.save(update_fields=["avatar"])

        serializer = ProfileSerializer(profile, context={"request": request})
        return Response({"code": 200, "msg": "头像更新成功", "data": serializer.data})

    def patch(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response({"code": 200, "data": serializer.data})
        return Response({"code": 400, "msg": serializer.errors}, status=400)
