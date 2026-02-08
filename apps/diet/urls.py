from django.urls import path
from apps.diet.api.v1.pantry import FridgeItemListView, FridgeItemDetailView, FridgeSyncView
from apps.diet.api.v1.journal import LogIntakeView, DietLogDetailView, WeightView, WorkoutLogView
from apps.diet.api.v1.discovery import (
    RecommendSearchView, RecipeDetailView, RestaurantDetailView, 
    WheelOptionsView, ShoppingListGenerateView
)
from apps.diet.api.v1.analytics import (
    DailySummaryView, DailyChartDataView, WeeklyChartDataView, WeightChartDataView,
    DietWeeklyReportView, DietCalendarView
)
from apps.diet.api.v1.preferences import (
    ProfileUpdateView, PreferenceOperationView, FavoriteListView
)
from apps.diet.api.v1.tools import AIFoodRecognitionView, AINutritionistView
from apps.diet.api.v1.gamification import ChallengeTaskView, RemedySolutionView, CarbonFootprintView
urlpatterns = [
    # --- 档案 ---
    path('profile/', ProfileUpdateView.as_view(), name='profile_update'),
    path('weight/', WeightView.as_view(), name='weight_manage'),

    # --- 冰箱 ---
    path('fridge/', FridgeItemListView.as_view(), name='fridge_list'),
    path('fridge/sync/', FridgeSyncView.as_view(), name='fridge_sync'),
    path('fridge/<int:pk>/', FridgeItemDetailView.as_view(), name='fridge_detail'),

    # --- 搜餐 & 推荐 ---
    path('search/', RecommendSearchView.as_view(), name='diet_search'),
    path('recipe/<str:id>/', RecipeDetailView.as_view(), name='recipe_detail'),
    path('restaurant/<str:id>/', RestaurantDetailView.as_view(), name='restaurant_detail'),
    path('wheel/', WheelOptionsView.as_view(), name='wheel_options'),
    path('shopping-list/generate/', ShoppingListGenerateView.as_view(), name='shopping_list'),

    # --- 偏好 ---
    path('preference/', PreferenceOperationView.as_view(), name='preference_op'),
    path('favorites/', FavoriteListView.as_view(), name='user_favorites'),

    # --- 记录 ---
    path('log/', LogIntakeView.as_view(), name='log_intake'),
    path('log/<int:pk>/', DietLogDetailView.as_view(), name='log_detail'), 
    path('workout/save/', WorkoutLogView.as_view(), name='workout_log'), 
    path('workout/history/', WorkoutLogView.as_view(), name='workout_history'),

    # --- 报表 ---
    path('summary/', DailySummaryView.as_view(), name='daily_summary'),
    # 图表数据专用接口
    path('report/charts/daily/', DailyChartDataView.as_view(), name='chart_daily'),
    path('report/charts/weekly/', WeeklyChartDataView.as_view(), name='chart_weekly'), # [新增]
    path('report/charts/weight/', WeightChartDataView.as_view(), name='chart_weight'),
    
    # 历史报表接口
    path('report/weekly/', DietWeeklyReportView.as_view(), name='report_weekly'), 
    path('report/calendar/', DietCalendarView.as_view(), name='report_calendar'), 
    
    # --- AI ---
    path('ai/food-recognition/', AIFoodRecognitionView.as_view(), name='ai_food_rec'),
    path('ai-nutritionist/analyze/', AINutritionistView.as_view(), name='ai_nutritionist'),
    
    # [修复/新增] 之前可能遗漏的路由
    path('challenge/tasks/', ChallengeTaskView.as_view(), name='challenge_tasks'),
    path('remedy/solutions/', RemedySolutionView.as_view(), name='remedy_solutions'),
    path('carbon/footprint/', CarbonFootprintView.as_view(), name='carbon_footprint'),
]