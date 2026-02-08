import json
from django.utils.deprecation import MiddlewareMixin
from apps.admin_management.models.audit import AuditLog

class AuditLogMiddleware(MiddlewareMixin):
    """
    审计日志中间件：自动记录后台所有的非GET请求
    """
    def process_response(self, request, response):
        # 1. 仅拦截 /api/admin/ 开头的请求
        if not request.path.startswith('/api/admin/'):
            return response
            
        # 2. 忽略读操作 (GET/HEAD/OPTIONS)
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return response

        # 3. 获取用户信息 (如果没有登录则是 Anonymous)
        user = request.user if request.user.is_authenticated else None
        
        # 4. 解析请求体 (尝试获取参数快照)
        req_body = {}
        try:
            # 注意：如果 View 已经读取过 body，这里可能需要特殊处理，但 DRF 通常没问题
            if request.body:
                # 简单判断是否是 JSON
                if request.content_type and 'application/json' in request.content_type:
                    req_body = json.loads(request.body.decode('utf-8'))
                else:
                    req_body = {"msg": "非JSON数据，未记录"}
        except Exception:
            req_body = {"msg": "解析失败"}
            
        # 🛡️ 敏感字段脱敏
        if isinstance(req_body, dict):
            if 'password' in req_body:
                req_body['password'] = '******'
            if 'token' in req_body:
                req_body['token'] = '******'

        # 5. 获取 IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        # 6. 提取模块名 (简单的 URL 拆分，如 /api/admin/v1/business/users/ -> users)
        try:
            # 去掉两头斜杠，分割
            parts = request.path.strip('/').split('/')
            # 通常倒数第二段是资源名，如 business/users 中的 users
            module = parts[-2] if len(parts) >= 2 else 'unknown'
        except:
            module = 'unknown'

        # 7. 异步入库 (同步写入数据库)
        try:
            AuditLog.objects.create(
                operator=user,
                operator_name=user.username if user else 'Anonymous',
                method=request.method,
                path=request.path,
                module=module,
                ip_address=ip,
                body=req_body,
                response_code=response.status_code
            )
        except Exception as e:
            # 日志记录失败不应影响主业务
            print(f"⚠️ [Audit] 日志记录失败: {e}")

        return response