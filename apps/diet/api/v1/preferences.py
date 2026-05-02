import logging

from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.diet.domains.preferences.services import PreferenceService
from apps.diet.serializers.preferences import ProfileSerializer
from apps.users.models import Profile


logger = logging.getLogger(__name__)


class ProfileUpdateView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self):
        obj, _ = Profile.objects.get_or_create(user=self.request.user)
        return obj

    def post(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def perform_update(self, serializer):
        instance = serializer.save()
        if "avatar" in self.request.FILES and instance.avatar:
            new_avatar_url = self.request.build_absolute_uri(instance.avatar.url)
            if instance.user.avatar != new_avatar_url:
                instance.user.avatar = new_avatar_url
                instance.user.save(update_fields=["avatar"])
        instance.calculate_and_save_daily_limit()
        instance.save(update_fields=["bmr", "daily_kcal_limit"])


class PreferenceOperationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        target_id = request.data.get("item_id") or request.data.get("target_id")
        target_type = request.data.get("item_type") or request.data.get("target_type")
        action = request.data.get("action")

        if not all([target_id, target_type, action]):
            return Response({"code": 400, "msg": "缺少参数"}, status=400)

        result = PreferenceService.toggle_preference(request.user, target_id, target_type, action)
        if result is False:
            return Response({"code": 400, "msg": "无效操作"}, status=400)
        return Response({"code": 200, "msg": "操作成功", "data": {"status": result == "added", "action": action}})


class FavoriteListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        filter_type = request.query_params.get("type", "all")
        try:
            results = PreferenceService.get_favorites(request.user, filter_type=filter_type)
            results.reverse()
            return Response({"code": 200, "msg": "success", "data": results})
        except Exception as exc:
            logger.exception("Failed to fetch favorite list", exc_info=exc)
            return Response({"code": 500, "msg": "获取收藏列表失败", "data": None}, status=500)
