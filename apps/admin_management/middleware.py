import json
import logging
import sys
import threading
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from apps.admin_management.models.audit import AuditLog

logger = logging.getLogger(__name__)

def save_audit_log_async(user_id, username, method, path, module, ip, req_body, status_code):
    """
    [异步工作线程] 实际执行日志持久化操作
    通过传递基础类型参数(user_id)而非ORM对象，避免跨线程的数据库连接失效问题。
    """
    try:
        AuditLog.objects.create(
            operator_id=user_id,  # 🚀 使用 _id 赋值，避免重新查询 User 对象
            operator_name=username,
            method=method,
            path=path,
            module=module,
            ip_address=ip,
            body=req_body,
            response_code=status_code
        )
    except Exception as e:
        # 日志记录失败不应影响主业务，输出到控制台或标准日志收集器
        logger.warning("[Audit] async log write failed: %s", e)


class AuditLogMiddleware(MiddlewareMixin):
    """
    审计日志中间件：自动记录后台所有的非GET请求 (已改造为轻量级异步写入)
    """
    def process_response(self, request, response):
        # 1. 仅拦截 /api/admin/ 开头的请求
        if not request.path.startswith('/api/admin/'):
            return response
            
        # 2. 忽略读操作 (GET/HEAD/OPTIONS)
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return response

        # 3. 提取用户信息基础类型 (极其关键：不能把 request.user 传给子线程)
        user = request.user if request.user.is_authenticated else None
        user_id = user.id if user else None
        username = user.username if user else 'Anonymous'
        
        # 4. 解析请求体并脱敏
        req_body = {}
        try:
            if request.body and request.content_type and 'application/json' in request.content_type:
                req_body = json.loads(request.body.decode('utf-8'))
        except Exception:
            req_body = {"msg": "非JSON数据或解析失败"}
            
        # 🛡️ 敏感字段脱敏
        if isinstance(req_body, dict):
            if 'password' in req_body:
                req_body['password'] = '******'
            if 'token' in req_body:
                req_body['token'] = '******'

        # 5. 获取 IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

        # 6. 提取模块名
        try:
            parts = request.path.strip('/').split('/')
            module = parts[-2] if len(parts) >= 2 else 'unknown'
        except:
            module = 'unknown'

        audit_args = (user_id, username, request.method, request.path, module, ip, req_body, response.status_code)
        is_sqlite = settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3'
        is_test_run = 'test' in sys.argv
        if is_sqlite or is_test_run:
            save_audit_log_async(*audit_args)
        else:
            thread = threading.Thread(target=save_audit_log_async, args=audit_args)
            thread.daemon = True
            thread.start()

        return response


class AdminApiCSRFFreeMiddleware(MiddlewareMixin):
    """
    后台管理接口使用 JWT Bearer Token，不依赖 Cookie Session。
    仅对 /api/admin/ 放宽 CSRF 检查，方便独立 HTML 后台跨机器访问。
    """

    def process_request(self, request):
        if request.path.startswith('/api/admin/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
