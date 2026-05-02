from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.diet.models import WeightRecord
from django.db.models import Sum
from apps.diet.models.mysql.journal import DailyIntake, WaterIntake, WaterEvent # [新增] 导入饮水模型
from apps.diet.domains.journal.intake_service import IntakeService
from apps.diet.domains.journal.workout_service import WorkoutService
from apps.diet.domains.journal.selectors import JournalSelector
from apps.diet.domains.analytics.report_service import ReportService
from apps.diet.serializers.journal import DailyIntakeSerializer, WorkoutRecordSerializer
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

    def get(self, request, pk):
        try:
            record = DailyIntake.objects.get(id=pk, user=request.user)
        except DailyIntake.DoesNotExist:
            return Response({"code": 404, "msg": "记录不存在"}, status=404)

        serializer = DailyIntakeSerializer(record)
        return Response({"code": 200, "msg": "success", "data": serializer.data})

    def patch(self, request, pk):
        try:
            record = DailyIntake.objects.get(id=pk, user=request.user)
        except DailyIntake.DoesNotExist:
            return Response({"code": 404, "msg": "记录不存在"}, status=404)

        allowed_fields = {
            "food_name",
            "meal_time",
            "source_type",
            "source_id",
            "calories",
            "macros",
            "exact_time",
        }
        update_data = {key: value for key, value in request.data.items() if key in allowed_fields}
        if not update_data:
            return Response({"code": 400, "msg": "没有可更新字段"}, status=400)

        serializer = DailyIntakeSerializer(record, data=update_data, partial=True)
        if not serializer.is_valid():
            return Response({"code": 400, "msg": serializer.errors}, status=400)

        serializer.save()
        return Response({"code": 200, "msg": "更新成功", "data": serializer.data})

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
    

# [新增] 今日运动统计视图
class WorkoutStatsTodayView(APIView):
    """今日运动统计"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 调用 Service 层获取统计数据
        stats = WorkoutService.get_today_stats(request.user)
        return Response({"code": 200, "msg": "success", "data": stats})


# [新增] 单次运动详情视图
class WorkoutDetailView(APIView):
    """单次运动详情"""
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        # 调用 Service 层获取详情
        record = WorkoutService.get_detail(request.user, id)
        if not record:
            return Response({"code": 404, "msg": "运动记录不存在"}, status=404)
        
        # 组装返回数据 (如需更复杂结构可使用 Serializer)
        data = {
            "id": record.id,
            "type": record.type,
            "duration": record.duration,
            "calories_burned": record.calories_burned,
            "date": record.date.strftime('%Y-%m-%d')
        }
        return Response({"code": 200, "msg": "success", "data": data})
    

class WaterIntakeView(APIView):
    """
    饮水记录视图 (按日获取)
    GET /diet/water/{date}/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, date_str):
        # 兼容空参兜底
        if not date_str:
            from django.utils import timezone
            date_str = timezone.now().date().strftime('%Y-%m-%d')
            
        record = WaterIntake.objects.filter(user=request.user, date=date_str).first()
        
        # 获取用户饮水目标 (优先读取最新字段)
        goal_ml = 2000
        if hasattr(request.user, 'profile') and request.user.profile:
            profile = request.user.profile
            if getattr(profile, 'water_goal_ml', None):
                goal_ml = profile.water_goal_ml
            elif getattr(profile, 'water_goal_cups', None):
                goal_ml = profile.water_goal_cups * 250
            
        events_data = []
        if record:
            # 获取按照时间线排序的饮水事件流
            events = record.events.all().order_by('created_at')
            events_data = [{
                'id': str(e.id),
                'ml': e.ml,
                'ts': int(e.created_at.timestamp() * 1000), # 前端需要的毫秒时间戳
                'source': e.source,
                'note': e.note
            } for e in events]

        return Response({
            "code": 200, 
            "msg": "success", 
            "data": {
                "date": date_str,
                "total_ml": record.total_ml if record else 0,
                "manual_ml": record.manual_ml if record else 0,
                "food_ml": record.food_ml if record else 0,
                "goal_ml": goal_ml,
                "events": events_data
            }
        })


class WaterEventView(APIView):
    """
    饮水事件追加视图
    POST /diet/water/{date}/events/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, date_str):
        ml = request.data.get('ml')
        
        if not date_str or ml is None:
            return Response({"code": 400, "msg": "缺少 date_str 路径参数或 ml 主体参数"}, status=400)
            
        try:
            ml_val = int(ml)
        except ValueError:
            return Response({"code": 400, "msg": "ml 必须是整数"}, status=400)
            
        # 幂等获取当天的总记录对象
        record, _ = WaterIntake.objects.get_or_create(
            user=request.user,
            date=date_str
        )
        
        # 创建新的事件流节点
        source = request.data.get('source', 'manual')
        note = request.data.get('note', '')
        event = WaterEvent.objects.create(
            intake=record,
            ml=ml_val,
            source=source,
            note=note
        )
        
        # 同步更新每日总计
        record.manual_ml += ml_val
        record.total_ml += ml_val
        record.save()
        
        return Response({
            "code": 200, 
            "msg": "success", 
            "data": {
                "date": str(record.date),
                "total_ml": record.total_ml,
                "manual_ml": record.manual_ml,
                "event": {
                    "id": str(event.id),
                    "ml": event.ml,
                    "source": event.source,
                    "ts": int(event.created_at.timestamp() * 1000)
                }
            }
        })


class WaterResetView(APIView):
    """
    饮水清空视图 (重置当日所有手动饮水)
    POST /diet/water/{date}/reset/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, date_str):
        if not date_str:
            return Response({"code": 400, "msg": "缺少 date_str 路径参数"}, status=400)
            
        record = WaterIntake.objects.filter(
            user=request.user,
            date=date_str
        ).first()
        
        # 降级：如果本身就为空，也要返回前端期望的标准结构
        if not record or record.manual_ml == 0:
             return Response({
                 "code": 200, 
                 "msg": "今日已清空或无记录", 
                 "data": {
                     "date": date_str,
                     "total_ml": record.total_ml if record else 0,
                     "manual_ml": 0
                 }
             })
             
        # 追加一条清空补偿事件
        event = WaterEvent.objects.create(
            intake=record,
            ml=-record.manual_ml,
            source='reset',
            note='手动清空今日记录'
        )
        
        record.total_ml -= record.manual_ml
        record.manual_ml = 0
        record.save()

        return Response({
            "code": 200, 
            "msg": "success", 
            "data": {
                "date": str(record.date),
                "total_ml": record.total_ml,
                "manual_ml": record.manual_ml,
                "event": {
                    "id": str(event.id),
                    "ml": event.ml,
                    "source": event.source,
                    "ts": int(event.created_at.timestamp() * 1000)
                }
            }
        })
