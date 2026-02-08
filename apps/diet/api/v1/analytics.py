from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import datetime

# 引入刚刚补全的 ReportService
from apps.diet.domains.analytics.report_service import ReportService
from apps.diet.domains.analytics.chart_service import ChartService

class DailySummaryView(APIView):
    """每日汇总接口"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        d_str = request.query_params.get('date')
        date = datetime.date.fromisoformat(d_str) if d_str else datetime.date.today()
        data = ReportService.get_daily_summary(request.user, date)
        return Response({"code": 200, "data": data})

class DietWeeklyReportView(APIView):
    """
    [完整逻辑] 周报数据接口
    GET /diet/report/weekly/?start_date=2024-01-01&end_date=2024-01-07
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        start_str = request.query_params.get('start_date')
        end_str = request.query_params.get('end_date')
        
        # 默认查询本周 (周一到周日)
        if not start_str or not end_str:
            today = datetime.date.today()
            start = today - datetime.timedelta(days=today.weekday())
            end = start + datetime.timedelta(days=6)
        else:
            try:
                start = datetime.date.fromisoformat(start_str)
                end = datetime.date.fromisoformat(end_str)
            except ValueError:
                return Response({"code": 400, "msg": "日期格式错误"}, status=400)
                
        data = ReportService.get_weekly_report(request.user, start, end)
        return Response({"code": 200, "data": data})

class DietCalendarView(APIView):
    """
    [完整逻辑] 月度日历接口
    GET /diet/report/calendar/?year=2024&month=1
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            year = int(request.query_params.get('year', datetime.date.today().year))
            month = int(request.query_params.get('month', datetime.date.today().month))
            
            data = ReportService.get_monthly_calendar(request.user, year, month)
            return Response({"code": 200, "data": data})
        except ValueError:
            return Response({"code": 400, "msg": "年份或月份格式错误"}, status=400)

class DailyChartDataView(APIView):
    """图表数据接口 - 日视图"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        d_str = request.query_params.get('date')
        date = datetime.date.fromisoformat(d_str) if d_str else datetime.date.today()
        # ChartService 内部会调用 ReportService
        data = ChartService.get_daily_chart(request.user, date)
        return Response({"code": 200, "data": data})

class WeightChartDataView(APIView):
    """图表数据接口 - 体重"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            days = int(request.query_params.get('days', 7))
        except ValueError:
            days = 7
        data = ChartService.get_weight_chart(request.user, days)
        return Response({"code": 200, "data": data})
    
class WeeklyChartDataView(APIView):
    """[新增] 周图表接口"""
    permission_classes = [IsAuthenticated]
    def get(self, request):
        start_str = request.query_params.get('start_date')
        end_str = request.query_params.get('end_date')
        
        if not start_str or not end_str:
            today = datetime.date.today()
            start = today - datetime.timedelta(days=today.weekday())
            end = start + datetime.timedelta(days=6)
        else:
            try:
                start = datetime.date.fromisoformat(start_str)
                end = datetime.date.fromisoformat(end_str)
            except ValueError:
                return Response({"code": 400, "msg": "日期格式错误"}, status=400)
                
        data = ChartService.get_weekly_chart(request.user, start, end)
        return Response({"code": 200, "data": data})
