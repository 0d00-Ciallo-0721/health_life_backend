from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
# ✅ 现在从 .models 导入 User 和 Profile 是完全正确的
from .models import User, Profile

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = '身体档案'
    fk_name = 'user'

class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline, )
    list_display = ('username', 'id', 'date_joined', 'is_staff')
    search_fields = ('username', 'openid')
    ordering = ('-date_joined',)

admin.site.register(User, CustomUserAdmin)