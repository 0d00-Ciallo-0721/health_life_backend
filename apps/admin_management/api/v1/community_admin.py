# [新增] 整个文件内容
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count
from django.utils import timezone
from pymongo.errors import PyMongoError

from apps.admin_management.permissions import IsCommunityAdmin
from apps.diet.models.mongo.community import CommunityFeed, Comment
from apps.users.models import User, UserFollow


def mongo_feed_list_unavailable_response():
    return Response({
        "code": 200,
        "msg": "MongoDB 服务未连接，动态风控列表已降级为空",
        "data": {"total": 0, "list": []}
    })


def mongo_feed_action_unavailable_response():
    return Response({"code": 503, "msg": "MongoDB 服务未连接，当前无法操作动态"}, status=503)

class CommunityFeedAdminView(APIView):
    """
    社区动态审核列表
    GET /admin/api/v1/social/feeds/
    """
    permission_classes = [IsAuthenticated, IsCommunityAdmin]

    def get(self, request):
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            skip = (page - 1) * page_size
            keyword = request.query_params.get('search', '').strip()

            # 1. 查询 Mongo 数据：置顶优先，再按时间倒序
            queryset = CommunityFeed.objects
            if keyword:
                queryset = queryset.filter(content__icontains=keyword)

            feeds = queryset.order_by('-is_pinned', '-created_at').skip(skip).limit(page_size)
            total = queryset.count()

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
        except PyMongoError:
            return mongo_feed_list_unavailable_response()


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
        except PyMongoError:
            return mongo_feed_action_unavailable_response()
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
        except PyMongoError:
            return mongo_feed_action_unavailable_response()
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
        suspects = UserFollow.objects.values('followed_id').annotate(
            follower_count=Count('follower_id')
        ).order_by('-follower_count')[:limit]

        user_ids = [s['followed_id'] for s in suspects]
        users = User.objects.filter(id__in=user_ids)
        user_map = {u.id: {"nickname": u.nickname, "username": u.username} for u in users}

        data = []
        for s in suspects:
            uid = s['followed_id']
            user_info = user_map.get(uid, {"nickname": "未知", "username": "未知"})
            follower_count = s['follower_count']
            risk_level = 'HIGH' if follower_count >= 1000 else 'MEDIUM'
            data.append({
                "id": uid,
                "user_id": uid,
                "username": user_info["username"],
                "nickname": user_info["nickname"],
                "user_info": user_info,
                "follower_count": follower_count,
                "recent_followers_gained": follower_count,
                "risk_level": risk_level,
                "detected_at": timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        return Response({"code": 200, "msg": "success", "data": data})
