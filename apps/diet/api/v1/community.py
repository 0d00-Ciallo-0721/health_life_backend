# [新增] 整个文件: apps/diet/api/v1/community.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.diet.domains.community.services import CommunityService

class CommunityFeedView(APIView):
    """动态流: GET/POST /diet/community/feed/ 及 POST /diet/community/share/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        # [修改] 传递 request.user.id 进去用于 is_saved 状态判断
        data = CommunityService.get_feed_list(page, page_size, current_user_id=request.user.id)
        return Response({"code": 200, "msg": "success", "data": {"list": data}})
    
    def post(self, request):
        # 兼容 /share/ 和 /feed/ POST
        feed_id = CommunityService.publish_feed(request.user.id, request.data)
        return Response({"code": 200, "msg": "发布成功", "data": {"id": feed_id}})

class CommunityShareListView(APIView):
    """分类分享列表: GET /diet/community/recipes/ 或 /restaurants/"""
    permission_classes = [IsAuthenticated]
    feed_type = 'recipe' # 子类可覆盖

    def get(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        data = CommunityService.get_feed_list(page, page_size, feed_type=self.feed_type)
        return Response({"code": 200, "msg": "success", "data": {"list": data}})

class CommunityLikeView(APIView):
    """点赞与取消: POST/DELETE /diet/community/feed/{feedId}/like/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, feedId):
        res = CommunityService.toggle_like(request.user.id, feedId, action='like')
        if "error" in res:
            return Response({"code": 404, "msg": res["error"]}, status=404)
        return Response({"code": 200, "msg": "点赞成功", "data": res})

    def delete(self, request, feedId):
        res = CommunityService.toggle_like(request.user.id, feedId, action='unlike')
        if "error" in res:
            return Response({"code": 404, "msg": res["error"]}, status=404)
        return Response({"code": 200, "msg": "已取消点赞", "data": res})

class CommunityCommentView(APIView):
    """评论操作: GET/POST /diet/community/feed/{feedId}/comments/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, feedId):
        data = CommunityService.get_comments(feedId)
        return Response({"code": 200, "msg": "success", "data": data})

    def post(self, request, feedId):
        content = request.data.get("content")
        if not content:
            return Response({"code": 400, "msg": "评论内容不能为空"}, status=400)
            
        res = CommunityService.add_comment(request.user.id, feedId, content)
        if "error" in res:
            return Response({"code": 404, "msg": res["error"]}, status=404)
        return Response({"code": 200, "msg": "评论成功", "data": res})
    

# [新增] 用户关注操作视图
class UserFollowView(APIView):
    """关注/取消关注: POST/DELETE /user/{userId}/follow/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, userId):
        if str(request.user.id) == str(userId):
            return Response({"code": 400, "msg": "不能关注自己"}, status=400)
        res = CommunityService.toggle_follow(request.user.id, userId, 'follow')
        return Response({"code": 200, "msg": "关注成功", "data": res})

    def delete(self, request, userId):
        res = CommunityService.toggle_follow(request.user.id, userId, 'unfollow')
        return Response({"code": 200, "msg": "已取消关注", "data": res})

# [新增] 用户公共主页视图
class UserProfileByIdView(APIView):
    """用户公开主页: GET /user/{userId}/profile/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, userId):
        data = CommunityService.get_user_profile(userId, request.user.id)
        if not data:
            return Response({"code": 404, "msg": "用户不存在"}, status=404)
        return Response({"code": 200, "msg": "success", "data": data})    
    

# [新增] 帖子详情视图
class CommunityFeedDetailView(APIView):
    """
    帖子详情
    GET /community/feed/{feedId}/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, feedId):
        data = CommunityService.get_feed_detail(feedId, current_user_id=request.user.id)
        if not data:
            return Response({"code": 404, "msg": "帖子不存在或已被删除"})
        return Response({"code": 200, "msg": "success", "data": data})

# [新增] 帖子收藏视图
class CommunitySaveView(APIView):
    """
    收藏/取消收藏
    POST/DELETE /community/feed/{feedId}/save/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, feedId):
        res = CommunityService.toggle_save(request.user.id, feedId, 'save')
        if "error" in res:
            return Response({"code": 400, "msg": res["error"]})
        return Response({"code": 200, "msg": "收藏成功", "data": res})

    def delete(self, request, feedId):
        res = CommunityService.toggle_save(request.user.id, feedId, 'unsave')
        if "error" in res:
            return Response({"code": 400, "msg": res["error"]})
        return Response({"code": 200, "msg": "已取消收藏", "data": res})

# [新增] 帖子举报视图
class CommunityReportView(APIView):
    """
    举报
    POST /community/feed/{feedId}/report/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, feedId):
        reason = request.data.get("reason", "内容违规")
        res = CommunityService.report_feed(request.user.id, feedId, reason)
        if "error" in res:
            return Response({"code": 400, "msg": res["error"]})
        return Response({"code": 200, "msg": "举报成功，感谢您的反馈", "data": res})    