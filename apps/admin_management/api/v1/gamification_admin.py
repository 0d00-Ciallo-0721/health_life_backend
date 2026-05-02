from rest_framework import viewsets, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.utils.text import slugify

from apps.diet.models.mysql.gamification import Achievement, ChallengeTask, Remedy
from apps.admin_management.permissions import IsGameAdmin

# ==========================================
# 1. 统一响应格式基类
# ==========================================
class BaseAdminViewSet(viewsets.ModelViewSet):
    """
    重写 DRF 默认响应格式，对齐前端 {code, msg, data} 规范
    """
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        # 可在此处扩展分页逻辑 (如果需要)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 200, "msg": "success", "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({"code": 200, "msg": "创建成功", "data": serializer.data})

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"code": 200, "msg": "更新成功", "data": serializer.data})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"code": 200, "msg": "删除成功", "data": None})


# ==========================================
# 2. 序列化器定义
# ==========================================
class AchievementAdminSerializer(serializers.ModelSerializer):
    # 动态附加字段：解锁该勋章的总人数
    unlocked_count = serializers.IntegerField(read_only=True, default=0)
    category = serializers.CharField(required=False, allow_blank=True)

    def validate_category(self, value):
        valid_values = {choice for choice, _ in Achievement._meta.get_field('category').choices}
        return value if value in valid_values else 'special'

    class Meta:
        model = Achievement
        fields = '__all__'

class ChallengeTaskAdminSerializer(serializers.ModelSerializer):
    desc = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(write_only=True, required=False, allow_blank=True)
    condition_code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = ChallengeTask
        fields = ['id', 'title', 'task_type', 'condition_code', 'reward_points', 'is_active', 'desc', 'description']

    def validate(self, attrs):
        description = attrs.pop('description', None)
        attrs['desc'] = description or attrs.get('desc') or attrs.get('title', '')
        attrs['condition_code'] = attrs.get('condition_code') or slugify(attrs.get('title', ''), allow_unicode=True).replace('-', '_') or 'task'
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['description'] = data.get('desc', '')
        return data

class RemedyAdminSerializer(serializers.ModelSerializer):
    desc = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Remedy
        fields = ['id', 'scenario', 'title', 'desc', 'description', 'points_cost', 'order']

    def validate(self, attrs):
        description = attrs.pop('description', None)
        attrs['desc'] = description or attrs.get('desc') or attrs.get('title', '')
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['description'] = data.get('desc', '')
        return data


# ==========================================
# 3. 游戏化后台管理视图集
# ==========================================
class AchievementAdminViewSet(BaseAdminViewSet):
    """
    成就管理后台接口 (增删改查)
    支持 category, rarity, points, icon 的编辑，以及解锁人数分布统计
    """
    permission_classes = [IsAuthenticated, IsGameAdmin]
    serializer_class = AchievementAdminSerializer

    def get_queryset(self):
        # 核心：使用 Left Join 关联 UserAchievement 表，按成就 ID 聚合统计人数
        queryset = Achievement.objects.annotate(
            unlocked_count=Count('userachievement')
        ).order_by('-id')
        keyword = self.request.query_params.get('search', '')
        if keyword:
            queryset = queryset.filter(Q(title__icontains=keyword) | Q(code__icontains=keyword))
        return queryset


class ChallengeTaskAdminViewSet(BaseAdminViewSet):
    """
    挑战任务后台接口
    支持包含 is_active 在内的基本信息管理
    """
    permission_classes = [IsAuthenticated, IsGameAdmin]
    serializer_class = ChallengeTaskAdminSerializer

    def get_queryset(self):
        queryset = ChallengeTask.objects.all().order_by('-id')
        keyword = self.request.query_params.get('search', '')
        task_type = self.request.query_params.get('task_type', '')
        if keyword:
            queryset = queryset.filter(title__icontains=keyword)
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        return queryset


class RemedyAdminViewSet(BaseAdminViewSet):
    """
    补救方案后台接口
    """
    permission_classes = [IsAuthenticated, IsGameAdmin]
    serializer_class = RemedyAdminSerializer

    def get_queryset(self):
        queryset = Remedy.objects.all().order_by('-id')
        scenario = self.request.query_params.get('scenario', '')
        if scenario:
            queryset = queryset.filter(scenario=scenario)
        return queryset
