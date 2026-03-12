from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser
from django.db.models import Sum
from django.utils import timezone

from apps.diet.domains.tools.ai_service import AIService
from apps.diet.models import DailyIntake
from apps.users.models import Profile

from django.core.files.storage import default_storage
import uuid
import os

class AIFoodRecognitionView(APIView):
    """拍图识热量"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if not request.FILES.get('image'):
            return Response({"code": 400, "msg": "请上传图片"}, status=400)
        
        # 调用真实 AI
        res = AIService.recognize_food(request.FILES['image'])
        
        if "error" in res:
            return Response({"code": 500, "msg": res['error']}, status=500)
            
        return Response({"code": 200, "data": res})

class AINutritionistView(APIView):
    """AI 营养师分析"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        # 1. 获取档案
        profile = getattr(user, 'profile', None)
        if not profile:
            return Response({"code": 400, "msg": "请先完善身体档案"}, status=400)

        # 2. 获取今日数据
        today = timezone.now().date()
        logs = DailyIntake.objects.filter(user=user, record_date=today)
        total_calories = logs.aggregate(t=Sum('calories'))['t'] or 0
        
        # 3. 调用真实 AI
        advice = AIService.get_nutrition_advice(profile, logs, total_calories)
        
        return Response({
            "code": 200, 
            "data": {
                "advice": advice,
                "goal_type": profile.goal_type,
                "today_calories": total_calories
            }
        })
    


# [新增] AI 实时建议视图
class AIRealTimeAdviceView(APIView):
    """实时建议"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        context_data = request.data.get("context", "")
        res = AIService.generate_real_time_advice(context_data)
        
        if "error" in res:
            return Response({"code": 500, "msg": res['error']}, status=500)
            
        return Response({"code": 200, "msg": "success", "data": res})

# [新增] AI 智能问答视图
class AIChatView(APIView):
    """智能问答 (多轮对话)"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        question = request.data.get("question")
        if not question:
            return Response({"code": 400, "msg": "问题不能为空"}, status=400)
            
        # 接收前端传递的上下文数组
        context_messages = request.data.get("context", [])
        
        res = AIService.chat_with_ai(question, context_messages)
        if "error" in res:
            return Response({"code": 500, "msg": res['error']}, status=500)
            
        return Response({"code": 200, "msg": "success", "data": res})

# [新增] AI 附件上传视图
class AIAttachmentUploadView(APIView):
    """AI 附件/体检单等上传"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        upload_file = request.FILES.get('file')
        if not upload_file:
            return Response({"code": 400, "msg": "请上传文件"}, status=400)
            
        custom_name = request.data.get('name', upload_file.name)
        
        # 存储文件到媒体库 (ai_uploads/ 目录下)
        ext = os.path.splitext(upload_file.name)[1]
        filename = f"ai_uploads/{uuid.uuid4().hex}{ext}"
        saved_path = default_storage.save(filename, upload_file)
        file_url = default_storage.url(saved_path)
        
        # 返回前端约定的格式
        data = {
            "url": file_url,
            "name": custom_name,
            "mime_type": upload_file.content_type,
            "size": upload_file.size
        }
        return Response({"code": 200, "msg": "success", "data": data})    