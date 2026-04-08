from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

from apps.users.models import Profile
from apps.diet.serializers.preferences import ProfileSerializer
from apps.diet.domains.preferences.services import PreferenceService
from apps.diet.domains.preferences.selectors import PreferenceSelector

class ProfileUpdateView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer
    # [新增] 显式增加多部分解析器，确保支持 wx.uploadFile 的头像上传
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self):
        obj, _ = Profile.objects.get_or_create(user=self.request.user)
        return obj

    def post(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def perform_update(self, serializer):
        # 1. 执行原有的保存逻辑
        instance = serializer.save()
        
        # 2. [核心修复] 数据同步：
        # 只有当用户确实通过表单文件上传了"新物理头像"时，才用新物理文件的URL覆盖 user.avatar
        # 如果是切换默认头像（纯字符串），不会触发此条件，避免把刚更新的默认头像又用旧文件覆盖掉
        if 'avatar' in self.request.FILES and instance.avatar:
            new_avatar_url = self.request.build_absolute_uri(instance.avatar.url)
            if instance.user.avatar != new_avatar_url:
                instance.user.avatar = new_avatar_url
                instance.user.save(update_fields=['avatar'])
        
        # 3. 计算并保存每日限额
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
    """
    获取用户的收藏列表 (混合 MySQL 与 MongoDB 聚合查询)
    GET /diet/favorites/?type=all|recipe|restaurant
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        filter_type = request.query_params.get('type', 'all')
        
        try:
            # 直接调用 Service 层已实现好的跨库聚合引擎，规避原来的模型导入错误和 action 映射错误
            results = PreferenceService.get_favorites(request.user, filter_type=filter_type)
            
            # 由于 Service 层未排序，我们在视图层统一做一次时间倒序展示最新收藏
            results.reverse() 
            
            return Response({
                "code": 200, 
                "msg": "success", 
                "data": results
            })
            
        except Exception as e:
            # 捕获异常并打印到 runserver 控制台，方便后续排查
            import traceback
            traceback.print_exc()
            
            # [核心修改点]：严格遵循前端约定，即使后端抛错也返回 200 + 空数组，避免向前端抛出 500 导致页面白屏崩溃
            return Response({
                "code": 200, 
                "msg": "获取收藏列表异常，已提供兜底空数据", 
                "data": []
            })