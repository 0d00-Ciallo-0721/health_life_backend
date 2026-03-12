from django.urls import path
from apps.diet.api.v1.pantry import FridgeItemListView, FridgeItemDetailView, FridgeSyncView
from apps.diet.api.v1.journal import (
    LogIntakeView, DietLogDetailView, WeightView, WorkoutLogView,
    WorkoutStatsTodayView, WorkoutDetailView  # <- [新增] 这两个 View
)
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
from apps.diet.api.v1.tools import (
    AIFoodRecognitionView, AINutritionistView,
    AIRealTimeAdviceView, AIChatView, AIAttachmentUploadView  # <- [新增] 这三个
)

from apps.diet.api.v1.gamification import (
    ChallengeTaskView, RemedySolutionView, CarbonFootprintView,
    ChallengeJoinView, ChallengeProgressView, ChallengeProgressActionView,
    LeaderboardView, AchievementView, RemedyPlanActionView, CarbonWeeklyView, CarbonSuggestionView
)

from apps.diet.api.v1.community import (
    CommunityFeedView, CommunityShareListView, 
    CommunityLikeView, CommunityCommentView
)

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
    # [新增] 以下两条为运动补齐接口路由
    path('workout/today-stats/', WorkoutStatsTodayView.as_view(), name='workout_today_stats'),
    path('workout/<int:id>/', WorkoutDetailView.as_view(), name='workout_detail'),

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
    # [新增] AI 营养师深度拓展路由
    path('ai-nutritionist/advice/', AIRealTimeAdviceView.as_view(), name='ai_realtime_advice'),
    path('ai-nutritionist/ask/', AIChatView.as_view(), name='ai_chat'),
    path('ai-nutritionist/upload/', AIAttachmentUploadView.as_view(), name='ai_upload'),
    

    # [修改/新增] 游戏化、成就与补救模块路由
    path('challenge/tasks/', ChallengeTaskView.as_view(), name='challenge_tasks'),
    path('challenge/tasks/<int:challengeId>/join/', ChallengeJoinView.as_view(), name='challenge_join'),
    path('challenge/progress/', ChallengeProgressView.as_view(), name='challenge_progress'),
    path('challenge/progress/<int:progressId>/<str:action>/', ChallengeProgressActionView.as_view(), name='challenge_action'),
    path('challenge/leaderboard/', LeaderboardView.as_view(), name='challenge_leaderboard'),
    path('achievements/', AchievementView.as_view(), name='achievements'),
    
    path('remedy/solutions/', RemedySolutionView.as_view(), name='remedy_solutions'),
    path('remedy/add-to-plan/', RemedyPlanActionView.as_view(), name='remedy_add_plan'),
    
    path('carbon/footprint/', CarbonFootprintView.as_view(), name='carbon_footprint'),
    

    # [修复/新增] 之前可能遗漏的路由
    path('challenge/tasks/', ChallengeTaskView.as_view(), name='challenge_tasks'),
    path('remedy/solutions/', RemedySolutionView.as_view(), name='remedy_solutions'),
    path('carbon/footprint/', CarbonFootprintView.as_view(), name='carbon_footprint'),
    
    # [新增] 社区与社交模块路由
    path('community/feed/', CommunityFeedView.as_view(), name='community_feed'),
    path('community/share/', CommunityFeedView.as_view(), name='community_share'), # 复用发帖逻辑
    
    # 指定 type='recipe'
    path('community/recipes/', CommunityShareListView.as_view(feed_type='recipe'), name='community_recipes'),
    # 指定 type='restaurant'
    path('community/restaurants/', CommunityShareListView.as_view(feed_type='restaurant'), name='community_restaurants'),
    
    path('community/feed/<str:feedId>/like/', CommunityLikeView.as_view(), name='community_like'),
    path('community/feed/<str:feedId>/comments/', CommunityCommentView.as_view(), name='community_comment'),

    path('carbon/footprint/weekly/', CarbonWeeklyView.as_view(), name='carbon_weekly'),
    path('carbon/suggestions/', CarbonSuggestionView.as_view(), name='carbon_suggestions'),

]