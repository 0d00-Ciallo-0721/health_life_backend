from mongoengine import Document, StringField, FloatField, ListField, PointField, DateTimeField, DictField
import datetime

class Restaurant(Document):
    """周边餐饮缓存 (MongoDB)"""
    amap_id = StringField(unique=True)
    name = StringField(required=True)
    # GeoJSON 格式: [lng, lat]
    location = PointField() 
    type = StringField()
    address = StringField()
    rating = FloatField(default=0.0)
    cost = FloatField(default=0.0)
    photos = ListField(StringField())
    
    # [新增] 菜单字段: [{"name": "..", "price": 20, "image": ".."}]
    menu = ListField(DictField()) 
    
    cached_at = DateTimeField(default=datetime.datetime.now)
    
    meta = {
        'collection': 'restaurant_cache',
        'indexes': [
            'location',     # 地理位置索引
            'amap_id'
        ]
    }