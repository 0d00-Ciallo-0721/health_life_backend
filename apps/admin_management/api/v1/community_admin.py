# [新增] 整个文件内容
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count

from apps.admin_management.permissions import IsCommunityAdmin
from apps.diet.models.mongo.community import CommunityFeed, Comment
from apps.users.models_users import User, UserFollow

class CommunityFeedAdminView(APIView):
    """
    社区动态审核列表
    GET /admin/api/v1/social/feeds/
    """
    permission_classes = [IsAuthenticated, IsCommunityAdmin]

    def get(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        skip = (page - 1) * page_size

        # 1. 查询 Mongo 数据：置顶优先，再按时间倒序
        feeds = CommunityFeed.objects.order_by('-is_pinned', '-created_at').skip(skip).limit(page_size)
        total = CommunityFeed.objects.count()

        # 2. 提取跨库映射所需的所有 MySQL user_id
        user_ids = list(set([f.user_id for f in feeds]))
        users = User.objects.filter(id__in=user_ids).select_related('profile')
        
        user_map = {}
        for u in users:
            avatar = u.profile.avatar.url if (hasattr(u, 'profile') and u.profile and u.profile.avatar) else getattr(u, 'avatar', '')
            user_map[u.id] = {
                "nickname": u.nickname or "未知用户",
                "username": u.username,
                "avatar": avatar or ""
            }

        # 3. 组装最终结果
        data = []
        for feed in feeds:
            data.append({
                "id": str(feed.id),
                "user_id": feed.user_id,
                "user_info": user_map.get(feed.user_id, {"nickname": "未知用户", "avatar": ""}),
                "content": feed.content,
                "images": feed.images,
                "type": feed.feed_type,
                "sport_info": feed.sport_info,
                "likes_count": feed.likes_count,
                "comments_count": feed.comments_count,
                "is_hidden": feed.is_hidden,
                "is_pinned": feed.is_pinned,
                "created_at": feed.created_at.strftime('%Y-%m-%d %H:%M:%S') if feed.created_at else None
            })

        return Response({"code": 200, "msg": "success", "data": {"total": total, "list": data}})


class CommunityFeedActionAdminView(APIView):
    """
    社区动态管控操作
    PATCH /admin/api/v1/social/feeds/<id>/
    DELETE /admin/api/v1/social/feeds/<id>/
    """
    permission_classes = [IsAuthenticated, IsCommunityAdmin]

    def patch(self, request, feed_id):
        try:
            feed = CommunityFeed.objects.get(id=feed_id)
        except CommunityFeed.DoesNotExist:
            return Response({"code": 404, "msg": "动态不存在"}, status=404)

        action = request.data.get('action') # 'hide', 'show', 'pin', 'unpin'
        if action == 'hide':
            feed.update(set__is_hidden=True)
        elif action == 'show':
            feed.update(set__is_hidden=False)
        elif action == 'pin':
            feed.update(set__is_pinned=True)
        elif action == 'unpin':
            feed.update(set__is_pinned=False)
        else:
            return Response({"code": 400, "msg": "无效的操作类型(需为 hide/show/pin/unpin)"}, status=400)

        return Response({"code": 200, "msg": f"操作 {action} 成功", "data": None})

    def delete(self, request, feed_id):
        try:
            feed = CommunityFeed.objects.get(id=feed_id)
            # 安全的级联删除：先删除绑定的 Mongo 评论，再删除帖子本体
            Comment.objects.filter(feed_id=feed).delete()
            feed.delete()
            return Response({"code": 200, "msg": "动态及关联评论已删除", "data": None})
        except CommunityFeed.DoesNotExist:
            return Response({"code": 404, "msg": "动态不存在"}, status=404)


class UserFollowAnomalyAdminView(APIView):
    """
    关注关系与刷粉异常检测
    GET /admin/api/v1/social/follows/anomaly/
    """
    permission_classes = [IsAuthenticated, IsCommunityAdmin]

    def get(self, request):
        limit = int(request.query_params.get('limit', 50))
        
        # 核心：对 MySQL 关注表进行 Group By 和 Count 聚合，查找被关注数畸高的头部用户
        suspects = UserFollow.objects.values('following_id').annotate(
            follower_count=Count('follower_id')
        ).order_by('-follower_count')[:limit]

        user_ids = [s['following_id'] for s in suspects]
        users = User.objects.filter(id__in=user_ids)
        user_map = {u.id: {"nickname": u.nickname, "username": u.username} for u in users}

        data = []
        for s in suspects:
            uid = s['following_id']
            data.append({
                "user_id": uid,
                "user_info": user_map.get(uid, {"nickname": "未知", "username": "未知"}),
                "follower_count": s['follower_count']
            })

        return Response({"code": 200, "msg": "success", "data": data})