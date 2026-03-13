from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import datetime
from django.db.models import Sum
from apps.diet.models.mysql.journal import WeightRecord, DailyIntake


# 引入刚刚补全的 ReportService
from apps.diet.domains.analytics.report_service import ReportService
from apps.diet.domains.analytics.chart_service import ChartService

class DailySummaryView(APIView):
    """每日汇总接口"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        d_str = request.query_params.get('date')
        if d_str in ['undefined', 'null', '']:
            d_str = None
        date = datetime.date.fromisoformat(d_str) if d_str else datetime.date.today()
        
        data = ReportService.get_daily_summary(request.user, date)
        
        # 计算百分比
        macros = data.get('macros', {})
        c_g = float(data.get('carb', macros.get('carbohydrates', macros.get('carbg', 0))) or 0)
        p_g = float(data.get('protein', macros.get('protein', macros.get('proteing', 0))) or 0)
        f_g = float(data.get('fat', macros.get('fat', macros.get('fatg', 0))) or 0)
        total_cals = (c_g * 4) + (p_g * 4) + (f_g * 9)

        if total_cals > 0:
            carb_pct = round((c_g * 4 / total_cals) * 100)
            protein_pct = round((p_g * 4 / total_cals) * 100)
            fat_pct = round((f_g * 9 / total_cals) * 100)
        else:
            carb_pct = protein_pct = fat_pct = 0
            
        # 将百分比注入到 data 内部
        data['carbPercent'] = carb_pct
        data['proteinPercent'] = protein_pct
        data['fatPercent'] = fat_pct

        # 核心修改：同时将这三个字段铺平放在最外层，防止前端解包错误
        return Response({
            "code": 200, 
            "data": data,
            "carbPercent": carb_pct,
            "proteinPercent": protein_pct,
            "fatPercent": fat_pct
        })
        

            
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
        
        data = ChartService.get_daily_chart(request.user, date)
        
        # 计算百分比
        macros = data.get('macros', {})
        c_g = float(data.get('carb', macros.get('carbohydrates', macros.get('carbg', 0))) or 0)
        p_g = float(data.get('protein', macros.get('protein', macros.get('proteing', 0))) or 0)
        f_g = float(data.get('fat', macros.get('fat', macros.get('fatg', 0))) or 0)
        total_cals = (c_g * 4) + (p_g * 4) + (f_g * 9)

        if total_cals > 0:
            carb_pct = round((c_g * 4 / total_cals) * 100)
            protein_pct = round((p_g * 4 / total_cals) * 100)
            fat_pct = round((f_g * 9 / total_cals) * 100)
        else:
            carb_pct = protein_pct = fat_pct = 0
            
        # 将百分比注入到 data 内部
        data['carbPercent'] = carb_pct
        data['proteinPercent'] = protein_pct
        data['fatPercent'] = fat_pct

        # 核心修改：同时将这三个字段铺平放在最外层，防止前端解包错误
        return Response({
            "code": 200, 
            "data": data,
            "carbPercent": carb_pct,
            "proteinPercent": protein_pct,
            "fatPercent": fat_pct
        })

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


class DietHistoryTrendView(APIView):
    """历史趋势大盘: GET /diet/report/history/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # 1. 获取体重趋势 (按日期正序排，前端画折线图需要)
        weights_qs = WeightRecord.objects.filter(user=user).order_by('date')
        weights = [{"weight": float(w.weight), "date": w.date.strftime('%Y-%m-%d')} for w in weights_qs]
        
        # 2. 获取用餐/打卡总次数 (饮食记录的总条数)
        total_meals = DailyIntake.objects.filter(user=user).count()

        # 3. 计算完美天数与日趋势
        profile = getattr(user, 'profile', None)
        target_limit = profile.daily_kcal_limit if profile and profile.daily_kcal_limit else 2000
        
        # 按日聚合摄入热量
        daily_calories = DailyIntake.objects.filter(user=user).values('record_date').annotate(
            total_cal=Sum('calories')
        ).order_by('record_date')
        
        perfect_days = 0
        trend = []
        
        for daily in daily_calories:
            consumed = daily['total_cal'] or 0
            
            # 判断是否达标 (大于0且未超出目标热量视为完美天数)
            if 0 < consumed <= target_limit:
                perfect_days += 1
                
            trend.append({
                "date": daily['record_date'].strftime('%Y-%m-%d'),
                "consumed": consumed,
                "target": target_limit
            })

        data = {
            "weights": weights,
            "total_meals": total_meals,
            "perfect_days": perfect_days,
            "trend": trend
        }
        
        return Response({"code": 200, "msg": "success", "data": data})