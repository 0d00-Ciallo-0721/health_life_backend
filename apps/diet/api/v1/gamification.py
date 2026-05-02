from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum
import datetime
from django.shortcuts import get_object_or_404
import json
from django.core.cache import cache
from apps.diet.domains.tools.ai_service import AIService
from apps.diet.models.mysql.gamification import Achievement, UserAchievement, UserChallengeProgress, UserRemedyPlan
from apps.diet.domains.gamification.services import GamificationService

from apps.diet.models import ChallengeTask, Remedy, DailyIntake
from apps.diet.models.mysql.journal import WorkoutRecord

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
        
        # 预取今日数据，减少循环查库
        today_intakes = list(DailyIntake.objects.filter(user=request.user, record_date=today))
        today_workouts = list(WorkoutRecord.objects.filter(user=request.user, date=today))
        
        # 2. 动态计算状态
        for t in tasks_db:
            status = 'pending'
            
            # 判断逻辑
            if t.condition_code == 'log_breakfast':
                has = any(log.meal_time == 'breakfast' for log in today_intakes)
                if has: status = 'completed'
                
            elif t.condition_code == 'log_dinner':
                has = any(log.meal_time == 'dinner' for log in today_intakes)
                if has: status = 'completed'
                
            elif t.condition_code == 'workout':
                if len(today_workouts) > 0: status = 'completed'
                
            elif t.condition_code == 'no_sugar':
                # 简单试探：看看食物名称里有没有带糖，或者带甜点的
                bad_words = ['糖', '奶茶', '蛋糕', '甜品', '饼干', '巧克力']
                has_sugar = any(any(bw in str(log.food_name) for bw in bad_words) for log in today_intakes)
                # 尚未吃含糖食品，并且吃了其他饭才算成功，为了防作弊暂且简化为：
                if len(today_intakes) > 0 and not has_sugar:
                    status = 'completed'
                elif has_sugar:
                    status = 'failed'
                
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
            
        data = [{"id": s.id, "name": s.title, "recipe": s.desc, "icon": "💡"} for s in solutions]
        return Response({"code": 200, "data": {"solutions": data}})

class RemedyTriageView(APIView):
    """
    对症下药智能分诊接口
    POST /remedy/triage/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        action_text = request.data.get('action_text', '')
        custom_keywords = request.data.get('custom_keywords', [])
        symptom_ids = request.data.get('symptom_ids', []) # 预留字段，可结合后续映射表使用
        
        if not action_text and not custom_keywords and not symptom_ids:
            return Response({"code": 400, "msg": "请提供至少一项症状描述或关键词"})

        # 取出所有备选方案喂给大模型
        # (控制传入的字段，避免 token 浪费，同时包含 desc 摘要帮助模型判断)
        remedies = Remedy.objects.all()
        remedy_list = [{
            "id": r.id, 
            "title": r.title, 
            "scenario": r.scenario, 
            "desc": r.desc[:80] + "..." if len(r.desc) > 80 else r.desc
        } for r in remedies]
        
        # 调用大模型智能分诊引擎
        ai_result = AIService.triage_symptoms(
            action_text=action_text,
            custom_keywords=custom_keywords,
            available_remedies_json=json.dumps(remedy_list, ensure_ascii=False)
        )
        
        # 将推荐的 ID 映射回完整的解决方案数据返回给前端
        final_solutions = []
        for rec in ai_result.get('recommended_solutions', []):
            try:
                r_obj = Remedy.objects.get(id=rec.get('remedy_id'))
                final_solutions.append({
                    "id": str(r_obj.id),
                    "name": r_obj.title,
                    "recipe": r_obj.desc,
                    "icon": getattr(r_obj, 'icon', '💡'),
                    "reason": rec.get('reason', '')
                })
            except Remedy.DoesNotExist:
                continue

        # 格式化识别出的症状，符合前端 {id, score, reason} 结构契约
        matched_symptoms = ai_result.get('matched_symptoms', [])
        formatted_symptoms = [
            {"id": f"sym_{i}", "score": 95, "reason": sym} 
            for i, sym in enumerate(matched_symptoms)
        ]

        return Response({
            "code": 200, 
            "msg": "success",
            "data": {
                "matched_symptoms": formatted_symptoms,
                "recommended_solutions": final_solutions
            }
        })

class CarbonFootprintView(APIView):
    """
    绿色足迹 (最小化闭环)
    GET /carbon/summary/ (向下兼容 /carbon/footprint/)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_str = request.query_params.get('date')
        if not date_str:
            date = timezone.now().date()
            date_str = str(date)
        else:
            try:
                date = datetime.date.fromisoformat(date_str)
            except ValueError:
                date = timezone.now().date()
                date_str = str(date)
                
        # 1. 饮食碳排: 假定 1.2g CO2e / kcal，转换为 kg
        logs = DailyIntake.objects.filter(user=request.user, record_date=date)
        total_cals = sum([log.calories or 0 for log in logs])
        food_kg = round((total_cals * 1.2) / 1000, 2)
        
        # 2. 运动抵消: 假定每消耗 1kcal 抵消 2.0g CO2e，转换为 kg (前端要求负数展示)
        workouts = WorkoutRecord.objects.filter(user=request.user, date=date)
        sport_duration = sum([w.duration or 0 for w in workouts]) # 汇总分钟
        sport_calories = sum([w.calories_burned or 0 for w in workouts])
        
        sport_offset_kg_positive = round((sport_calories * 2.0) / 1000, 2)
        sport_offset_kg = -sport_offset_kg_positive if sport_offset_kg_positive > 0 else 0.0
        
        # 3. 模拟额外维度（保持扩展性）
        travel_kg = 0.0
        package_kg = 0.0
        
        # 4. 计算总量与评级
        total_kg = round(food_kg + travel_kg + package_kg + sport_offset_kg, 2)
        if total_kg < 0:
            total_kg = 0.0  # 总排放不为负
            
        if total_kg == 0 and food_kg == 0:
            level = 'low' # 当日无记录降级
        elif total_kg <= 2.5:
            level = 'low'
        elif total_kg <= 5.0:
            level = 'medium'
        else:
            level = 'high'
            
        # 5. 构建运动卡片结构
        today_workout = None
        if workouts.exists():
            today_workout = {
                "distance_km": round((sport_duration / 60) * 8, 1), # 结合时长估算个距离配速
                "duration_sec": sport_duration * 60,
                "calories_kcal": sport_calories,
                "offset_kg": sport_offset_kg
            }

        # 严格遵守契约返回
        return Response({
            "code": 200, 
            "msg": "success",
            "data": {
                "date": date_str,
                "total_kg": total_kg,
                "level": level,
                "breakdown": {
                    "food_kg": food_kg,
                    "travel_kg": travel_kg,
                    "package_kg": package_kg,
                    "sport_offset_kg": sport_offset_kg
                },
                "today_workout": today_workout
            }
        })
    

