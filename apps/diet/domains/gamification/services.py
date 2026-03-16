# [新增] 整个文件: apps/diet/domains/gamification/services.py
from django.utils import timezone
from django.core.cache import cache
from apps.diet.models.mysql.gamification import ChallengeTask, UserChallengeProgress

class GamificationService:
    @staticmethod
    def join_challenge(user, task_id):
        try:
            task = ChallengeTask.objects.get(id=task_id, is_active=True)
        except ChallengeTask.DoesNotExist:
            return {"error": "任务不存在或未启用"}
        
        # 检查是否已在进行中，防重复加入
        if UserChallengeProgress.objects.filter(user=user, challenge=task, status='pending').exists():
            return {"error": "您已在进行该挑战，请勿重复加入"}
            
        progress = UserChallengeProgress.objects.create(
            user=user,
            challenge=task,
            status='pending',
            progress=0
        )
        return {"id": progress.id, "status": progress.status}

    @staticmethod
    def update_progress(user, progress_id, action='check'):
        try:
            record = UserChallengeProgress.objects.get(id=progress_id, user=user)
        except UserChallengeProgress.DoesNotExist:
            return {"error": "进度记录不存在"}
        
        if action == 'abandon':
            record.status = 'abandoned'
            record.save()
            return {"status": record.status}
            
        if action == 'check' and record.status == 'pending':
            record.status = 'completed'
            record.completed_at = timezone.now()
            record.save()
            
            # 使用 Redis 的有序集合 (Sorted Set) 实现排行榜积分累加
            redis_client = getattr(cache, 'client', None)
            if redis_client:
                try:
                    # 兼容 django-redis 的原生 client 获取
                    r = redis_client.get_client()
                    leaderboard_key = "diet_leaderboard_weekly"
                    r.zincrby(leaderboard_key, record.challenge.reward_points, user.id)
                except Exception:
                    pass # 降级处理，若无 redis 则忽略
                    
            return {"status": record.status, "reward": record.challenge.reward_points}
            
        return {"status": record.status}

    @staticmethod
    def get_leaderboard(board_type='weekly', scope='global'):
        """获取排行榜数据 (依赖 Redis ZSET)"""
        redis_client = getattr(cache, 'client', None)
        if not redis_client:
            return []
        
        try:
            r = redis_client.get_client()
            key = f"diet_leaderboard_{board_type}"
            # ZREVRANGE: 按分数降序，取前 50 名
            top_users = r.zrevrange(key, 0, 49, withscores=True)
            
            results = []
            for rank, (uid, score) in enumerate(top_users):
                results.append({
                    "rank": rank + 1,
                    "user_id": int(uid),
                    "score": int(score)
                })
            return results
        except Exception:
            return []


    @staticmethod
    def get_merged_achievements(user):
        """
        全表扫描 Achievement，并 Left Join UserAchievement (模拟合并视图)
        计算出 unlocked 和 unlocked_at 返回给前端荣誉墙
        """
        from apps.diet.models.mysql.gamification import Achievement, UserAchievement
        
        # 1. 查询当前用户解锁的所有成就，提取成映射字典(避免 N+1 数据库查询)
        user_achievements = UserAchievement.objects.filter(user=user)
        unlocked_map = {ua.achievement_id: ua.unlocked_at for ua in user_achievements}
        
        # 2. 全表扫描字典表
        all_achievements = Achievement.objects.all()
        
        results = []
        for a in all_achievements:
            unlocked_at = unlocked_map.get(a.id)
            results.append({
                "id": str(a.id),
                "name": a.title,            # 对齐前端字段名 name
                "description": a.desc,      # 对齐前端字段名 description
                "icon": a.icon or "",
                "category": a.category,
                "rarity": a.rarity,
                "points": a.points,
                "unlocked": a.id in unlocked_map,
                "unlocked_at": unlocked_at.isoformat() if unlocked_at else None
            })
            
        return results

    @staticmethod
    def get_user_featured_badges(user_id):
        """
        供其他模块（如 Profile 和 Community）调用
        获取用户个性名片代表徽章 (最多 3 个)，若未设置则兜底最近解锁的徽章
        """
        from apps.diet.models.mysql.gamification import UserFeaturedBadge, UserAchievement
        
        # 1. 尝试查询用户主动配置的代表徽章
        featured = UserFeaturedBadge.objects.filter(user_id=user_id)\
            .select_related('achievement').order_by('sort_order')[:3]
        
        if not featured.exists():
            # 2. 兜底策略：取最近解锁的 3 个徽章
            fallback = UserAchievement.objects.filter(user_id=user_id)\
                .select_related('achievement').order_by('-unlocked_at')[:3]
            
            return [{
                "id": str(item.achievement.id),
                "name": item.achievement.title,
                "icon": item.achievement.icon or ""
            } for item in fallback]

        return [{
            "id": str(badge.achievement.id),
            "name": badge.achievement.title,
            "icon": badge.achievement.icon or ""
        } for badge in featured]