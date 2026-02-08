from django.urls import path
from .views import WeChatLoginView, UserMetaView

urlpatterns = [
    path('login/', WeChatLoginView.as_view(), name='wechat_login'),
    # [新增] 用户元数据接口
    path('meta/', UserMetaView.as_view(), name='user_meta'),
]