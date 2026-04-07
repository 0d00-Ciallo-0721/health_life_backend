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
    
    # [核验修改] 允许 sport 类型
    feed_type = StringField(default='post', choices=['post', 'recipe', 'restaurant', 'meal', 'sport']) 
    target_id = StringField() 
    
    # [核验修改] 运动记录专属字段 (非结构化嵌套)
    sport_info = DictField() 
    
    likes_count = IntField(default=0)
    comments_count = IntField(default=0)
    created_at = DateTimeField(default=datetime.datetime.utcnow)

    is_hidden = BooleanField(default=False)
    is_pinned = BooleanField(default=False)

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