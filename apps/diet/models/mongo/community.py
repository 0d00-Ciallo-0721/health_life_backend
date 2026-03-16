# [新增] 整个文件: apps/diet/models/mongo/community.py
import datetime
from mongoengine import Document, StringField, IntField, ListField, DateTimeField, ReferenceField, CASCADE, DictField, BooleanField

class CommunityFeed(Document):
    """
    社区动态流 (MongoDB)
    """
    meta = {
        'collection': 'community_feed',
        'indexes': ['-created_at', 'feed_type']
    }
    user_id = IntField(required=True) # 关联 MySQL 中的 User ID
    content = StringField(required=True)
    images = ListField(StringField()) # 图片 URL 列表
    feed_type = StringField(default='post', choices=['post', 'recipe', 'restaurant', 'meal', 'sport']) # 动态类型
    target_id = StringField() # 如果是分享菜谱/商家，记录对应的 ID
    
    # 运动记录专属字段 (非结构化嵌套)
    sport_info = DictField() 
    
    likes_count = IntField(default=0)
    comments_count = IntField(default=0)
    created_at = DateTimeField(default=datetime.datetime.utcnow)

    # 🚀 [新增] 后台治理与管控字段
    is_hidden = BooleanField(default=False) # 是否被后台屏蔽隐藏
    is_pinned = BooleanField(default=False) # 是否在社区置顶

class Comment(Document):
    """
    动态评论 (MongoDB)
    """
    meta = {
        'collection': 'community_comment',
        'indexes': ['feed_id', '-created_at']
    }
    feed_id = ReferenceField(CommunityFeed, reverse_delete_rule=CASCADE) # 级联删除
    user_id = IntField(required=True)
    content = StringField(required=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)