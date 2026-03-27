from django.urls import path
from rest_framework.routers import DefaultRouter
from .auth import AdminLoginView
from .dashboard import DashboardSummaryView 
from .business import (
    UserManageViewSet, 
    RecipeAuditViewSet, 
    RestaurantViewSet,
    CommunityFeedViewSet, 
    CommentViewSet,
    JournalMacroStatsView # 🚀 聚合统计数据
)
from .system import (
    CurrentUserMenuView, 
    MenuViewSet, 
    RoleViewSet, 
    AuditLogViewSet,
    NotificationViewSet,
    SystemConfigViewSet 
)
from .gamification_admin import (
    AchievementAdminViewSet, 
    ChallengeTaskAdminViewSet, 
    RemedyAdminViewSet
)
from .community_admin import (
    CommunityFeedAdminView,
    CommunityFeedActionAdminView,
    UserFollowAnomalyAdminView
)

router = DefaultRouter()
# 注册系统与管理接口
router.register(r'system/menus', MenuViewSet, basename='sys_menu')
router.register(r'system/roles', RoleViewSet, basename='sys_role')
router.register(r'system/logs', AuditLogViewSet, basename='sys_log') 
router.register(r'system/notifications', NotificationViewSet, basename='sys_notify') 
router.register(r'system/configs', SystemConfigViewSet, basename='sys_config')
# 注册业务相关接口
router.register(r'business/users', UserManageViewSet, basename='biz_user')
router.register(r'business/recipes', RecipeAuditViewSet, basename='biz_recipe')
router.register(r'business/restaurants', RestaurantViewSet, basename='biz_restaurant')
router.register(r'business/feeds', CommunityFeedViewSet, basename='biz_feed')
router.register(r'business/comments', CommentViewSet, basename='biz_comment')
# 注册游戏化管理
router.register(r'game/achievements', AchievementAdminViewSet, basename='admin-achievement')
router.register(r'game/challenges', ChallengeTaskAdminViewSet, basename='admin-challenge')
router.register(r'game/remedies', RemedyAdminViewSet, basename='admin-remedy')

urlpatterns = [
    path('auth/login/', AdminLoginView.as_view(), name='admin_login'),
    path('system/menus/tree/', CurrentUserMenuView.as_view(), name='my_menus'),
    
    # 仪表盘与统计
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard_summary'),
    path('business/stats/journal/', JournalMacroStatsView.as_view(), name='biz_journal_stats'),
    
    # 社交异常处理
    path('social/feeds/', CommunityFeedAdminView.as_view(), name='admin_social_feeds'),
    path('social/feeds/<str:feed_id>/', CommunityFeedActionAdminView.as_view(), name='admin_social_feed_action'),
    path('social/follows/anomaly/', UserFollowAnomalyAdminView.as_view(), name='admin_social_follow_anomaly'),
] + router.urls