from rest_framework import serializers
from apps.diet.models import DailyIntake, WeightRecord, WorkoutRecord

class DailyIntakeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyIntake
        fields = '__all__' # 自动包含 meal_time, macros

class WeightSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeightRecord
        fields = ['id', 'date', 'weight', 'bmi']
        read_only_fields = ['id', 'bmi']

class WorkoutRecordSerializer(serializers.ModelSerializer):
    """[v3.1 新增] 运动记录序列化"""
    class Meta:
        model = WorkoutRecord
        fields = '__all__'
        read_only_fields = ['user', 'created_at']