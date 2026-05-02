from django.urls import path
# 1. 确保引入了 ProfileUpdateView (用于头像上传和档案修改)
from .views import (
    WeChatLoginView, UserMetaView, UserProfileView, 
    UserFollowView, UserPostsView, LogoutView,
    ProfileUpdateView, CurrentUserAccountView  # [新增导入]
)

urlpatterns = [
    path('login/', WeChatLoginView.as_view(), name='wechat_login'),
    path('logout/', LogoutView.as_view(), name='user_logout'),
    path('me/', CurrentUserAccountView.as_view(), name='current_user_account'),
    path('meta/', UserMetaView.as_view(), name='user_meta'),
    
    # [新增] 修改个人档案（含头像上传）: POST /api/v1/user/profile/
    # 对应 Phase 1 的 ProfileUpdateView
    path('profile/', ProfileUpdateView.as_view(), name='profile_self_update'),

    # 社交与主页模块路由
    # [修正] 参数名从 user_id 改为 userId，以匹配视图函数中的参数名
    path('<int:userId>/profile/', UserProfileView.as_view(), name='user_profile'),
    path('<int:userId>/follow/', UserFollowView.as_view(), name='user_follow'),
    path('<int:userId>/posts/', UserPostsView.as_view(), name='user_posts'),
]
