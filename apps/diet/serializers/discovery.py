from rest_framework import serializers

class RecipeSimpleSerializer(serializers.Serializer):
    """用于列表展示的简略信息"""
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    image = serializers.CharField(source='image_url', default="")
    calories = serializers.IntegerField(default=350)
    cooking_time = serializers.IntegerField(default=15)
    match_score = serializers.IntegerField(required=False)
    match_reason = serializers.CharField(required=False)
    tags = serializers.ListField(child=serializers.CharField(), source='keywords', required=False)

class RestaurantSimpleSerializer(serializers.Serializer):
    """用于列表展示的餐厅信息"""
    id = serializers.CharField(source='amap_id')
    name = serializers.CharField()
    address = serializers.CharField()
    rating = serializers.FloatField()
    image = serializers.SerializerMethodField()
    distance = serializers.IntegerField(required=False, default=0)
    
    def get_image(self, obj):
        # 兼容 obj 可能是 dict 或 Document 对象
        if isinstance(obj, dict):
            photos = obj.get('photos', [])
        else:
            photos = getattr(obj, 'photos', [])
        return photos[0] if photos else ""