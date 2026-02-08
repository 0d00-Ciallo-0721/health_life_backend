from rest_framework.renderers import JSONRenderer

class CustomRenderer(JSONRenderer):
    """
    自定义渲染器：将所有 API 的返回数据统一包装为标准格式
    {
        "code": 200,
        "msg": "success",
        "data": { ... }
    }
    """
    def render(self, data, accepted_media_type=None, renderer_context=None):
        # 默认标准格式
        response_data = {
            'code': 200,
            'msg': 'success',
            'data': data
        }

        # 获取响应对象，判断状态码
        if renderer_context:
            response = renderer_context.get('response')
            if response:
                response_data['code'] = response.status_code
                # 如果视图已经手动返回了 code (比如我们在 views.py 里手写的那些)，就不再包装，防止嵌套
                if isinstance(data, dict) and 'code' in data:
                    return super().render(data, accepted_media_type, renderer_context)
                
                # 如果是异常报错 (由 exception_handler 处理过的)
                if response.status_code >= 400:
                    response_data['msg'] = data.get('detail') or data.get('msg') or 'error'
                    response_data['data'] = None

        return super().render(response_data, accepted_media_type, renderer_context)