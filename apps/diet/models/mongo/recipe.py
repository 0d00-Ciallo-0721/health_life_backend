from mongoengine import Document, StringField, ListField, IntField, DictField, DateTimeField
from datetime import datetime

class Recipe(Document):
    """菜谱集合 (MongoDB)"""
    name = StringField(required=True, max_length=128)
    dish = StringField()
    description = StringField()
    recipeIngredient = ListField(StringField())
    ingredients_search = ListField(StringField())
    recipeInstructions = ListField(StringField())
    keywords = ListField(StringField())
    image_url = StringField(default="") 
    
    # 补充字段
    calories = IntField(default=350)
    cooking_time = IntField(default=15)
    difficulty = StringField(default="简单")
    nutrition = DictField(default=lambda: {"carb": 0, "protein": 0, "fat": 0})
    
    # 🚀 [新增] 审核相关字段 (务必添加)
    # 0=待审核, 1=通过, 2=拒绝
    status = IntField(default=0, verbose_name="审核状态") 
    created_at = DateTimeField(default=datetime.now)

    meta = {'collection': 'recipes'}