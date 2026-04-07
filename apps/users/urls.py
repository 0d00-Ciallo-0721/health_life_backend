from django.urls import path
# [修改] 新增导入 LogoutView
from .views import WeChatLoginView, UserMetaView, UserProfileView, UserFollowView, UserPostsView, LogoutView

urlpatterns = [
    path('login/', WeChatLoginView.as_view(), name='wechat_login'),
    path('logout/', LogoutView.as_view(), name='user_logout'),  # [新增] 退出登录路由
    path('meta/', UserMetaView.as_view(), name='user_meta'),
    
    # 社交与主页模块路由
    path('<int:user_id>/profile/', UserProfileView.as_view(), name='user_profile'),
    path('<int:user_id>/follow/', UserFollowView.as_view(), name='user_follow'),
    path('<int:user_id>/posts/', UserPostsView.as_view(), name='user_posts'),
]