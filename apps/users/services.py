from apps.common.exceptions import BusinessException
from .models import User, UserFollow


class UserFollowService:
    """处理用户关注相关业务逻辑。"""

    @classmethod
    def is_following(cls, follower: User, target_user: User) -> bool:
        if follower.id == target_user.id:
            return False
        return UserFollow.objects.filter(follower=follower, followed=target_user).exists()

    @classmethod
    def follow(cls, follower: User, target_user_id: int):
        if follower.id == target_user_id:
            raise BusinessException("不能关注自己")

        target_user = User.objects.filter(id=target_user_id).first()
        if not target_user:
            raise BusinessException("目标用户不存在")

        UserFollow.objects.get_or_create(follower=follower, followed=target_user)

    @classmethod
    def unfollow(cls, follower: User, target_user_id: int):
        if follower.id == target_user_id:
            raise BusinessException("不能对自己执行取关")

        deleted_count, _ = UserFollow.objects.filter(
            follower=follower,
            followed_id=target_user_id,
        ).delete()
        if deleted_count == 0:
            raise BusinessException("您尚未关注该用户")
