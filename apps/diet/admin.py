from django.contrib import admin
from django.utils import timezone
from apps.diet.models import FridgeItem, DailyIntake, UserPreference, WorkoutRecord, WeightRecord, ChallengeTask, Remedy

@admin.register(FridgeItem)
class FridgeItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'amount', 'unit', 'category', 'sub_category', 'expiry_date', 'days_since_created')
    search_fields = ('name', 'user__username')
    list_filter = ('category', 'is_scrap')
    ordering = ('-created_at',)
    
    def days_since_created(self, obj):
        delta = timezone.now() - obj.created_at
        return f"{delta.days} 天"
    days_since_created.short_description = "库存时长"

@admin.register(DailyIntake)
class DailyIntakeAdmin(admin.ModelAdmin):
    list_display = ('user', 'record_date', 'meal_time', 'food_name', 'calories', 'source_type')
    list_filter = ('record_date', 'meal_time', 'source_type')
    search_fields = ('food_name', 'user__username')
    ordering = ('-record_date', '-id')

@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'target_type', 'action', 'target_id', 'created_at')
    list_filter = ('action', 'target_type')
    search_fields = ('user__username', 'target_id')

@admin.register(WorkoutRecord)
class WorkoutRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'duration', 'calories_burned', 'date')
    list_filter = ('type', 'date')

@admin.register(WeightRecord)
class WeightRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'weight', 'bmi', 'date')
    ordering = ('-date',)

@admin.register(ChallengeTask)
class ChallengeTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'task_type', 'condition_code', 'is_active')

@admin.register(Remedy)
class RemedyAdmin(admin.ModelAdmin):
    list_display = ('title', 'scenario', 'order')
    list_filter = ('scenario',)    