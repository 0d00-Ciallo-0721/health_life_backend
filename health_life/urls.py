from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
# [新增导入]
from django.conf import settings
from django.conf.urls.static import static
from apps.diet.api.v1.discovery import RecipeDetailView, RestaurantDetailView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # 业务路由
    path('api/v1/users/', include('apps.users.urls')),
    path('api/v1/user/', include('apps.users.urls')),
    path('api/v1/diet/', include('apps.diet.urls')),
    path('api/v1/recipe/<str:id>/', RecipeDetailView.as_view(), name='legacy_recipe_detail'),
    path('api/v1/restaurant/<str:id>/', RestaurantDetailView.as_view(), name='legacy_restaurant_detail'),
    path('api/v1/', include('apps.diet.urls')),
    
    # 后台接口入口
    path('api/admin/', include('apps.admin_management.urls')), 
]

# [新增] 开启本地 Media 媒体文件服务，修复 404 图片无法访问的问题
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
