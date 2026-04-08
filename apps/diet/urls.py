from django.urls import path

# ==========================================
# 视图导入 (按领域模块划分)
# ==========================================
from apps.diet.api.v1.preferences import (
    ProfileUpdateView, PreferenceOperationView, FavoriteListView
)
from apps.diet.api.v1.pantry import (
    FridgeItemListView, FridgeItemDetailView, FridgeSyncView
)
from apps.diet.api.v1.discovery import (
    RecommendSearchView, RecipeDetailView, RestaurantDetailView, 
    WheelOptionsView, ShoppingListGenerateView, ShoppingStoreLBSView
)
from apps.diet.api.v1.journal import (
    LogIntakeView, DietLogDetailView, WeightView, WorkoutLogView,
    WorkoutStatsTodayView, WorkoutDetailView, WaterIntakeView,
    WaterEventView, WaterResetView
)
from apps.diet.api.v1.community import (
    CommunityFeedView, CommunityShareListView, 
    CommunityLikeView, CommunityCommentView,
    CommunityFeedDetailView, CommunitySaveView, CommunityReportView,
    UserProfileView, UserPostsView,
    CommunityUploadView  # [新增补充]
)
from apps.diet.api.v1.gamification import (
    ChallengeTaskView, ChallengeJoinView, ChallengeProgressView, ChallengeProgressActionView,
    LeaderboardView, AchievementView, 
    RemedySolutionView, RemedyPlanActionView, RemedyUsageHistoryView, RemedyTriageView,
    CarbonFootprintView, CarbonWeeklyView, CarbonSuggestionView, CarbonHistoryView, CarbonAchievementView,
    RemedyFavoriteView, ChallengeTaskProgressCompatView, 
    ChallengeTaskDetailView,
    UserFeaturedBadgeView # [新增补充]
)
from apps.diet.api.v1.tools import (
    AIFoodRecognitionView, AINutritionistView,
    AIRealTimeAdviceView, AIChatView, AIChatStreamView, AIAttachmentUploadView, # [新增] AIChatStreamView
    AIIngredientRecognitionView, AIHealthWarningsView
)

from apps.diet.api.v1.analytics import (
    DailySummaryView, DailyChartDataView, WeeklyChartDataView, WeightChartDataView,
    DietWeeklyReportView, DietCalendarView, DietHistoryTrendView
)


