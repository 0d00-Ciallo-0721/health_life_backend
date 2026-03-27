from rest_framework import viewsets, status
from rest_framework.views import APIView 
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth import get_user_model
from bson import ObjectId
from apps.admin_management.models.notification import Notification 

# 引入 Models
from apps.diet.models.mongo.recipe import Recipe as MongoRecipe
from apps.diet.models.mongo.restaurant import Restaurant
from apps.diet.models.mysql.gamification import ChallengeTask, Remedy, Achievement
from apps.diet.models.mongo.community import CommunityFeed, Comment

# 引入 Serializer
from apps.admin_management.serializers.business_s import (
    AdminUserSerializer, 
    MongoRecipeAuditSerializer,
    MongoRestaurantSerializer,
    ChallengeTaskSerializer,
    RemedySerializer,
    AchievementSerializer,           
    MongoCommunityFeedSerializer,    
    MongoCommentSerializer           
)
from apps.admin_management.permissions import RBACPermission

User = get_user_model()
# 🚀 [新增核心函数]：MongoEngine 通用分页器
def paginate_mongo_queryset(request, queryset, serializer_class):
    """
    针对 MongoEngine QuerySet 的通用分页辅助函数
    返回格式适配主流后台表格: { total, page, size, list }
    """
    try:
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('size', 20)) # 默认20条
    except ValueError:
        page = 1
        page_size = 20

    total = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    
    # 利用 MongoEngine 的切片特性做 Skip 和 Limit
    paginated_qs = queryset[start:end]
    serializer = serializer_class(paginated_qs, many=True)
    
    return {
        "total": total,
        "page": page,
        "size": page_size,
        "list": serializer.data
    }