class UserFeaturedBadgeView(APIView):
    """
    配置个性名片代表徽章
    POST /achievements/featured/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        achievement_ids = request.data.get('achievement_ids', [])
        
        if not isinstance(achievement_ids, list):
            return Response({"code": 400, "msg": "achievement_ids 必须是一个数组格式"})
            
        if len(achievement_ids) > 3:
            return Response({"code": 400, "msg": "最多只能设置3个代表徽章"})
            
        from apps.diet.models.mysql.gamification import UserFeaturedBadge, Achievement
        from django.db import transaction
        
        # 校验传入的ID是否真实存在
        valid_achievements = Achievement.objects.filter(id__in=achievement_ids)
        valid_ids = [a.id for a in valid_achievements]
        
        with transaction.atomic():
            # 先清空该用户之前的代表徽章
            UserFeaturedBadge.objects.filter(user=request.user).delete()
            
            # 按前端传来的数组顺序插入新数据，记录 sort_order
            new_badges = []
            for index, a_id in enumerate(achievement_ids):
                if int(a_id) in valid_ids:
                    new_badges.append(UserFeaturedBadge(
                        user=request.user,
                        achievement_id=a_id,
                        sort_order=index
                    ))
            
            if new_badges:
                UserFeaturedBadge.objects.bulk_create(new_badges)
                
        return Response({"code": 200, "msg": "名片徽章配置成功"})

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
    """
    我的成就/荣誉墙列表
    GET /achievements/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.diet.models.mysql.gamification import Achievement, UserAchievement
        
        # 1. 获取所有的成就字典数据
        all_achievements = Achievement.objects.all().order_by('category', 'id')
        
        # 2. 获取当前用户已解锁的成就记录
        unlocked_qs = UserAchievement.objects.filter(user=request.user)
        # 构建 HashMap 提升查询效率 {achievement_id: unlocked_at}
        unlocked_map = {ua.achievement_id: ua.unlocked_at for ua in unlocked_qs}
        
        data = []
        for ach in all_achievements:
            is_unlocked = ach.id in unlocked_map
            unlocked_time = unlocked_map[ach.id].strftime('%Y-%m-%d %H:%M:%S') if is_unlocked else None
            
            data.append({
                "id": str(ach.id),
                "name": ach.title,
                "description": ach.desc,
                "icon": ach.icon or "🏅",
                "category": ach.category,
                "rarity": ach.rarity,
                "points": ach.points,
                "unlocked": is_unlocked,
                "unlocked_at": unlocked_time
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
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not start_date_str or not end_date_str:
            today = timezone.now().date()
            start_date = today - datetime.timedelta(days=today.weekday())
            end_date = start_date + datetime.timedelta(days=6)
        else:
            try:
                start_date = datetime.date.fromisoformat(start_date_str)
                end_date = datetime.date.fromisoformat(end_date_str)
            except ValueError:
                return Response({"code": 400, "msg": "日期格式错误"})

        # 获取7天所有数据并在内存组装，防止某些数据库的 SQL 聚合问题
        intakes = DailyIntake.objects.filter(user=request.user, record_date__range=(start_date, end_date))
        workouts = WorkoutRecord.objects.filter(user=request.user, date__range=(start_date, end_date))
        
        daily_food_kg = {}
        for l in intakes:
            d_str = str(l.record_date)
            # 同样转换规则: 1.2g CO2 per kcal
            daily_food_kg[d_str] = daily_food_kg.get(d_str, 0) + (l.calories or 0) * 1.2 / 1000

        daily_sport_offset = {}
        for w in workouts:
            d_str = str(w.date)
            # 2.0g CO2 per kcal burned
            daily_sport_offset[d_str] = daily_sport_offset.get(d_str, 0) + (w.calories_burned or 0) * 2.0 / 1000

        total_saved = 0.0
        daily_data = []
        
        num_days = (end_date - start_date).days + 1
        for i in range(num_days):
            curr = start_date + datetime.timedelta(days=i)
            c_str = str(curr)
            # 我们假设如果一个人一天吃少于他应有的碳排放，就叫saved。
            
            f_kg = daily_food_kg.get(c_str, 0)
            offset = daily_sport_offset.get(c_str, 0)
            
            val_kg = max(f_kg - offset, 0)
            daily_data.append({"date": c_str, "val": round(val_kg, 2)})
            total_saved += max(offset, 0)
            
        data = {
            "total_saved": round(total_saved, 2),
            "trend": "up" if total_saved > 2 else "down",
            "daily_data": daily_data
        }
        return Response({"code": 200, "msg": "success", "data": data})

class CarbonSuggestionView(APIView):
    """环保建议: GET /diet/carbon/suggestions/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cache_key = f"carbon_suggestions_{request.user.id}"
        cached = cache.get(cache_key)
        if cached:
            return Response({"code": 200, "msg": "success", "data": cached})
            
        # 给模型提供一点最近3天的饮食信息
        three_days_ago = timezone.now().date() - datetime.timedelta(days=3)
        logs = DailyIntake.objects.filter(user=request.user, record_date__gte=three_days_ago)
        
        summary_lines = []
        for log in logs:
            summary_lines.append(f"{log.food_name} ({log.calories}kcal)")
            
        recent_str = "无" if not summary_lines else ", ".join(summary_lines)
        
        suggestions = AIService.generate_carbon_suggestions(recent_str)
        if suggestions:
            cache.set(cache_key, suggestions, timeout=43200)

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
            
        return Response({"code": 200, "msg": "success", "data": data})    
    

# [新增] 补救方案收藏视图
class RemedyFavoriteView(APIView):
    """
    收藏/取消收藏补救方案
    POST /remedy/favorite/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        remedy_id = request.data.get("remedy_id")
        if not remedy_id:
            return Response({"code": 400, "msg": "缺少 remedy_id 参数"})
        
        res = GamificationService.toggle_remedy_favorite(request.user.id, remedy_id)
        if "error" in res:
            return Response({"code": 400, "msg": res["error"]})
        return Response({"code": 200, "msg": "操作成功", "data": res})

# [新增] 兼容前端的挑战进度更新视图
class ChallengeTaskProgressCompatView(APIView):
    """
    更新挑战进度 (兼容前端路径)
    POST /challenge/tasks/{taskId}/progress/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, taskId):
        progress_val = request.data.get("progress")
        if progress_val is None:
            return Response({"code": 400, "msg": "缺少 progress 参数"})
            
        res = GamificationService.update_task_progress_compat(request.user, taskId, progress_val)
        if "error" in res:
            return Response({"code": 400, "msg": res["error"]})
        return Response({"code": 200, "msg": "进度已更新", "data": res})    
    
class ChallengeTaskDetailView(APIView):
    """
    获取单条健康挑战任务的详情
    GET /challenge/tasks/{pk}/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        # 查询对应的任务数据，如果不存在则返回 404
        task = get_object_or_404(ChallengeTask, pk=pk)
        
        # 组装返回数据结构
        data = {
            "id": task.id,
            "title": task.title,
            "desc": task.desc,
            "reward_points": task.reward_points,
            "condition_code": task.condition_code,
            "is_active": task.is_active,
            # 如果模型中有其他需要的字段（如时长、封面图等），可在此处补充
        }

        return Response({
            "code": 200,
            "msg": "success",
            "data": data
        })
