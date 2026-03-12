# [新增] 整个文件: apps/diet/domains/community/services.py
from django.core.cache import cache
from apps.diet.models.mongo.community import CommunityFeed, Comment

class CommunityService:
    @staticmethod
    def publish_feed(user_id, data):
        feed = CommunityFeed(
            user_id=user_id,
            content=data.get('content', ''),
            images=data.get('images', []),
            feed_type=data.get('type', 'post'),
            target_id=data.get('target_id', '')
        )
        feed.save()
        return str(feed.id)

    @staticmethod
    def get_feed_list(page=1, page_size=10, feed_type=None):
        skip = (page - 1) * page_size
        query = CommunityFeed.objects
        
        if feed_type:
            query = query.filter(feed_type=feed_type)
            
        feeds = query.order_by('-created_at').skip(skip).limit(page_size)
        
        result = []
        for feed in feeds:
            result.append({
                "id": str(feed.id),
                "user_id": feed.user_id,
                "content": feed.content,
                "images": feed.images,
                "type": feed.feed_type,
                "target_id": feed.target_id,
                "likes_count": feed.likes_count,
                "comments_count": feed.comments_count,
                "created_at": feed.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        return result

    @staticmethod
    def toggle_like(user_id, feed_id, action='like'):
        try:
            feed = CommunityFeed.objects.get(id=feed_id)
        except CommunityFeed.DoesNotExist:
            return {"error": "动态不存在"}
        
        redis_client = getattr(cache, 'client', None)
        key = f"diet_feed_like:{feed_id}"
        
        if redis_client:
            try:
                r = redis_client.get_client()
                if action == 'like':
                    added = r.sadd(key, user_id)
                    if added: # 防止重复点赞增加计数
                        feed.update(inc__likes_count=1)
                else:
                    removed = r.srem(key, user_id)
                    if removed and feed.likes_count > 0:
                        feed.update(dec__likes_count=1)
            except Exception:
                pass # 降级处理
        
        feed.reload()
        return {"likes_count": feed.likes_count}

    @staticmethod
    def add_comment(user_id, feed_id, content):
        try:
            feed = CommunityFeed.objects.get(id=feed_id)
        except CommunityFeed.DoesNotExist:
            return {"error": "动态不存在"}
        
        comment = Comment(feed_id=feed, user_id=user_id, content=content)
        comment.save()
        feed.update(inc__comments_count=1)
        
        return {
            "id": str(comment.id),
            "content": comment.content,
            "created_at": comment.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

    @staticmethod
    def get_comments(feed_id):
        try:
            feed = CommunityFeed.objects.get(id=feed_id)
        except CommunityFeed.DoesNotExist:
            return []
        
        comments = Comment.objects.filter(feed_id=feed).order_by('-created_at')
        return [{
            "id": str(c.id),
            "user_id": c.user_id,
            "content": c.content,
            "created_at": c.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for c in comments]