# [新增] 整个文件: apps/diet/domains/community/services.py
from django.core.cache import cache
from apps.diet.models.mongo.community import CommunityFeed, Comment

class CommunityService:
    @staticmethod
    def publish_feed(user_id, data):
        # [修改] 支持持久化 sport_info 数据
        feed = CommunityFeed(
            user_id=user_id,
            content=data.get('content', ''),
            images=data.get('images', []),
            feed_type=data.get('type', 'post'),
            target_id=data.get('target_id', ''),
            sport_info=data.get('sport_info', {}) # [新增]
        )
        feed.save()
        return str(feed.id)

    @staticmethod
    def get_feed_list(page=1, page_size=10, feed_type=None, current_user_id=None):
        # [修改] 签名新增 current_user_id 用于判断 is_saved。重构了跨库聚合的逻辑！
        skip = (page - 1) * page_size
        query = CommunityFeed.objects
        
        if feed_type:
            query = query.filter(feed_type=feed_type)
            
        feeds = query.order_by('-created_at').skip(skip).limit(page_size)
        
        # --- 核心难点处理：跨库内存 Join ---
        # 1. 提取去重后的 MySQL user_id 集合
        user_ids = list(set([feed.user_id for feed in feeds]))
        
        # 2. 批量查出对应的 User 信息 (带头像、昵称)
        from apps.users.models import User, UserFollow
        from apps.diet.domains.gamification.services import GamificationService
        
        users_qs = User.objects.filter(id__in=user_ids).select_related('profile')
        user_dict = {}
        for u in users_qs:
            avatar = u.profile.avatar.url if (hasattr(u, 'profile') and u.profile and u.profile.avatar) else getattr(u, 'avatar', '')
            user_dict[u.id] = {
                "id": u.id,
                "nickname": u.nickname or "未知用户",
                "avatar": avatar or "",
                # 3. 注入阶段二实现的个性名片代表徽章
                "featured_badges": GamificationService.get_user_featured_badges(u.id)
            }

        # 4. 判断当前用户的 is_saved 收藏状态
        saved_feed_ids = set()
        if current_user_id:
            try:
                # 尝试连接第五阶段才正式搭建的 Preference 表，无表时做平滑回落
                from apps.diet.models.mysql.preference import Preference
                feed_ids_str = [str(f.id) for f in feeds]
                saved_feed_ids = set(Preference.objects.filter(
                    user_id=current_user_id, target_type='feed', action='save', target_id__in=feed_ids_str
                ).values_list('target_id', flat=True))
            except ImportError:
                pass 

        result = []
        for feed in feeds:
            result.append({
                "id": str(feed.id),
                "content": feed.content,
                "images": feed.images,
                "type": feed.feed_type,
                "target_id": feed.target_id,
                "likes_count": feed.likes_count,
                "comments_count": feed.comments_count,
                "created_at": feed.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "sport_info": feed.sport_info, # [新增]
                "is_saved": str(feed.id) in saved_feed_ids, # [新增]
                # [新增] 替换掉原本简单的 user_id，注入复杂的 user 对象
                "user": user_dict.get(feed.user_id, {"id": feed.user_id, "nickname": "未知用户", "avatar": "", "featured_badges": []})
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
    

    @staticmethod
    def toggle_follow(follower_id, following_id, action):
        """关注或取消关注系统"""
        from apps.users.models import User, UserFollow
        if action == 'follow':
            UserFollow.objects.get_or_create(follower_id=follower_id, following_id=following_id)
            return {"status": "followed"}
        elif action == 'unfollow':
            UserFollow.objects.filter(follower_id=follower_id, following_id=following_id).delete()
            return {"status": "unfollowed"}
        return {"error": "Invalid action"}    
    
    @staticmethod
    def get_user_profile(target_user_id, current_user_id=None):
        """获取社交维度的用户公共主页全景视图"""
        from apps.users.models import User, UserFollow
        try:
            target_user = User.objects.select_related('profile').get(id=target_user_id)
        except User.DoesNotExist:
            return None

        # 统计数据：粉丝数、关注数
        follow_count = UserFollow.objects.filter(follower_id=target_user_id).count()
        fans_count = UserFollow.objects.filter(following_id=target_user_id).count()
        
        # 跨库统计该用户在 MongoDB 中发布的动态总获赞数
        feeds = CommunityFeed.objects.filter(user_id=target_user_id)
        like_count = sum(feed.likes_count for feed in feeds)

        is_followed = False
        if current_user_id:
            is_followed = UserFollow.objects.filter(follower_id=current_user_id, following_id=target_user_id).exists()

        avatar = target_user.profile.avatar.url if (hasattr(target_user, 'profile') and target_user.profile and target_user.profile.avatar) else getattr(target_user, 'avatar', '')
        signature = target_user.profile.signature if hasattr(target_user, 'profile') else ""

        return {
            "id": target_user.id,
            "nickname": target_user.nickname,
            "avatar": avatar or "",
            "signature": signature or "",
            "follow_count": follow_count,
            "fans_count": fans_count,
            "like_count": like_count,
            "is_followed": is_followed
        }    