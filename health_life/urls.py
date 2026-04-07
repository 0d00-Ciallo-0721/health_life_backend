from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # 业务路由
    # [修改] 将 api/v1/user/ 加上s，改为 api/v1/users/ ！！！
    path('api/v1/users/', include('apps.users.urls')),
    
    # ✅ [核心] 将 diet 的 URL 挂载两次，以兼容前端混乱的路径
    path('api/v1/diet/', include('apps.diet.urls')),
    path('api/v1/', include('apps.diet.urls')),
    
    # 后台接口入口
    path('api/admin/', include('apps.admin_management.urls')), 
]