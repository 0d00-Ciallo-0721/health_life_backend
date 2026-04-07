import os
from pathlib import Path
from datetime import timedelta
import mongoengine
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ✅ 1. 加载 .env 文件
load_dotenv(BASE_DIR / '.env')

# ✅ 2. 读取密钥 (优先从环境变量读，读不到用默认值)
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-fallback-key')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
# 开发与穿透调试期允许所有主机，生产环境建议在 .env 中配置具体域名
ALLOWED_HOSTS = ['*']

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
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.admin_management.middleware.AuditLogMiddleware',
]

# --- 🚀 3. 智能数据库配置 (Smart Database Switch) ---
USE_MYSQL = os.environ.get('FORCE_MYSQL', 'False') == 'True'

if USE_MYSQL:
    print("🚀 [Settings] 模式: MySQL (生产/本地高性能)")
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
    print("🚗 [Settings] 模式: SQLite3 (便携/服务器零依赖)")
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
    print(f"✅ [Settings] MongoDB 连接尝试: {MONGO_HOST}")
except Exception as e:
    print(f"⚠️ [Settings] MongoDB 连接失败 (LBS功能可能受限): {e}")

# --- 🚀 5. 智能缓存配置 (Smart Cache Switch) ---
REDIS_URL = os.environ.get('REDIS_URL', '')
HAS_REDIS_LIB = False
try:
    import django_redis
    HAS_REDIS_LIB = True
except ImportError:
    pass

if HAS_REDIS_LIB and REDIS_URL:
    print("🚀 [Settings] 缓存: Redis")
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
    print("🚗 [Settings] 缓存: 本地内存 (LocMemCache)")
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
CSRF_TRUSTED_ORIGINS = [
    'http://47.93.45.198:8081',
    'https://47.93.45.198:8081',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]

# --- 高德地图 ---
AMAP_WEB_KEY = os.environ.get('AMAP_WEB_KEY', '')

# --- AI 服务配置 (SiliconFlow) ---
SILICONFLOW_API_KEY = os.environ.get('SILICONFLOW_API_KEY', 'sk-pqovdrehlnwxfmhgmhgifwaaxreddhemoaxmecxbhexgtbuf')
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
SILICONFLOW_MODEL = "Qwen/Qwen2.5-VL-72B-Instruct" 

# --- 🚀 CORS 跨域设置 ---
CORS_ALLOW_ALL_ORIGINS = True 
CORS_ALLOW_CREDENTIALS = True

from corsheaders.defaults import default_headers
CORS_ALLOW_HEADERS = list(default_headers) + [
    'authorization', 
    'x-requested-with',
]