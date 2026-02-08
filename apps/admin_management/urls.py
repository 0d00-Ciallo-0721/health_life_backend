from django.urls import path, include

urlpatterns = [
    path('v1/', include('apps.admin_management.api.v1.urls')),
]