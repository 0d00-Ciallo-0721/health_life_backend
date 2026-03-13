from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum
import datetime

from apps.diet.models.mysql.gamification import ChallengeTask, Remedy, UserChallengeProgress, UserRemedyPlan, Achievement, UserAchievement
from apps.diet.domains.gamification.services import GamificationService

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
    


# [新增] 加入挑战视图
class ChallengeJoinView(APIView):
    """加入挑战: POST /diet/challenge/tasks/{challengeId}/join/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, challengeId):
        res = GamificationService.join_challenge(request.user, challengeId)
        if "error" in res:
            return Response({"code": 400, "msg": res["error"]}, status=400)
        return Response({"code": 200, "msg": "success", "data": res})

# [新增] 我的挑战进度视图
class ChallengeProgressView(APIView):
    """我的挑战进度: GET /diet/challenge/progress/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        status = request.query_params.get('status', 'pending')
        progresses = UserChallengeProgress.objects.filter(user=request.user, status=status).select_related('challenge')
        
        data = []
        for p in progresses:
            data.append({
                "progress_id": p.id,
                "challenge_id": p.challenge_id,
                "title": p.challenge.title,
                "status": p.status,
                "progress": p.progress
            })
        return Response({"code": 200, "msg": "success", "data": data})

# [新增] 检查/放弃挑战视图
class ChallengeProgressActionView(APIView):
    """更新进度 (打卡/放弃): POST /diet/challenge/progress/{progressId}/{action}/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, progressId, action):
        if action not in ['check', 'abandon']:
            return Response({"code": 400, "msg": "非法操作"}, status=400)
            
        res = GamificationService.update_progress(request.user, progressId, action)
        if "error" in res:
            return Response({"code": 400, "msg": res["error"]}, status=400)
        return Response({"code": 200, "msg": "success", "data": res})

# [新增] 排行榜视图
class LeaderboardView(APIView):
    """获取排行榜: GET /diet/challenge/leaderboard/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        board_type = request.query_params.get('type', 'weekly')
        scope = request.query_params.get('scope', 'global')
        data = GamificationService.get_leaderboard(board_type, scope)
        return Response({"code": 200, "msg": "success", "data": data})

# [新增] 成就视图
class AchievementView(APIView):
    """我的成就列表: GET /diet/achievements/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        my_achievements = UserAchievement.objects.filter(user=request.user).values_list('achievement__code', flat=True)
        all_achievements = Achievement.objects.all()
        
        data = []
        for a in all_achievements:
            data.append({
                "code": a.code,
                "title": a.title,
                "desc": a.desc,
                "unlocked": a.code in my_achievements
            })
        return Response({"code": 200, "msg": "success", "data": data})

# [新增] 添加补救方案至计划视图
class RemedyPlanActionView(APIView):
    """加入补救计划: POST /diet/remedy/add-to-plan/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        remedy_id = request.data.get('remedy_id')
        if not remedy_id:
            return Response({"code": 400, "msg": "缺少 remedy_id"}, status=400)
            
        try:
            remedy = Remedy.objects.get(id=remedy_id)
            UserRemedyPlan.objects.get_or_create(user=request.user, remedy=remedy)
            return Response({"code": 200, "msg": "已加入今日补救计划"})
        except Remedy.DoesNotExist:
            return Response({"code": 404, "msg": "补救方案不存在"}, status=404)    
        

class CarbonWeeklyView(APIView):
    """周碳足迹报告: GET /diet/carbon/footprint/weekly/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        # 这里接入具体的周统计逻辑，暂时返回默认结构
        data = {
            "total_saved": 15.4,  # kg
            "trend": "down",
            "daily_data": [{"date": start_date, "val": 2.1}]
        }
        return Response({"code": 200, "msg": "success", "data": data})

class CarbonSuggestionView(APIView):
    """环保建议: GET /diet/carbon/suggestions/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 写死的规则策略 (后续可接大模型)
        suggestions = [
            {"title": "多吃植物蛋白", "desc": "今日肉类摄入较高，建议明后天尝试豆制品。"},
            {"title": "光盘行动", "desc": "减少厨余垃圾能有效降低碳排放。"}
        ]
        return Response({"code": 200, "msg": "success", "data": suggestions})        
    

class RemedyUsageHistoryView(APIView):
    """补救方案使用历史: GET /diet/remedy/usage-history/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
        except ValueError:
            page, page_size = 1, 20

        skip = (page - 1) * page_size
        # 查询 UserRemedyPlan 表，关联查询 Remedy 详情
        history_qs = UserRemedyPlan.objects.filter(user=request.user).select_related('remedy').order_by('-added_at')
        total = history_qs.count()
        
        data = []
        for plan in history_qs[skip:skip+page_size]:
            data.append({
                "id": plan.id,
                "remedy_title": plan.remedy.title if plan.remedy else "未知方案",
                "remedy_desc": plan.remedy.desc if plan.remedy else "",
                "added_at": plan.added_at.strftime('%Y-%m-%d %H:%M:%S'),
                "is_completed": plan.is_completed
            })
        
        return Response({
            "code": 200, 
            "msg": "success", 
            "data": {
                "total": total,
                "page": page,
                "list": data
            }
        })

# [新增] 碳足迹历史趋势视图
class CarbonHistoryView(APIView):
    """碳足迹历史: GET /diet/carbon/footprint/history/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 提取过去半年的数据进行按月聚合计算
        six_months_ago = timezone.now().date() - datetime.timedelta(days=180)
        logs = DailyIntake.objects.filter(user=request.user, record_date__gte=six_months_ago).values('record_date', 'calories')
        
        # 在内存中按月聚合，避免 SQLite 和 MySQL 在 TruncMonth 上的方言兼容性问题
        monthly_data = {}
        for log in logs:
            if not log['record_date']: continue
            month_str = log['record_date'].strftime('%Y-%m')
            cals = log['calories'] or 0
            monthly_data[month_str] = monthly_data.get(month_str, 0) + cals
        
        trend = []
        for month, cals in sorted(monthly_data.items()):
            carbon_g = int(cals * 1.2) # 同样的系数逻辑
            trend.append({
                "month": month,
                "carbon_saved": carbon_g,
                "trees": round(carbon_g / 60, 1)
            })
            
        return Response({"code": 200, "msg": "success", "data": {"trend": trend}})

# [新增] 碳足迹专属成就视图
class CarbonAchievementView(APIView):
    """环保成就: GET /diet/carbon/achievements/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 仅查询 code 带有 'carbon_' 前缀的专属环保成就
        carbon_achievements = Achievement.objects.filter(code__startswith='carbon_')
        unlocked_codes = UserAchievement.objects.filter(
            user=request.user, 
            achievement__in=carbon_achievements
        ).values_list('achievement__code', flat=True)
        
        data = []
        for a in carbon_achievements:
            data.append({
                "code": a.code,
                "title": a.title,
                "desc": a.desc,
                "unlocked": a.code in unlocked_codes
            })
            
        # 如果数据库中尚未配置 carbon_ 前缀的成就，提供兜底的默认展示数据，防止前端页面空窗报错
        if not data:
            data = [
                {"code": "carbon_1", "title": "初级环保卫士", "desc": "累计减少碳排放 1kg", "unlocked": True},
                {"code": "carbon_2", "title": "种树小能手", "desc": "累计等效种树 1 棵", "unlocked": False}
            ]
            
        return Response({"code": 200, "msg": "success", "data": data})    