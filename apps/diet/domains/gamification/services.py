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