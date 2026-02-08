from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

# 引入模型
from apps.diet.models.mongo.recipe import Recipe as MongoRecipe
from apps.diet.models.mysql.journal import DailyIntake

User = get_user_model()

class DashboardSummaryView(APIView):
    """
    后台首页核心数据统计
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 1. 基础核心指标
        total_users = User.objects.count()
        total_recipes = MongoRecipe.objects.count()
        pending_audit = MongoRecipe.objects.filter(status=0).count()
        new_users_today = User.objects.filter(date_joined__gte=today_start).count()
        active_records_today = DailyIntake.objects.filter(record_date=today_start.date()).count()

        # 🚀 [新增] 计算近7日活跃趋势 (每天的打卡数)
        trend_data = []
        # 循环过去7天 (包括今天)
        for i in range(6, -1, -1):
            target_date = (now - timedelta(days=i)).date()
            count = DailyIntake.objects.filter(record_date=target_date).count()
            trend_data.append({
                "date": target_date.strftime("%m-%d"), # 格式化日期: 02-05
                "value": count
            })

        return Response({
            "code": 200,
            "msg": "success",
            "data": {
                "cards": [
                    {
                        "title": "总用户数",
                        "value": total_users,
                        "today_added": new_users_today,
                        "icon": "User"
                    },
                    {
                        "title": "总菜谱数",
                        "value": total_recipes,
                        "action_needed": pending_audit,
                        "icon": "Dish"
                    },
                    {
                        "title": "今日打卡数",
                        "value": active_records_today,
                        "icon": "DataLine"
                    }
                ],
                "trend": trend_data, # 🚀 将趋势数据传给前端
                "chart_placeholder": False 
            }
        })