import datetime
from django.utils import timezone
from apps.diet.models import WorkoutRecord
from django.db.models import Sum


class WorkoutService:
    @staticmethod
    def log_workout(user, workout_type, duration, calories, date_str=None):
        date = timezone.now().date()
        if date_str:
            try: date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            except: pass
                
        return WorkoutRecord.objects.create(
            user=user, type=workout_type, duration=duration, 
            calories_burned=calories, date=date
        )

    @staticmethod
    def get_history(user, days=30):
        start = timezone.now().date() - datetime.timedelta(days=days)
        return WorkoutRecord.objects.filter(
            user=user, date__gte=start
        ).order_by('-date', '-created_at')
    

    # [新增] 获取今日运动统计
    @staticmethod
    def get_today_stats(user):
        today = timezone.now().date()
        records = WorkoutRecord.objects.filter(user=user, date=today)
        
        # 聚合计算总热量和总时长
        stats = records.aggregate(
            total_calories=Sum('calories_burned'),
            total_duration=Sum('duration')
        )
        
        return {
            "total_calories": stats['total_calories'] or 0,
            "total_duration": stats['total_duration'] or 0,
            "count": records.count()
        }

    # [新增] 获取单次运动详情
    @staticmethod
    def get_detail(user, workout_id):
        try:
            return WorkoutRecord.objects.get(id=workout_id, user=user)
        except WorkoutRecord.DoesNotExist:
            return None    
