import logging
import os
from pathlib import Path
from datetime import timedelta
import mongoengine
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ✅ 1. 加载 .env 文件
load_dotenv(BASE_DIR / '.env')

logger = logging.getLogger(__name__)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=None):
    value = os.environ.get(name)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(',') if item.strip()]

# ✅ 2. 读取密钥与安全开关
DEBUG = env_bool('DEBUG', False)
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-change-me'
    else:
        raise RuntimeError('SECRET_KEY must be configured when DEBUG is disabled')
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', ['127.0.0.1', 'localhost'])
PUBLIC_TUNNEL_HOSTS = env_list('PUBLIC_TUNNEL_HOSTS', ['47.95.215.220', '47.93.45.198'])
ALLOWED_HOSTS = list(dict.fromkeys(ALLOWED_HOSTS + PUBLIC_TUNNEL_HOSTS))
ALLOW_TEST_WECHAT_LOGIN = env_bool('ALLOW_TEST_WECHAT_LOGIN', DEBUG)
ENABLE_LBS_MOCK_FALLBACK = env_bool('ENABLE_LBS_MOCK_FALLBACK', DEBUG)
ENABLE_AI_SERVICES = env_bool('ENABLE_AI_SERVICES', True)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'corsheaders',
    'drf_spectacular', 
    'rest_framework_simplejwt.token_blacklist',  # [新增] JWT黑名单应用，用于退出登录
    
    # Local apps
    'apps.users',
    'apps.diet',
    'apps.common',
    'apps.admin_management', 
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'apps.admin_management.middleware.AdminApiCSRFFreeMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.admin_management.middleware.AuditLogMiddleware',
]

# --- 🚀 3. 智能数据库配置 (Smart Database Switch) ---
USE_MYSQL = env_bool('FORCE_MYSQL', False)

if USE_MYSQL:
    logger.info("[Settings] Database mode: MySQL")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'health_life_db'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
            }
        }
    }
else:
    logger.info("[Settings] Database mode: SQLite3")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # 增加全局模板目录扫描
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# --- 4. MongoDB 配置 (容错处理) ---
MONGO_HOST = os.environ.get('MONGO_HOST', '127.0.0.1')
try:
    mongoengine.connect(
        db='health_life_mongo',
        host=MONGO_HOST,
        port=27017,
        alias='default',
        serverSelectionTimeoutMS=2000 
    )
    logger.info("[Settings] MongoDB host: %s", MONGO_HOST)
except Exception as e:
    logger.warning("[Settings] MongoDB connection failed: %s", e)

# --- 🚀 5. 智能缓存配置 (Smart Cache Switch) ---
REDIS_URL = os.environ.get('REDIS_URL', '')
HAS_REDIS_LIB = False
try:
    import django_redis
    HAS_REDIS_LIB = True
except ImportError:
    pass

if HAS_REDIS_LIB and REDIS_URL:
    logger.info("[Settings] Cache backend: Redis")
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            }
        }
    }
else:
    logger.info("[Settings] Cache backend: LocMemCache")
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# --- 用户模型 ---
AUTH_USER_MODEL = 'users.User'

# --- DRF & JWT ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'apps.common.exceptions.custom_exception_handler',
    'DEFAULT_RENDERER_CLASSES': (
        'apps.common.renderers.CustomRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer', 
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

SPECTACULAR_SETTINGS = {
    'TITLE': '健康生活小程序 API 文档',
    'DESCRIPTION': '包含大转盘、外卖跳转协议、身体档案管理、冰箱库存等核心接口',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True, 
}

# --- 微信小程序 ---
WECHAT_APP_ID = os.environ.get('WECHAT_APP_ID', '')
WECHAT_APP_SECRET = os.environ.get('WECHAT_APP_SECRET', '')

ROOT_URLCONF = 'health_life.urls'
WSGI_APPLICATION = 'health_life.wsgi.application'
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- 🎯 6. 静态文件与媒体文件配置 (已修复) ---
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # 生产环境收集静态文件的目录

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'         # 处理用户头像、帖子图片等物理存储位置

# --- 🛡️ 7. CSRF 与穿透安全设置 (已修复) ---
# 必须配置，否则通过 SSH 公网隧道 (8081端口) 访问 Admin 后台会报 403 CSRF 错误
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
])
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(
    CSRF_TRUSTED_ORIGINS + [f'http://{host}:8081' for host in PUBLIC_TUNNEL_HOSTS]
))

# --- 高德地图 ---
AMAP_WEB_KEY = os.environ.get('AMAP_WEB_KEY', '')

# AI Dynamic Routing Configuration
# 根据任务类型 (vision/text) 路由到不同的模型供应商
# -----------------------------------------------------------------------------
AI_CONFIG = {
    'vision': {
        'provider': os.environ.get('AI_VISION_PROVIDER', 'doubao-seed-2-0-pro-260215'),
        'base_url': os.environ.get('AI_VISION_BASE_URL', 'https://ark.cn-beijing.volces.com/api/v3'),
        'api_key': os.environ.get('AI_VISION_API_KEY', ''),
        'api_keys': env_list('AI_VISION_API_KEYS', [os.environ.get('AI_VISION_API_KEY', '')]),
        'model': os.environ.get('AI_VISION_MODEL', 'doubao-seed-2-0-pro-260215'),
    },
    'text': {
        'provider': os.environ.get('AI_TEXT_PROVIDER', 'doubao-seed-2-0-pro-260215'),
        'base_url': os.environ.get('AI_TEXT_BASE_URL', 'https://ark.cn-beijing.volces.com/api/v3'),
        'api_key': os.environ.get('AI_TEXT_API_KEY', ''),
        'api_keys': env_list('AI_TEXT_API_KEYS', [os.environ.get('AI_TEXT_API_KEY', '')]),
        'model': os.environ.get('AI_TEXT_MODEL', 'doubao-seed-2-0-pro-260215'),
    },
    # 降级供应商：当主供应商全部密钥失败时自动切换 (Kimi / Moonshot AI)
    'fallback': {
        'provider': 'kimi',
        'base_url': os.environ.get('AI_FALLBACK_BASE_URL', 'https://api.moonshot.cn/v1'),
        'api_keys': env_list('AI_FALLBACK_API_KEYS', []),
        'model': os.environ.get('AI_FALLBACK_MODEL', 'kimi-k2.6'),
    },
}

# --- 🚀 CORS 跨域设置 ---
CORS_ALLOW_ALL_ORIGINS = env_bool('CORS_ALLOW_ALL_ORIGINS', False)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS', [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
])
CORS_ALLOWED_ORIGINS = list(dict.fromkeys(
    CORS_ALLOWED_ORIGINS + [f'http://{host}:8081' for host in PUBLIC_TUNNEL_HOSTS]
))

from corsheaders.defaults import default_headers
CORS_ALLOW_HEADERS = list(default_headers) + [
    'authorization', 
    'x-requested-with',
]
