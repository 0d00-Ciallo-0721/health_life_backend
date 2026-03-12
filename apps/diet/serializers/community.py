from rest_framework import serializers

class FeedCreateSerializer(serializers.Serializer):
    """社区发帖入参校验"""
    content = serializers.CharField(max_length=1000, error_messages={"blank": "内容不能为空"})
    images = serializers.ListField(
        child=serializers.URLField(), required=False, max_length=9,
        error_messages={"max_length": "最多只能上传9张图片"}
    )
    type = serializers.ChoiceField(choices=['post', 'recipe', 'restaurant'], default='post')
    target_id = serializers.CharField(max_length=64, required=False, allow_blank=True)