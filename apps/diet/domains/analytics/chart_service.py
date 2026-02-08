from apps.diet.domains.analytics.report_service import ReportService
from apps.diet.models import WeightRecord
from django.utils import timezone
import datetime

class ChartService:
    @staticmethod
    def get_daily_chart(user, date):
        summary = ReportService.get_daily_summary(user, date)['summary']
        macros = summary['macros']
        
        # 进度图配置
        calorie_chart = {
            "type": "progress_bar",
            "consumed": summary['intake_actual'],
            "target": summary['intake_goal'],
            "percent": summary['progress_percentage'],
            "colors": {"consumed": "#4CAF50", "remaining": "#2196F3"}
        }
        
        # [修复] 营养环图: 正确获取 consumed 值
        # macros 结构: {'carbohydrates': {'consumed': 10, ...}, ...}
        nutrient_chart = {
            "type": "semi_donut",
            "data": [
                {"name": "碳水", "value": macros['carbohydrates']['consumed'], "color": "#2196F3"},
                {"name": "蛋白质", "value": macros['protein']['consumed'], "color": "#FF9800"},
                {"name": "脂肪", "value": macros['fat']['consumed'], "color": "#9C27B0"}
            ]
        }
        return {"calorie_chart": calorie_chart, "nutrient_chart": nutrient_chart}

    @staticmethod
    def get_weekly_chart(user, start, end):
        """[新增] 获取周图表数据"""
        report = ReportService.get_weekly_report(user, start, end)
        trend = report['trend']
        
        # 趋势图 (Line)
        line_data = [{"date": t['date'], "consumed": t['consumed'], "target": t['target']} for t in trend]
        
        return {
            "trend_chart": {
                "type": "line",
                "data": line_data,
                "config": {"colors": {"line": "#4CAF50", "target": "#FF9800"}, "show_grid": True}
            }
        }

    @staticmethod
    def get_weight_chart(user, days=30):
        start = timezone.now().date() - datetime.timedelta(days=days)
        records = WeightRecord.objects.filter(user=user, date__gte=start).order_by('date')
        line_data = [{"date": r.date.isoformat(), "weight": r.weight} for r in records]
        
        return {
            "weight_chart": {
                "type": "line",
                "data": line_data,
                "config": {"y_axis_label": "体重(kg)", "color": "#4CAF50"}
            }
        }