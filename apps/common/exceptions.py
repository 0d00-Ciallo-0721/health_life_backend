from rest_framework.views import exception_handler
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    """
    自定义异常处理
    """
    # 先调用 DRF 原生的处理逻辑
    response = exception_handler(exc, context)

    if response is not None:
        msg = "Error"
        if isinstance(response.data, dict):
            msg = response.data.get('detail') or response.data.get('msg') or str(response.data)
        elif isinstance(response.data, list):
            msg = str(response.data[0])
        else:
            msg = str(response.data)

        # ✅ [修复核心] 显式传递 status 参数
        # 之前漏了 status=response.status_code，导致默认返回 200
        return Response({
            'code': response.status_code,
            'msg': msg,
            'data': None
        }, status=response.status_code)
    
    return None