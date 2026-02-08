from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum
import datetime

from apps.diet.models import ChallengeTask, Remedy, DailyIntake

class ChallengeTaskView(APIView):
    """
    健康挑战任务 (DB 驱动)
    GET /challenge/tasks/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. 从数据库读取所有启用任务
        tasks_db = ChallengeTask.objects.filter(is_active=True)
        
        results = []
        today = timezone.now().date()
        
        # 2. 动态计算状态 (逻辑仍需代码处理，但规则来自 DB)
        for t in tasks_db:
            status = 'pending'
            
            if t.condition_code == 'log_breakfast':
                # 检查是否记录早餐
                has = DailyIntake.objects.filter(
                    user=request.user, record_date=today, meal_time='breakfast'
                ).exists()
                if has: status = 'completed'
                
            elif t.condition_code == 'no_sugar':
                # 简单逻辑：还没记录就算进行中，记录了含糖则失败 (这里简化为手动打卡或一直 pending)
                # 实际业务可能需要更复杂的判定
                pass 
                
            results.append({
                "id": t.id,
                "title": t.title,
                "desc": t.desc,
                "reward": t.reward_points,
                "status": status
            })
            
        return Response({"code": 200, "data": results})

class RemedySolutionView(APIView):
    """
    补救方案 (DB 驱动)
    GET /remedy/solutions/?scenario=overeat
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        scenario = request.query_params.get('scenario', 'overeat')
        
        # [修改] 查库
        solutions = Remedy.objects.filter(scenario=scenario).order_by('order')
        
        if not solutions.exists():
            # 尝试用默认 'overeat'
            solutions = Remedy.objects.filter(scenario='overeat').order_by('order')
            
        data = [{"title": s.title, "desc": s.desc} for s in solutions]
        return Response({"code": 200, "data": data})

class CarbonFootprintView(APIView):
    """
    碳足迹 (计算逻辑)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 逻辑计算本身就是基于数据库数据的，不需要额外建表存储“系数”
        # 除非你想动态配置系数，否则当前逻辑已满足“基于数据库数据”
        date_str = request.query_params.get('date')
        date = datetime.date.fromisoformat(date_str) if date_str else timezone.now().date()
            
        logs = DailyIntake.objects.filter(user=request.user, record_date=date)
        total_cals = logs.aggregate(t=Sum('calories'))['t'] or 0
        
        carbon_g = int(total_cals * 1.2) # 系数可硬编码
        trees = round(carbon_g / 60, 1)
        
        return Response({
            "code": 200, 
            "data": {
                "date": str(date),
                "total_carbon_g": carbon_g,
                "equivalent_trees": trees
            }
        })