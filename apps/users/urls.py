from django.urls import path
# [修改] 新增导入 UserProfileView, UserFollowView
from .views import WeChatLoginView, UserMetaView, UserProfileView, UserFollowView

# [修改] 完整替换 urlpatterns 列表
urlpatterns = [
    path('login/', WeChatLoginView.as_view(), name='wechat_login'),
    path('meta/', UserMetaView.as_view(), name='user_meta'),
    
    # [新增] 社交与主页模块路由
    path('<int:user_id>/profile/', UserProfileView.as_view(), name='user_profile'),
    path('<int:user_id>/follow/', UserFollowView.as_view(), name='user_follow'),
]