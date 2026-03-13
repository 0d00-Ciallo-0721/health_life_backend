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
    

# [新增] 食材智能识别视图
class AIIngredientRecognitionView(APIView):
    """食材智能识别 (用于冰箱添加): POST /diet/ingredient/recognize/"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if not request.FILES.get('image'):
            return Response({"code": 400, "msg": "请上传图片"}, status=400)
        
        # 调用 AI Service 的新方法
        res = AIService.recognize_ingredient(request.FILES['image'])
        
        if "error" in res:
            return Response({"code": 500, "msg": res['error']}, status=500)
            
        return Response({"code": 200, "msg": "success", "data": res})

# [新增] AI 健康预警视图
class AIHealthWarningsView(APIView):
    """健康预警: GET /diet/ai-nutritionist/warnings/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 实际业务中，这里可以通过查询用户近期的 DailyIntake 记录，发现异常值（如连天超标、不吃早饭等）。
        # 为了不阻塞联调，先返回基于一定业务逻辑构造的静态提示池。
        warnings = [
            {
                "id": 1,
                "title": "膳食纤维不足",
                "desc": "您最近2天的蔬菜摄入量偏低，可能会影响肠道健康，建议今天安排一份清炒绿叶菜。",
                "level": "warning"  # warning, danger, info
            },
            {
                "id": 2,
                "title": "碳水连续超标",
                "desc": "监测到您昨日主食比例偏高，为了减脂目标，今天请注意控制米面摄入。",
                "level": "danger"
            }
        ]
        return Response({"code": 200, "msg": "success", "data": warnings})    