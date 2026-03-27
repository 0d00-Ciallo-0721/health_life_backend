# [新增] 处理用户维度的业务逻辑
from django.db import transaction
from apps.common.exceptions import BusinessException
from .models import User, UserFollow

class UserFollowService:
    """处理用户关注/取消关注的业务逻辑"""
    
    @classmethod
    def is_following(cls, follower: User, target_user: User) -> bool:
        """判断 follower 是否已关注 target_user"""
        if follower.id == target_user.id:
            return False
        # ⚠️ 注意：此处假定 UserFollow 模型外键为 user(发起关注者) 和 following(被关注者)
        # 如果你模型命名不同(如 follower, target_user), 请相应替换字段名
        return UserFollow.objects.filter(user=follower, following=target_user).exists()

    @classmethod
    def follow(cls, follower: User, target_user_id: int):
        """执行关注动作"""
        if follower.id == target_user_id:
            raise BusinessException("不能关注自己")
            
        target_user = User.objects.filter(id=target_user_id).first()
        if not target_user:
            raise BusinessException("目标用户不存在")
        
        # 使用 get_or_create 避免重复关注报错
        UserFollow.objects.get_or_create(user=follower, following=target_user)

    @classmethod
    def unfollow(cls, follower: User, target_user_id: int):
        """执行取消关注动作"""
        if follower.id == target_user_id:
            raise BusinessException("不能对自身执行取消关注")
            
        deleted_count, _ = UserFollow.objects.filter(user=follower, following_id=target_user_id).delete()
        if deleted_count == 0:
            raise BusinessException("您尚未关注该用户")