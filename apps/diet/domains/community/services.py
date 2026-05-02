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
    def get_feed_list(page=1, page_size=10, feed_type=None, current_user_id=None, query_user_id=None):
        skip = (page - 1) * page_size
        query = CommunityFeed.objects
        
        if query_user_id:
            query = query.filter(user_id=query_user_id)
            
        if feed_type:
            query = query.filter(feed_type=feed_type)
            
        feeds = list(query.order_by('-created_at').skip(skip).limit(page_size))
        
        user_ids = list(set([feed.user_id for feed in feeds]))
        
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
                "featured_badges": GamificationService.get_user_featured_badges(u.id)
            }

        saved_feed_ids = set()
        liked_feed_ids = set()
        if current_user_id:
            try:
                # 🚨 核心修复 1：修正导入模型名称及 action 枚举值
                from apps.diet.models.mysql.preference import UserPreference
                feed_ids_str = [str(f.id) for f in feeds]
                saved_feed_ids = set(UserPreference.objects.filter(
                    user_id=current_user_id, target_type='feed', action='save', target_id__in=feed_ids_str
                ).values_list('target_id', flat=True))
                liked_feed_ids = set(UserPreference.objects.filter(
                    user_id=current_user_id, target_type='feed', action='like', target_id__in=feed_ids_str
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
                "sport_info": feed.sport_info, 
                "is_saved": str(feed.id) in saved_feed_ids, 
                "is_liked": str(feed.id) in liked_feed_ids,
                "user": user_dict.get(feed.user_id, {"id": feed.user_id, "nickname": "未知用户", "avatar": "", "featured_badges": []})
            })
        return result

    @staticmethod
    def toggle_like(user_id, feed_id, action='like'):
        try:
            feed = CommunityFeed.objects.get(id=feed_id)
        except CommunityFeed.DoesNotExist:
            return {"error": "动态不存在"}

        if action not in ['like', 'unlike']:
            return {"error": "Invalid action"}

        from apps.diet.models.mysql.preference import UserPreference

        feed_id_str = str(feed_id)
        if action == 'like':
            _, changed = UserPreference.objects.get_or_create(
                user_id=user_id,
                target_id=feed_id_str,
                target_type='feed',
                action='like',
            )
            if changed:
                feed.update(inc__likes_count=1)
            is_liked = True
        else:
            deleted, _ = UserPreference.objects.filter(
                user_id=user_id,
                target_id=feed_id_str,
                target_type='feed',
                action='like',
            ).delete()
            if deleted and getattr(feed, 'likes_count', 0) > 0:
                feed.update(dec__likes_count=1)
            is_liked = False

        redis_client = getattr(cache, 'client', None)
        key = f"diet_feed_like:{feed_id_str}"
        if redis_client:
            try:
                r = redis_client.get_client()
                if action == 'like':
                    r.sadd(key, user_id)
                else:
                    r.srem(key, user_id)
            except Exception:
                pass
        
        feed.reload()
        return {"likes_count": feed.likes_count, "is_liked": is_liked}

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
        from apps.users.models import UserFollow
        if action == 'follow':
            UserFollow.objects.get_or_create(follower_id=follower_id, followed_id=following_id)
            return {"status": "followed"}
        elif action == 'unfollow':
            UserFollow.objects.filter(follower_id=follower_id, followed_id=following_id).delete()
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
        fans_count = UserFollow.objects.filter(followed_id=target_user_id).count()
        
        # 跨库统计该用户在 MongoDB 中发布的动态总获赞数
        try:
            feeds = CommunityFeed.objects.filter(user_id=target_user_id)
            like_count = sum(feed.likes_count for feed in feeds)
        except Exception:
            like_count = 0

        is_followed = False
        if current_user_id:
            is_followed = UserFollow.objects.filter(follower_id=current_user_id, followed_id=target_user_id).exists()

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
    
    @classmethod
    def get_feed_detail(cls, feed_id: str, current_user_id: int):
        """获取单个帖子详情"""
        from apps.diet.models.mongo.community import CommunityFeed
        # 🚨 核心修复 2：修正导入模型名称
        from apps.diet.models.mysql.preference import UserPreference
        
        try:
            feed = CommunityFeed.objects.get(id=feed_id)
            feed_data = feed.to_mongo().to_dict() if hasattr(feed, 'to_mongo') else feed
            feed_data['id'] = str(feed.id)
            if '_id' in feed_data:
                del feed_data['_id']
            
            # 修正 action
            feed_data['is_liked'] = UserPreference.objects.filter(
                user_id=current_user_id,
                target_id=feed_id,
                target_type='feed',
                action='like'
            ).exists()
            feed_data['is_saved'] = UserPreference.objects.filter(
                user_id=current_user_id, 
                target_id=feed_id, 
                target_type='feed', 
                action='save'
            ).exists()
            
            # 填充 user 信息，同 get_feed_list
            from apps.users.models import User
            from apps.diet.domains.gamification.services import GamificationService
            try:
                author = User.objects.select_related('profile').get(id=feed.user_id)
                avatar = author.profile.avatar.url if (hasattr(author, 'profile') and author.profile and author.profile.avatar) else getattr(author, 'avatar', '')
                feed_data['user'] = {
                    "id": author.id,
                    "nickname": author.nickname or "未知用户",
                    "avatar": avatar or "",
                    "featured_badges": GamificationService.get_user_featured_badges(author.id)
                }
            except User.DoesNotExist:
                feed_data['user'] = {
                    "id": feed.user_id,
                    "nickname": "未知用户",
                    "avatar": "",
                    "featured_badges": []
                }
            
            return feed_data
        except Exception as e:
            return None

    @classmethod
    def toggle_save(cls, user_id: int, feed_id: str, action: str):
        """切换帖子收藏状态"""
        from apps.diet.models.mongo.community import CommunityFeed
        # 🚨 核心修复 4：修正导入模型名称
        from apps.diet.models.mysql.preference import UserPreference
        from django.utils import timezone
        
        try:
            feed = CommunityFeed.objects.get(id=feed_id)
            
            if action == 'save':
                obj, created = UserPreference.objects.get_or_create(
                    user_id=user_id, 
                    target_id=feed_id, 
                    target_type='feed',
                    action='save',
                    defaults={'created_at': timezone.now()}
                )
                if created:
                    feed.update(inc__save_count=1)
            else:
                deleted, _ = UserPreference.objects.filter(
                    user_id=user_id, target_id=feed_id, target_type='feed', action='save'
                ).delete()
                if deleted:
                    if getattr(feed, 'save_count', 0) > 0:
                        feed.update(dec__save_count=1)
                        
            feed.reload()
            return {"save_count": getattr(feed, 'save_count', 0), "is_saved": action == 'save'}
        except Exception as e:
            return {"error": "帖子不存在或操作失败"}

    @classmethod
    def report_feed(cls, user_id: int, feed_id: str, reason: str):
        """创建举报记录"""
        from apps.admin_management.models.audit import AuditLog
        from apps.users.models import User
        
        try:
            feed = CommunityFeed.objects.get(id=feed_id)
            
            reporter = User.objects.filter(id=user_id).first()
            AuditLog.objects.create(
                operator=reporter,
                operator_name=reporter.username if reporter else f"user:{user_id}",
                method="POST",
                path=f"/api/v1/diet/community/feed/{feed_id}/report/",
                module="community_report",
                ip_address=None,
                body={"feed_id": str(feed_id), "reason": reason},
                response_code=200,
            )
            
            # 给帖子增加被举报的权重计数 (可选策略)
            feed.update(inc__report_count=1)
            
            return {"status": "reported"}
        except Exception as e:
            return {"error": "帖子不存在或处理失败"}
