from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser
from django.db.models import Sum
from django.utils import timezone

from apps.diet.domains.tools.ai_service import AIService
from apps.diet.models import DailyIntake
from apps.users.models import Profile

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