from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser
from django.db.models import Sum
from django.utils import timezone
from django.core.cache import cache
import datetime

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
            # [核心修改]: 移除 status=500，使用默认的 HTTP 200 响应。
            # 依靠 JSON 体中的 "code": 500 告知前端发生错误，避免微信小程序因非 2xx 状态码直接进入 fail 回调抛出识别异常。
            return Response({"code": 500, "msg": res['error']})
            
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
        cache_key = f"health_warnings_{request.user.id}"
        cached_warnings = cache.get(cache_key)
        if cached_warnings:
            return Response({"code": 200, "msg": "success", "data": cached_warnings})

        # 获取近3天饮食数据
        three_days_ago = timezone.now().date() - datetime.timedelta(days=3)
        logs = DailyIntake.objects.filter(user=request.user, record_date__gte=three_days_ago)
        
        if not logs.exists():
            return Response({"code": 200, "msg": "success", "data": []})

        # 构建简要数据字符串
        summary_lines = []
        for log in logs:
            cals = log.calories or 0
            macros = log.macros or {}
            c = macros.get('carbohydrates', macros.get('carb', 0))
            p = macros.get('protein', 0)
            f = macros.get('fat', 0)
            summary_lines.append(f"{log.record_date} {log.get_meal_time_display()}: {log.food_name} ({cals}kcal, 碳水{c}g, 蛋白{p}g, 脂肪{f}g)")
        
        recent_logs_summary = "\n".join(summary_lines)
        profile = getattr(request.user, 'profile', None)

        warnings = AIService.generate_health_warnings(profile, recent_logs_summary)
        
        if warnings:
            # 缓存12小时
            cache.set(cache_key, warnings, timeout=43200)

        return Response({"code": 200, "msg": "success", "data": warnings})    