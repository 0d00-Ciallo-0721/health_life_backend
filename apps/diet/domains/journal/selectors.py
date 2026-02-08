from django.db.models import Sum
from apps.diet.models import DailyIntake
import datetime

class JournalSelector:
    @staticmethod
    def get_recipe_stats(user, recipe_id):
        logs = DailyIntake.objects.filter(user=user, source_type=1, source_id=str(recipe_id)).order_by('-record_date')
        last = logs.first()
        recently = False
        if last:
            if (datetime.date.today() - last.record_date).days <= 7:
                recently = True
        return {"cook_count": logs.count(), "recently_cooked": recently}

    @staticmethod
    def get_daily_logs(user, date):
        """获取指定日期的记录"""
        return DailyIntake.objects.filter(user=user, record_date=date)

    @staticmethod
    def get_range_logs(user, start, end):
        """获取日期范围内的记录"""
        return DailyIntake.objects.filter(user=user, record_date__range=(start, end))