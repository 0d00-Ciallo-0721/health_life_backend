from django.urls import path
# [修改] 新增导入 UserPostsView (需在 views.py 中实现该视图)
from .views import WeChatLoginView, UserMetaView, UserProfileView, UserFollowView, UserPostsView

urlpatterns = [
    path('login/', WeChatLoginView.as_view(), name='wechat_login'),
    path('meta/', UserMetaView.as_view(), name='user_meta'),
    
    # 社交与主页模块路由
    path('<int:user_id>/profile/', UserProfileView.as_view(), name='user_profile'),
    path('<int:user_id>/follow/', UserFollowView.as_view(), name='user_follow'),
    # [修复] 补充缺失的 TA 的动态列表接口
    path('<int:user_id>/posts/', UserPostsView.as_view(), name='user_posts'),
]