class UserManageViewSet(viewsets.ModelViewSet):
    """
    用户管理：查看列表、禁用/启用用户
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsAdminUser, RBACPermission]
    
    # 定义搜索字段 (需要安装 django-filter 或手动实现，这里简单演示手动过滤)
    def get_queryset(self):
        qs = super().get_queryset()
        keyword = self.request.query_params.get('search', '')
        if keyword:
            qs = qs.filter(username__icontains=keyword) | qs.filter(nickname__icontains=keyword)
        return qs

    # 权限映射
    perms_map = {
        'list': 'business:user:list',
        'update': 'business:user:edit',
        'partial_update': 'business:user:edit',
    }
    
    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """封禁/解封用户"""
        user = self.get_object()
        # 反转状态
        user.is_active = not user.is_active
        user.save()
        status_text = "启用" if user.is_active else "禁用"
        return Response({"msg": f"用户已{status_text}"})
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # 处理分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = self._inject_profile_data(serializer.data, [obj.id for obj in page])
            return self.get_paginated_response(data)

        serializer = self.get_serializer(queryset, many=True)
        data = self._inject_profile_data(serializer.data, [obj.id for obj in queryset])
        return Response({"code": 200, "data": data})

    # 🚀 [新增] 跨表注入辅助方法
    def _inject_profile_data(self, data, user_ids):
        from apps.users.models import User, UserFollow, Profile
        # 批量查询 Profile 避免 N+1
        profiles = Profile.objects.filter(user_id__in=user_ids)
        profile_map = {p.user_id: p for p in profiles}
        
        goal_map = {'lose': '减脂', 'maintain': '保持', 'gain': '增肌'}
        
        for item in data:
            p = profile_map.get(item['id'])
            if p:
                item['goal_type'] = goal_map.get(p.goal_type, '未知')
                item['water_goal_cups'] = p.water_goal_cups
            else:
                item['goal_type'] = '未知'
                item['water_goal_cups'] = 8 # 默认值
                
        return data




class RecipeAuditViewSet(viewsets.ViewSet):
    """
    菜谱审核 (MongoDB) - 🚀 包含跨库数据一致性防御处理
    """
    permission_classes = [IsAuthenticated, IsAdminUser, RBACPermission]
    perms_map = {
        'list': 'business:recipe:audit',
        'audit': 'business:recipe:audit' 
    }

    def list(self, request):
        """获取待审核菜谱列表 (已接入通用分页器)"""
        # 注意: 如果你已经在上一步引入了 paginate_mongo_queryset，这里继续使用它
        recipes = MongoRecipe.objects.all().order_by('-created_at')
        # 如果未引入分页函数，请使用切片；如果已引入，请替换为 paginate_mongo_queryset
        serializer = MongoRecipeAuditSerializer(recipes[:20], many=True)
        return Response({"code": 200, "data": serializer.data})

    @action(detail=True, methods=['post'])
    def audit(self, request, pk=None):
        """审核通过/拒绝"""
        try:
            recipe = MongoRecipe.objects.get(id=ObjectId(pk))
        except Exception:
            return Response({"msg": "菜谱不存在"}, status=404)
        
        result = request.data.get('result') # 'pass' 或 'reject'
        
        # 🚀 跨库关联与容错处理 (MongoDB -> MySQL)
        target_user = None
        
        # 1. 尝试通过 Integer ID 关联 (最佳实践)
        user_id = getattr(recipe, 'author_id', None) or getattr(recipe, 'user_id', None)
        
        if user_id:
            target_user = User.objects.filter(id=user_id).first()
        else:
            # 2. 降级：如果 MongoDB 只存了用户名字符串
            author_name = getattr(recipe, 'author_name', getattr(recipe, 'author', None))
            if author_name:
                target_user = User.objects.filter(username=author_name).first()
                
        # 🛡️ 容错防御：处理"孤岛数据"
        if not target_user:
            # 即便作者信息丢失，我们依然要完成审核状态的变更，但不触发崩溃
            print(f"⚠️ [Data Inconsistency] 菜谱 ID:{pk} 对应的作者在 MySQL 中丢失。跳过发信。")
        
        # ------------------------------------------------------------------
        # 状态机流转与通知派发
        # ------------------------------------------------------------------
        if result == 'pass':
            recipe.status = 1 
            recipe.save()
            
            if target_user:
                Notification.objects.create(
                    title="菜谱审核通过",
                    content=f"恭喜！您上传的菜谱《{recipe.name}》已通过审核并上架。",
                    type='private',
                    target_user=target_user
                )
            return Response({"code": 200, "msg": "审核通过，数据已落库"})
            
        elif result == 'reject':
            recipe.status = 2
            recipe.save()
            
            if target_user:
                Notification.objects.create(
                    title="菜谱审核未通过",
                    content=f"很遗憾，您上传的菜谱《{recipe.name}》未通过审核。请检查内容后重试。",
                    type='private',
                    target_user=target_user
                )
            return Response({"code": 200, "msg": "审核已拒绝，数据已落库"})
        
        return Response({"code": 400, "msg": "审核结果参数(result)缺失或错误"}, status=400)

from apps.diet.models.mongo.restaurant import Restaurant
# ... (保留原有 import)

class RestaurantViewSet(viewsets.ViewSet):
    """
    LBS 商家管理 (MongoDB)
    """
    permission_classes = [IsAuthenticated, IsAdminUser, RBACPermission]
    perms_map = {
        'list': 'business:restaurant:list',
        'create': 'business:restaurant:add',
        'update': 'business:restaurant:edit',
        'partial_update': 'business:restaurant:edit',
        'destroy': 'business:restaurant:delete',
    }

    def list(self, request):
        """获取商家列表"""
        query = request.query_params.get('search', '')
        if query:
            queryset = Restaurant.objects(name__icontains=query)
        else:
            queryset = Restaurant.objects.all()
        
        queryset = queryset.order_by('-cached_at')
        
        # 🚀 使用分页器
        data = paginate_mongo_queryset(request, queryset, MongoRestaurantSerializer)
        return Response({"code": 200, "data": data})

    def create(self, request):
        """新增商家"""
        serializer = MongoRestaurantSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"code": 200, "msg": "创建成功", "data": serializer.data})
        return Response({"code": 400, "msg": serializer.errors})

    def retrieve(self, request, pk=None):
        """获取详情"""
        try:
            obj = Restaurant.objects.get(id=ObjectId(pk))
            serializer = MongoRestaurantSerializer(obj)
            return Response({"code": 200, "data": serializer.data})
        except Exception:
            return Response({"code": 404, "msg": "商家不存在"})

    def update(self, request, pk=None):
        """修改商家"""
        try:
            obj = Restaurant.objects.get(id=ObjectId(pk))
            serializer = MongoRestaurantSerializer(obj, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({"code": 200, "msg": "更新成功", "data": serializer.data})
            return Response({"code": 400, "msg": serializer.errors})
        except Exception:
            return Response({"code": 404, "msg": "商家不存在"})

    def destroy(self, request, pk=None):
        """删除商家"""
        try:
            obj = Restaurant.objects.get(id=ObjectId(pk))
            obj.delete()
            return Response({"code": 200, "msg": "删除成功"})
        except Exception:
            return Response({"code": 404, "msg": "商家不存在"})
        


class ChallengeTaskViewSet(viewsets.ModelViewSet):
    """
    健康挑战任务管理
    """
    queryset = ChallengeTask.objects.all().order_by('-id')
    serializer_class = ChallengeTaskSerializer
    permission_classes = [IsAuthenticated, IsAdminUser, RBACPermission]
    
    # 定义搜索与过滤
    def get_queryset(self):
        qs = super().get_queryset()
        # 按标题搜索
        keyword = self.request.query_params.get('search', '')
        if keyword:
            qs = qs.filter(title__icontains=keyword)
        
        # 按类型过滤 (daily/weekly)
        task_type = self.request.query_params.get('type', '')
        if task_type:
            qs = qs.filter(task_type=task_type)
            
        return qs

    perms_map = {
        'list': 'business:task:list',
        'create': 'business:task:add',
        'update': 'business:task:edit',
        'partial_update': 'business:task:edit',
        'destroy': 'business:task:delete',
    }


class RemedyViewSet(viewsets.ModelViewSet):
    """
    补救方案管理
    """
    queryset = Remedy.objects.all().order_by('scenario', 'order')
    serializer_class = RemedySerializer
    permission_classes = [IsAuthenticated, IsAdminUser, RBACPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        # 按场景过滤 (overeat/stay_up...)
        scenario = self.request.query_params.get('scenario', '')
        if scenario:
            qs = qs.filter(scenario=scenario)
        return qs

    perms_map = {
        'list': 'business:remedy:list',
        'create': 'business:remedy:add',
        'update': 'business:remedy:edit',
        'partial_update': 'business:remedy:edit',
        'destroy': 'business:remedy:delete',
    }        



class AchievementViewSet(viewsets.ModelViewSet):
    """
    成就字典管理
    """
    queryset = Achievement.objects.all().order_by('-id')
    serializer_class = AchievementSerializer
    permission_classes = [IsAuthenticated, IsAdminUser, RBACPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        keyword = self.request.query_params.get('search', '')
        if keyword:
            qs = qs.filter(title__icontains=keyword) | qs.filter(code__icontains=keyword)
        return qs

    perms_map = {
        'list': 'business:achievement:list',
        'create': 'business:achievement:add',
        'update': 'business:achievement:edit',
        'partial_update': 'business:achievement:edit',
        'destroy': 'business:achievement:delete',
    }

class CommunityFeedViewSet(viewsets.ViewSet):
    """
    社区动态审核/管理 (MongoDB)
    """
    permission_classes = [IsAuthenticated, IsAdminUser, RBACPermission]
    perms_map = {
        'list': 'business:feed:list',
        'destroy': 'business:feed:delete',  # 管理员直接删除违规帖子
    }

    def list(self, request):
        query = request.query_params.get('search', '')
        if query:
            queryset = CommunityFeed.objects(content__icontains=query)
        else:
            queryset = CommunityFeed.objects.all()
            
        queryset = queryset.order_by('-created_at')
        
        # 🚀 使用分页器
        data = paginate_mongo_queryset(request, queryset, MongoCommunityFeedSerializer)
        return Response({"code": 200, "data": data})

    def destroy(self, request, pk=None):
        try:
            obj = CommunityFeed.objects.get(id=ObjectId(pk))
            obj.delete() # Comment 设置了 cascade，关联评论会自动删除
            return Response({"code": 200, "msg": "违规动态删除成功"})
        except Exception:
            return Response({"code": 404, "msg": "动态不存在"})

class CommentViewSet(viewsets.ViewSet):
    """
    社区评论审核/管理 (MongoDB)
    """
    permission_classes = [IsAuthenticated, IsAdminUser, RBACPermission]
    perms_map = {
        'list': 'business:comment:list',
        'destroy': 'business:comment:delete',
    }

    def list(self, request):
        query = request.query_params.get('search', '')
        if query:
            queryset = Comment.objects(content__icontains=query)
        else:
            queryset = Comment.objects.all()
            
        queryset = queryset.order_by('-created_at')
        
        # 🚀 使用分页器
        data = paginate_mongo_queryset(request, queryset, MongoCommentSerializer)
        return Response({"code": 200, "data": data})

    def destroy(self, request, pk=None):
        try:
            obj = Comment.objects.get(id=ObjectId(pk))
            
            # 手动扣减动态的评论数
            if obj.feed_id:
                obj.feed_id.update(dec__comments_count=1)
                
            obj.delete()
            return Response({"code": 200, "msg": "违规评论删除成功"})
        except Exception:
            return Response({"code": 404, "msg": "评论不存在"})
        

class JournalMacroStatsView(APIView):
    """
    日志与健康管理宏观数据聚合 (供后台 Dashboard 图表调用)
    GET /admin/api/v1/business/stats/journal/
    """
    permission_classes = [IsAuthenticated, IsAdminUser, RBACPermission]
    # 对齐阶段一初始化的健康业务顶级菜单权限
    perms_map = {'get': 'health:manage'} 

    def get(self, request):
        from apps.diet.models.mysql.journal import WaterIntake, DailyIntake
        from django.utils import timezone
        
        today = timezone.now().date()
        
        # 1. 饮水达标率统计
        water_records = WaterIntake.objects.filter(date=today).select_related('user__profile')
        total_water_users = water_records.count()
        completed_users = 0
        total_cups = 0
        
        for record in water_records:
            total_cups += record.cups
            # 动态判断用户的目标，若无 Profile 则按默认 8 杯算
            goal = record.user.profile.water_goal_cups if (hasattr(record.user, 'profile') and record.user.profile) else 8
            if record.cups >= goal:
                completed_users += 1
                
        water_completion_rate = round(completed_users / total_water_users * 100, 2) if total_water_users > 0 else 0.0
        
        # 2. 平均打卡情况 (今日饮食记录)
        intake_users_count = DailyIntake.objects.filter(record_date=today).values('user_id').distinct().count()
        total_intake_records = DailyIntake.objects.filter(record_date=today).count()
        avg_intake_per_user = round(total_intake_records / intake_users_count, 1) if intake_users_count > 0 else 0.0
        
        data = {
            "today": today.strftime('%Y-%m-%d'),
            "water_stats": {
                "total_users_logged": total_water_users,
                "completed_users": completed_users,
                "completion_rate_pct": water_completion_rate,
                "total_cups_drank": total_cups
            },
            "intake_stats": {
                "total_users_logged": intake_users_count,
                "total_records": total_intake_records,
                "avg_records_per_user": avg_intake_per_user
            }
        }
        
        return Response({"code": 200, "msg": "success", "data": data})        