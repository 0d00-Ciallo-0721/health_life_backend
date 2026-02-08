from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.users.models import Profile
from apps.diet.serializers.preferences import ProfileSerializer
from apps.diet.domains.preferences.services import PreferenceService
from apps.diet.domains.preferences.selectors import PreferenceSelector

class ProfileUpdateView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer
    def get_object(self):
        obj, _ = Profile.objects.get_or_create(user=self.request.user)
        return obj
    def perform_update(self, serializer):
        instance = serializer.save()
        instance.calculate_and_save_daily_limit()

class PreferenceOperationView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        target_id = request.data.get('item_id') or request.data.get('target_id')
        target_type = request.data.get('item_type') or request.data.get('target_type')
        action = request.data.get('action')
        
        if not all([target_id, target_type, action]):
            return Response({"code": 400, "msg": "缺少参数"}, status=400)
            
        res = PreferenceService.toggle_preference(request.user, target_id, target_type, action)
        if res is False: return Response({"code": 400, "msg": "无效操作"}, status=400)
        return Response({"code": 200, "msg": "操作成功", "data": {"status": res == "added", "action": action}})

class FavoriteListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        data = PreferenceSelector.get_user_favorites(
            request.user, 
            request.query_params.get('type', 'all'), 
            int(request.query_params.get('page', 1))
        )
        return Response({"code": 200, "data": data})