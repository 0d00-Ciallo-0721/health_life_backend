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

    def post(self, request, *args, **kwargs):
        # 兼容小程序的 POST 请求
        return self.partial_update(request, *args, **kwargs)

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
        # 1. 提取前端的分类过滤参数，默认为 all
        filter_type = request.query_params.get('type', 'all')
        
        # 2. 调用 Service 层的多态跨库聚合引擎
        from apps.diet.domains.preferences.services import PreferenceService
        data = PreferenceService.get_favorites(request.user, filter_type=filter_type)
        
        # 3. 经过多态序列化器格式化输出
        from apps.diet.serializers.preferences import FavoriteItemSerializer
        serializer = FavoriteItemSerializer(data, many=True)
        
        return Response({"code": 200, "msg": "success", "data": serializer.data})