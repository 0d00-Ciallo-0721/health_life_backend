from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth import get_user_model
from bson import ObjectId
from apps.admin_management.models.notification import Notification # 🚀 导入
# 引入 Models
from apps.diet.models.mongo.recipe import Recipe as MongoRecipe
from apps.diet.models.mongo.restaurant import Restaurant # 👈 确保这个也导入了
from apps.diet.models.mysql.gamification import ChallengeTask, Remedy, Achievement
from apps.admin_management.serializers.business_s import ChallengeTaskSerializer, RemedySerializer
from apps.diet.models.mongo.community import CommunityFeed, Comment

# 引入 Serializer (这是本次报错的核心)
from apps.admin_management.serializers.business_s import (
    AdminUserSerializer, 
    MongoRecipeAuditSerializer,
    MongoRestaurantSerializer,
    ChallengeTaskSerializer,
    RemedySerializer,
    AchievementSerializer,           # 🚀 新增
    MongoCommunityFeedSerializer,    # 🚀 新增
    MongoCommentSerializer           # 🚀 新增
)
from apps.admin_management.permissions import RBACPermission

User = get_user_model()


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


class RecipeAuditViewSet(viewsets.ViewSet):
    """
    菜谱审核 (MongoDB)
    因为 MongoEngine 不支持 DRF 的 ModelViewSet，所以用 ViewSet 手写
    """
    permission_classes = [IsAuthenticated, IsAdminUser, RBACPermission]
    perms_map = {
        'list': 'business:recipe:audit',
        'audit': 'business:recipe:audit' # 自定义动作权限
    }

    def list(self, request):
        """获取待审核菜谱列表"""
        # 假设 status=0 是待审核，status=1 是通过 (根据你的模型定义调整)
        # 这里演示获取所有
        recipes = MongoRecipe.objects.all().order_by('-created_at')[:20] 
        serializer = MongoRecipeAuditSerializer(recipes, many=True)
        return Response({"code": 200, "data": serializer.data})

    @action(detail=True, methods=['post'])
    def audit(self, request, pk=None):
        """审核通过/拒绝"""
        try:
            recipe = MongoRecipe.objects.get(id=ObjectId(pk))
        except Exception:
            return Response({"msg": "菜谱不存在"}, status=404)
        
        result = request.data.get('result') # pass / reject
        
        # 🚀 1. 查找菜谱作者 (假设菜谱中有 user_id 字段，或者根据 author_name 反查)
        # 注意: 你的 MongoDB Recipe 模型目前可能没有存 user_id。
        # 如果没有，我们暂时无法发给具体人，只能演示“生成了一条无主通知”或跳过发送。
        # 假设我们之前在同步数据时存了 user_id (通常应该有)，这里先模拟查找用户:
        # target_user = User.objects.filter(username=recipe.author_name).first() 
        
        # 演示用：为了测试流程，我们把通知发给当前操作的管理员自己 (或者发给 ID=1 的用户)
        target_user = request.user 
        
        if result == 'pass':
            recipe.status = 1 
            recipe.save()
            
            # 🚀 2. 自动发送通过通知
            Notification.objects.create(
                title="菜谱审核通过",
                content=f"恭喜！您上传的菜谱《{recipe.name}》已通过审核并上架。",
                type='private',
                target_user=target_user
            )
            
            return Response({"msg": "审核通过，已发送通知"})
            
        elif result == 'reject':
            recipe.status = 2
            recipe.save()
            
            # 🚀 3. 自动发送拒绝通知
            Notification.objects.create(
                title="菜谱审核未通过",
                content=f"很遗憾，您上传的菜谱《{recipe.name}》未通过审核。请检查内容后重试。",
                type='private',
                target_user=target_user
            )
            
            return Response({"msg": "已拒绝，已发送通知"})
        
        return Response({"msg": "参数错误"}, status=400)
    

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
        """获取商家列表 (支持 ?search=xxx)"""
        query = request.query_params.get('search', '')
        
        # MongoDB 模糊查询
        if query:
            queryset = Restaurant.objects(name__icontains=query)
        else:
            queryset = Restaurant.objects.all()
        
        # ⚠️ 注意: 实际生产中 MongoEngine 分页需要特殊处理
        # 这里简单起见，按缓存时间倒序取前 50 条，避免全表扫描卡死
        queryset = queryset.order_by('-cached_at')[:50]
        
        serializer = MongoRestaurantSerializer(queryset, many=True)
        return Response({"code": 200, "data": serializer.data})

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
            
        queryset = queryset.order_by('-created_at')[:50]
        serializer = MongoCommunityFeedSerializer(queryset, many=True)
        return Response({"code": 200, "data": serializer.data})

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
            
        queryset = queryset.order_by('-created_at')[:50]
        serializer = MongoCommentSerializer(queryset, many=True)
        return Response({"code": 200, "data": serializer.data})

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