from django.urls import path
from .auth import AdminLoginView
from rest_framework.routers import DefaultRouter
from .business import UserManageViewSet, RecipeAuditViewSet # 导入
from .dashboard import DashboardSummaryView 
from .business import (
    UserManageViewSet, 
    RecipeAuditViewSet, 
    RestaurantViewSet,
    ChallengeTaskViewSet, 
    RemedyViewSet,
    AchievementViewSet,   # 🚀 新增
    CommunityFeedViewSet, # 🚀 新增
    CommentViewSet        # 🚀 新增
)
from .system import (
    CurrentUserMenuView, 
    MenuViewSet, 
    RoleViewSet, 
    AuditLogViewSet,
    NotificationViewSet ,
    SystemConfigViewSet 

)


router = DefaultRouter()
# 注册菜单接口
router.register(r'system/menus', MenuViewSet, basename='sys_menu')
router.register(r'system/roles', RoleViewSet, basename='sys_role')
router.register(r'system/logs', AuditLogViewSet, basename='sys_log') 
router.register(r'system/notifications', NotificationViewSet, basename='sys_notify') 
router.register(r'system/configs', SystemConfigViewSet, basename='sys_config')
router.register(r'business/users', UserManageViewSet, basename='biz_user')
router.register(r'business/recipes', RecipeAuditViewSet, basename='biz_recipe')
router.register(r'business/restaurants', RestaurantViewSet, basename='biz_restaurant')
router.register(r'business/tasks', ChallengeTaskViewSet, basename='biz_task')
router.register(r'business/remedies', RemedyViewSet, basename='biz_remedy')
router.register(r'business/achievements', AchievementViewSet, basename='biz_achievement')
router.register(r'business/feeds', CommunityFeedViewSet, basename='biz_feed')
router.register(r'business/comments', CommentViewSet, basename='biz_comment')


urlpatterns = [
    path('auth/login/', AdminLoginView.as_view(), name='admin_login'),
    path('system/menus/tree/', CurrentUserMenuView.as_view(), name='my_menus'),
    
    # 🚀 [新增] 仪表盘统计接口
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard_summary'),
    
] + router.urls