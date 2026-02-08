import datetime
from django.utils import timezone
from apps.diet.models import WorkoutRecord

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