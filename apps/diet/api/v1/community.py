# [新增] 整个文件: apps/diet/api/v1/community.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.diet.domains.community.services import CommunityService
from rest_framework.parsers import MultiPartParser
from django.core.files.storage import default_storage
import uuid
import os


class CommunityFeedView(APIView):
    """动态流: GET/POST /diet/community/feed/ 及 POST /diet/community/share/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        
        # 1. 基础数据查询 (来自 Service 层，已含有基础的 is_saved, is_liked 判定)
        data = CommunityService.get_feed_list(page, page_size, current_user_id=request.user.id)
        
        # 2. [新增] 增强层：动态聚合用户徽章、组装标准数据结构
        from apps.diet.serializers.community import FeedResponseEnhancer
        enhanced_data = FeedResponseEnhancer.enhance_feed_list(data, request.user)
        
        return Response({"code": 200, "msg": "success", "data": {"list": enhanced_data}})
    
    def post(self, request):
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
    


# [新增] 核心业务逻辑 ====================
class UserProfileView(APIView):
    """
    用户主页个人公开信息 
    GET /user/{userId}/profile/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, userId):
        from django.shortcuts import get_object_or_404
        from apps.users.models import User, Profile, UserFollow
        from apps.diet.models.mongo.community import CommunityFeed
        from apps.diet.models.mysql.gamification import UserFeaturedBadge
        
        target_user = get_object_or_404(User, id=userId)
        profile, _ = Profile.objects.get_or_create(user=target_user)
        
        # 1. 社交统计
        follow_count = UserFollow.objects.filter(follower=target_user).count()
        fans_count = UserFollow.objects.filter(followed=target_user).count()
        is_followed = UserFollow.objects.filter(follower=request.user, followed=target_user).exists()
        
        # 2. 从 MongoDB 获取获赞数
        try:
            posts = CommunityFeed.objects.filter(user_id=target_user.id)
            like_count = sum([p.likes_count for p in posts])
        except Exception:
            like_count = 0
            
        # 3. 拉取名片代表徽章
        featured = UserFeaturedBadge.objects.filter(user=target_user).select_related('achievement')
        badges = [{"id": str(b.achievement.id), "name": b.achievement.title, "icon": b.achievement.icon} for b in featured]

        # 4. 头像防腐处理
        avatar_url = target_user.avatar
        if not avatar_url and getattr(profile, 'avatar', None):
            avatar_url = profile.avatar.url if hasattr(profile.avatar, 'url') else str(profile.avatar)

        data = {
            "id": target_user.id,
            "nickname": target_user.nickname or target_user.username,
            "avatar": avatar_url,
            "signature": getattr(profile, 'signature', ''),
            "follow_count": follow_count,
            "fans_count": fans_count,
            "like_count": like_count,
            "is_followed": is_followed,
            "featured_badges": badges
        }
        return Response({"code": 200, "msg": "success", "data": data})

class UserPostsView(APIView):
    """
    获取用户的动态列表 (含聚合)
    GET /user/{userId}/posts/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, userId):
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
        except ValueError:
            page, page_size = 1, 10
            
        from apps.diet.models.mongo.community import CommunityFeed
        from apps.diet.serializers.community import FeedResponseEnhancer
        
        skip = (page - 1) * page_size
        # 降序查询 MongoDB 个人帖子，排除违规隐藏项
        qs = CommunityFeed.objects.filter(user_id=int(userId), is_hidden=False).order_by('-created_at')[skip:skip+page_size]
        
        raw_list = []
        for post in qs:
            raw_list.append({
                "id": str(post.id),
                "user_id": post.user_id,
                "content": post.content,
                "type": post.feed_type,
                "images": post.images,
                "sport_info": post.sport_info,
                "likes_count": post.likes_count,
                "comments_count": post.comments_count,
                "created_at": post.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
            
        # [复用聚合层] 批量补齐徽章、用户信息及状态
        enhanced_data = FeedResponseEnhancer.enhance_feed_list(raw_list, request.user)
        
        return Response({"code": 200, "msg": "success", "data": {"list": enhanced_data}})


class CommunityUploadView(APIView):
    """
    社区发帖图片上传
    POST /community/upload/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        upload_file = request.FILES.get('file')
        if not upload_file:
            return Response({"code": 400, "msg": "请上传图片文件"})
            
        custom_name = request.data.get('name', upload_file.name)
        
        # 存储文件到媒体库 (community_uploads/ 目录下)
        ext = os.path.splitext(upload_file.name)[1]
        filename = f"community_uploads/{uuid.uuid4().hex}{ext}"
        saved_path = default_storage.save(filename, upload_file)
        
        # 获取可通过 HTTP 访问的 URL (受 settings.MEDIA_URL 控制)
        file_url = default_storage.url(saved_path)
        
        # 返回与前端约定的格式
        data = {
            "url": file_url,         # 前端将提取该 url 用于 posts.images
            "name": custom_name,
            "mime_type": upload_file.content_type,
            "size": upload_file.size
        }
        return Response({"code": 200, "msg": "上传成功", "data": data})