import datetime
import calendar
from django.db.models import Sum
from apps.diet.domains.journal.selectors import JournalSelector
from apps.diet.models import DailyIntake
from apps.users.models import Profile

class ReportService:
    @staticmethod
    def get_daily_summary(user, target_date):
        """获取每日汇总 (复原完整逻辑)"""
        logs = JournalSelector.get_daily_logs(user, target_date)
        total_intake = logs.aggregate(t=Sum('calories'))['t'] or 0
        
        # 宏量统计
        macro_stats = {"carbohydrates": 0.0, "protein": 0.0, "fat": 0.0}
        grouped = {"breakfast": [], "lunch": [], "dinner": [], "snack": [], "night_snack": []}
        
        for log in logs:
            # 完整复原 macros 取值逻辑
            nuts = log.macros or {}
            # 兼容处理 keys
            carb = nuts.get('carbohydrates') or nuts.get('carb', 0)
            prot = nuts.get('protein', 0)
            fat = nuts.get('fat', 0)
            
            macro_stats["carbohydrates"] += float(carb)
            macro_stats["protein"] += float(prot)
            macro_stats["fat"] += float(fat)
            
            # 分组
            k = log.meal_time if log.meal_time in grouped else "snack"
            time_str = ""
            if log.exact_time:
                time_str = log.exact_time.strftime("%H:%M")
                
            grouped[k].append({
                "id": log.id, 
                "food_name": log.food_name, 
                "calories": log.calories, 
                "source_type": log.source_type,
                "meal_time": time_str
            })

        # 计算进度
        profile, _ = Profile.objects.get_or_create(user=user)
        target = profile.daily_kcal_limit or 2000
        
        progress = (total_intake / target * 100) if target > 0 else 0
        health_level = "good"
        if progress < 90: health_level = "excellent"
        elif 90 <= progress < 110: health_level = "good"
        elif 110 <= progress < 130: health_level = "warning"
        else: health_level = "danger"
        
        # 宏量目标计算 (基于 Profile 目标类型)
        ratios = {"c": 0.5, "p": 0.2, "f": 0.3}
        if profile.goal_type == 'lose': ratios = {"c": 0.4, "p": 0.3, "f": 0.3}
        elif profile.goal_type == 'gain': ratios = {"c": 0.45, "p": 0.35, "f": 0.2}
        
        macros_target = {
            "carbohydrates": {
                "consumed": round(macro_stats["carbohydrates"], 1),
                "target": round(target * ratios["c"] / 4, 1), # 1g碳水=4kcal
            },
            "protein": {
                "consumed": round(macro_stats["protein"], 1),
                "target": round(target * ratios["p"] / 4, 1), # 1g蛋白=4kcal
            },
            "fat": {
                "consumed": round(macro_stats["fat"], 1),
                "target": round(target * ratios["f"] / 9, 1), # 1g脂肪=9kcal
            }
        }
        
        for k, v in macros_target.items():
            t = v["target"]
            v["percentage"] = round((v["consumed"] / t * 100), 1) if t > 0 else 0

        return {
            "date": str(target_date),
            "summary": {
                "intake_goal": target, 
                "intake_actual": total_intake,
                "remaining": max(0, target - total_intake),
                "progress_percentage": round(progress, 1),
                "health_level": health_level,
                "health_tip": f"今日表现: {health_level.upper()}",
                "macros": macros_target
            },
            "grouped_items": grouped
        }

    @staticmethod
    def get_weekly_report(user, start_date, end_date):
        """
        [完整复原] 获取周报详细数据
        """
        # 确保日期类型
        if isinstance(start_date, str): 
            start_date = datetime.date.fromisoformat(start_date)
        if isinstance(end_date, str): 
            end_date = datetime.date.fromisoformat(end_date)
            
        logs = JournalSelector.get_range_logs(user, start_date, end_date).order_by('record_date', 'id')
        
        # 1. 构建时间轴 (Timeline)
        timeline = []
        for log in logs:
            timeline.append({
                "date": str(log.record_date),
                "meal_time": log.get_meal_time_display(), 
                "food_name": log.food_name,
                "calories": log.calories,
                "meal_type": log.meal_time
            })
            
        # 2. 统计数据 (Stats)
        total_consumed = logs.aggregate(t=Sum('calories'))['t'] or 0
        num_days = (end_date - start_date).days + 1
        avg_daily = int(total_consumed / num_days) if num_days > 0 else 0
        
        # 3. 极值分析 (Highlights)
        # 注意：需要重新查询或在内存处理，这里复用 QuerySet
        max_item = logs.order_by('-calories').first()
        min_item = logs.order_by('calories').first()
        
        max_info = None
        if max_item:
            max_info = {
                "date": str(max_item.record_date), 
                "food_name": max_item.food_name, 
                "calories": max_item.calories
            }
            
        min_info = None
        if min_item:
            min_info = {
                "date": str(min_item.record_date), 
                "food_name": min_item.food_name, 
                "calories": min_item.calories
            }
        
        # 4. 每日趋势 (Trend)
        trend = []
        profile = getattr(user, 'profile', None)
        target = profile.daily_kcal_limit if profile else 2000

        # 高效聚合每日总和
        daily_sums_qs = logs.values('record_date').annotate(total=Sum('calories'))
        daily_map = {d['record_date']: d['total'] for d in daily_sums_qs}
            
        for i in range(num_days):
            d = start_date + datetime.timedelta(days=i)
            c = daily_map.get(d, 0)
            trend.append({
                "date": str(d),
                "consumed": c,
                "target": target
            })
            
        return {
            "timeline": timeline,
            "total_consumed": total_consumed,
            "avg_daily_consumed": avg_daily,
            "max_calorie_item": max_info,
            "min_calorie_item": min_info,
            "trend": trend
        }

    @staticmethod
    def get_monthly_calendar(user, year, month):
        """
        [完整复原] 月度日历热量状态
        """
        _, num_days = calendar.monthrange(year, month)
        start = datetime.date(year, month, 1)
        end = datetime.date(year, month, num_days)
        
        # 使用 Selectors 获取范围数据
        logs = DailyIntake.objects.filter(user=user, record_date__range=(start, end)).values('record_date').annotate(total=Sum('calories'))
        log_map = {l['record_date']: l['total'] for l in logs}
        
        profile = getattr(user, 'profile', None)
        target = profile.daily_kcal_limit if profile else 2000
        
        res = []
        for day in range(1, num_days+1):
            curr = datetime.date(year, month, day)
            t = log_map.get(curr, 0)
            status = "none"
            if t > 0:
                if t > target * 1.1: status = "exceeded"
                elif t < target * 0.9: status = "insufficient"
                else: status = "perfect"
            res.append({"date": str(curr), "day": day, "calories": t, "status": status})
        return res

    @staticmethod
    def get_seven_day_history(user):
        """
        [完整复原] 获取7日历史 (ChartService 可能会用到)
        """
        today = datetime.date.today()
        history = []
        for i in range(6, -1, -1):
            date = today - datetime.timedelta(days=i)
            # 使用 aggregate 查询单日总和
            s = DailyIntake.objects.filter(user=user, record_date=date).aggregate(t=Sum('calories'))['t'] or 0
            history.append({"date": date.strftime("%m-%d"), "calories": s})
        return {"chart_data": history}