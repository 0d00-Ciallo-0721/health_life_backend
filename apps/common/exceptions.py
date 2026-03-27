from rest_framework.views import exception_handler
from rest_framework.response import Response
# [新增] 引入 DRF 的 APIException 基类
from rest_framework.exceptions import APIException

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

# ==========================================
# [新增] 业务异常基类 (追加到文件最下方)
# ==========================================
class BusinessException(APIException):
    """
    自定义业务逻辑异常
    配合 custom_exception_handler 统一返回格式
    """
    status_code = 400
    default_detail = '业务处理异常'
    default_code = 'business_error'

    def __init__(self, detail=None, status_code=None):
        if detail is not None:
            self.detail = detail
        if status_code is not None:
            self.status_code = status_code