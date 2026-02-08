from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # 业务路由
    path('api/v1/user/', include('apps.users.urls')),
    
    # ✅ [核心] 将 diet 的 URL 挂载两次，以兼容前端混乱的路径
    # 1. 标准路径: /api/v1/diet/search/
    path('api/v1/diet/', include('apps.diet.urls')),
    
    # 2. [兼容补丁] 根路径兼容: /api/v1/recipe/..., /api/v1/restaurant/...
    # 这样前端请求 /api/v1/recipe/123/ 也能被 apps.diet.urls 捕获
    path('api/v1/', include('apps.diet.urls')),
    # 后台接口入口
    path('api/admin/', include('apps.admin_management.urls')), 
]