urlpatterns = [
    # ==========================================
    # 1. 档案与偏好 (Profile & Preferences)
    # ==========================================
    path('profile/', ProfileUpdateView.as_view(), name='profile_update'),
    path('preference/', PreferenceOperationView.as_view(), name='preference_op'),
    path('favorites/', FavoriteListView.as_view(), name='user_favorites'),

    # ==========================================
    # 2. 冰箱与库存 (Pantry Domain)
    # ==========================================
    path('fridge/', FridgeItemListView.as_view(), name='fridge_list'),
    path('fridge/sync/', FridgeSyncView.as_view(), name='fridge_sync'),
    path('fridge/<int:pk>/', FridgeItemDetailView.as_view(), name='fridge_detail'),

    # ==========================================
    # 3. 搜餐与推荐 (Discovery Domain)
    # ==========================================
    path('search/', RecommendSearchView.as_view(), name='diet_search'),
    path('wheel/', WheelOptionsView.as_view(), name='wheel_options'),
    path('recipe/<str:id>/', RecipeDetailView.as_view(), name='recipe_detail'),
    path('restaurant/<str:id>/', RestaurantDetailView.as_view(), name='restaurant_detail'),
    path('shopping-list/generate/', ShoppingListGenerateView.as_view(), name='shopping_list'),
    path('shopping-list/stores/', ShoppingStoreLBSView.as_view(), name='shopping_stores'),

    # ==========================================
    # 4. 饮食与运动记录 (Journal Domain)
    # ==========================================
    path('log/', LogIntakeView.as_view(), name='log_intake'),
    path('log/<int:pk>/', DietLogDetailView.as_view(), name='log_detail'), 
    path('weight/', WeightView.as_view(), name='weight_manage'),
    path('workout/save/', WorkoutLogView.as_view(), name='workout_log'), 
    path('workout/history/', WorkoutLogView.as_view(), name='workout_history'),
    path('workout/today-stats/', WorkoutStatsTodayView.as_view(), name='workout_today_stats'),
    path('workout/<int:id>/', WorkoutDetailView.as_view(), name='workout_detail'),

    # ==========================================
    # 5. 社区与社交 (Community Domain)
    # ==========================================
    path('community/upload/', CommunityUploadView.as_view(), name='community_upload'), # [新增] 图片上传
    path('community/feed/', CommunityFeedView.as_view(), name='community_feed'),
    path('community/share/', CommunityFeedView.as_view(), name='community_share'),
    path('community/recipes/', CommunityShareListView.as_view(feed_type='recipe'), name='community_recipes'),
    path('community/restaurants/', CommunityShareListView.as_view(feed_type='restaurant'), name='community_restaurants'),
    path('community/feed/<str:feedId>/like/', CommunityLikeView.as_view(), name='community_like'),
    path('community/feed/<str:feedId>/comments/', CommunityCommentView.as_view(), name='community_comment'),
    path('community/feed/<str:feedId>/', CommunityFeedDetailView.as_view(), name='community_feed_detail'),
    path('community/feed/<str:feedId>/save/', CommunitySaveView.as_view(), name='community_save'),
    path('community/feed/<str:feedId>/report/', CommunityReportView.as_view(), name='community_report'),
    # ==========================================
    # 6. 游戏化：挑战、成就与补救 (Gamification Domain)
    # ==========================================
    # 挑战与成就
    path('challenge/tasks/', ChallengeTaskView.as_view(), name='challenge_tasks'),
    # [修复] 补充缺失的挑战任务详情接口
    path('challenge/tasks/<int:pk>/', ChallengeTaskDetailView.as_view(), name='challenge_task_detail'),
    path('challenge/tasks/<int:challengeId>/join/', ChallengeJoinView.as_view(), name='challenge_join'),
    
    # [新增] 兼容前端调用的任务进度路由
    path('challenge/tasks/<int:taskId>/progress/', ChallengeTaskProgressCompatView.as_view(), name='challenge_task_progress_compat'),
    
    path('challenge/progress/', ChallengeProgressView.as_view(), name='challenge_progress'),
    path('challenge/progress/<int:progressId>/<str:action>/', ChallengeProgressActionView.as_view(), name='challenge_action'),
    path('challenge/leaderboard/', LeaderboardView.as_view(), name='challenge_leaderboard'),
    path('achievements/', AchievementView.as_view(), name='achievements'),
    path('achievements/featured/', UserFeaturedBadgeView.as_view(), name='featured_badges'),    
    # 补救方案
    path('remedy/solutions/', RemedySolutionView.as_view(), name='remedy_solutions'),
    path('remedy/triage/', RemedyTriageView.as_view(), name='remedy_triage'),
    path('remedy/add-to-plan/', RemedyPlanActionView.as_view(), name='remedy_add_plan'),
    path('remedy/usage-history/', RemedyUsageHistoryView.as_view(), name='remedy_usage_history'),
    
    # [新增] 补救方案收藏路由
    path('remedy/favorite/', RemedyFavoriteView.as_view(), name='remedy_favorite'),
    
    # 碳足迹
    path('carbon/summary/', CarbonFootprintView.as_view(), name='carbon_summary'),
    path('carbon/footprint/', CarbonFootprintView.as_view(), name='carbon_footprint_compat'),
    path('carbon/footprint/weekly/', CarbonWeeklyView.as_view(), name='carbon_weekly'),
    path('carbon/footprint/history/', CarbonHistoryView.as_view(), name='carbon_history'),
    path('carbon/suggestions/', CarbonSuggestionView.as_view(), name='carbon_suggestions'),
    path('carbon/achievements/', CarbonAchievementView.as_view(), name='carbon_achievements'),

    # ==========================================
    # 7. AI 与工具 (Tools Domain)
    # ==========================================
    path('ai/food-recognition/', AIFoodRecognitionView.as_view(), name='ai_food_rec'),
    path('ingredient/recognize/', AIIngredientRecognitionView.as_view(), name='ai_ingredient_rec'),
    path('ai-nutritionist/analyze/', AINutritionistView.as_view(), name='ai_nutritionist'),
    path('ai-nutritionist/advice/', AIRealTimeAdviceView.as_view(), name='ai_realtime_advice'),
    path('ai-nutritionist/ask/', AIChatView.as_view(), name='ai_chat'),
    path('ai-nutritionist/ask/stream/', AIChatStreamView.as_view(), name='ai_chat_stream'),
    path('ai-nutritionist/upload/', AIAttachmentUploadView.as_view(), name='ai_upload'),
    path('ai-nutritionist/warnings/', AIHealthWarningsView.as_view(), name='ai_health_warnings'),

    # [新增] 数据报表 (Analytics Domain)
    # ==========================================
    path('summary/', DailySummaryView.as_view(), name='daily_summary'),
    path('report/charts/daily/', DailyChartDataView.as_view(), name='chart_daily'),
    path('report/charts/weekly/', WeeklyChartDataView.as_view(), name='chart_weekly'),
    path('report/charts/weight/', WeightChartDataView.as_view(), name='chart_weight'),
    path('report/weekly/', DietWeeklyReportView.as_view(), name='report_weekly'), 
    path('report/calendar/', DietCalendarView.as_view(), name='report_calendar'), 
    path('report/history/', DietHistoryTrendView.as_view(), name='report_history'),

    # [改进] 饮水记录持久化同步路由 (按日期参数化)
    path('water/<str:date_str>/', WaterIntakeView.as_view(), name='water_intake'),
    path('water/<str:date_str>/events/', WaterEventView.as_view(), name='water_events'),
    path('water/<str:date_str>/reset/', WaterResetView.as_view(), name='water_reset'),

]