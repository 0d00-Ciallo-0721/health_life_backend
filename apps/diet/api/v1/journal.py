from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.diet.domains.journal.intake_service import IntakeService
from apps.diet.domains.journal.workout_service import WorkoutService
from apps.diet.domains.journal.selectors import JournalSelector
from apps.diet.domains.analytics.report_service import ReportService
from apps.diet.serializers.journal import WorkoutRecordSerializer
from apps.diet.models import WeightRecord

class LogIntakeView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            source_type = int(request.data.get("source_type", 1))
            portion = float(request.data.get("portion", 1.0))
            source_id = request.data.get("source_id")
            if not source_id and source_type != 3: # type 3 可以没有 source_id
                return Response({"code": 400, "msg": "缺少 source_id"}, status=400)
        except ValueError:
            return Response({"code": 400, "msg": "参数类型错误"}, status=400)

        res = IntakeService.log_intake(
            user=request.user,
            source_type=source_type,
            source_id=source_id,
            portion=portion,
            deduct_fridge=request.data.get("deduct_fridge", True),
            meal_type=request.data.get("meal_type"),
            meal_time_str=request.data.get("meal_time"),
            macros=request.data.get("macros"),
            custom_calories=int(request.data.get("calories", 0))
        )
        
        if res:
            # 重新获取 summary 更新前端 UI
            summary = ReportService.get_daily_summary(request.user, res.record_date)
            s_data = summary['summary']
            return Response({
                "code": 200, 
                "msg": f"记录成功 (+{res.calories} kcal)",
                "data": {
                    "log_id": res.id,
                    "today_total_calories": s_data['intake_actual'],
                    "remaining_calories": s_data['remaining'],
                    "daily_summary": summary
                }
            })
        return Response({"code": 500, "msg": "记录失败"}, status=500)

class DietLogDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, pk):
        success = IntakeService.delete_intake(request.user, pk)
        if success:
            return Response({"code": 200, "msg": "删除成功"})
        return Response({"code": 404, "msg": "记录不存在"}, status=404)

class WorkoutLogView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        w_type = request.data.get('type')
        duration = request.data.get('duration')
        calories = request.data.get('calories_burned')
        if not all([w_type, duration, calories]):
            return Response({"code": 400, "msg": "缺少参数"}, status=400)
            
        record = WorkoutService.log_workout(
            request.user, w_type, int(duration), int(calories), request.data.get('date')
        )
        return Response({"code": 200, "msg": "打卡成功", "data": WorkoutRecordSerializer(record).data})

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        records = WorkoutService.get_history(request.user, days)
        serializer = WorkoutRecordSerializer(records, many=True)
        total = sum(r.calories_burned for r in records)
        return Response({
            "code": 200, 
            "data": {"summary": {"total_calories_burned": total, "total_count": len(records)}, "history": serializer.data}
        })

class WeightView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        weight = request.data.get('weight')
        if not weight: return Response({"code": 400, "msg": "体重不能为空"}, status=400)
        # 简单逻辑暂时写在这里，或移入 Service
        from apps.users.models import Profile
        from django.utils import timezone
        import datetime
        
        date_str = request.data.get('date')
        date = datetime.date.fromisoformat(date_str) if date_str else timezone.now().date()
        
        profile = getattr(request.user, 'profile', None)
        bmi = 0
        if profile and profile.height:
            h = profile.height / 100
            bmi = round(float(weight) / (h * h), 1)
            profile.weight = float(weight)
            profile.save()
            
        WeightRecord.objects.update_or_create(
            user=request.user, date=date, defaults={'weight': weight, 'bmi': bmi}
        )
        return Response({"code": 200, "msg": "记录成功", "data": {"bmi": bmi}})

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        # 简单查询，直接操作 Model
        import datetime
        from django.utils import timezone
        start = timezone.now().date() - datetime.timedelta(days=days)
        data = list(WeightRecord.objects.filter(user=request.user, date__gte=start).order_by('date').values('date', 'weight', 'bmi'))
        return Response({"code": 200, "data": {"records": data}})