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
        data = CommunityService.get_feed_list(page, page_size)
        return Response({"code": 200, "msg": "success", "data": data})

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
        return Response({"code": 200, "msg": "success", "data": data})

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