import os
from pathlib import Path
from datetime import timedelta
import mongoengine
from dotenv import load_dotenv # 引入读取环境变量的库

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ✅ 1. 加载 .env 文件
load_dotenv(BASE_DIR / '.env')

# ✅ 2. 读取密钥 (优先从环境变量读，读不到用默认值)
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-fallback-key')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
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
    
    # Local apps
    'apps.users',
    'apps.diet',
    'apps.common',
    # 管理后台模块
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
# 逻辑：检查环境变量 FORCE_MYSQL。
# 如果为 True，尝试用 MySQL；否则默认用 SQLite (便携，无需安装MySQL)。

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
        'DIRS': [],
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
        serverSelectionTimeoutMS=2000 # 超时设置短一点，避免连不上卡死
    )
    print(f"✅ [Settings] MongoDB 连接尝试: {MONGO_HOST}")
except Exception as e:
    print(f"⚠️ [Settings] MongoDB 连接失败 (LBS功能可能受限): {e}")

# --- 🚀 5. 智能缓存配置 (Smart Cache Switch) ---
# 逻辑：如果 .env 里配了 Redis 且装了库，就用 Redis；否则降级为内存缓存。

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
    
    # ✅ [修改] 激活全局异常处理
    'EXCEPTION_HANDLER': 'apps.common.exceptions.custom_exception_handler',
    
    # ✅ [新增/取消注释] 激活统一响应渲染器
    # 这会将 ProfileUpdateView 等原生接口的返回自动包装为 {code: 200, data: ...}
    'DEFAULT_RENDERER_CLASSES': (
        'apps.common.renderers.CustomRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer', # 保留浏览器调试界面
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
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- 高德地图 ---
AMAP_WEB_KEY = os.environ.get('AMAP_WEB_KEY', '')


# --- AI 服务配置 (SiliconFlow) ---
# 请将 'sk-...' 替换为你真实的 Key，或者在系统环境变量中设置 SILICONFLOW_API_KEY
SILICONFLOW_API_KEY = os.environ.get('SILICONFLOW_API_KEY', 'sk-pqovdrehlnwxfmhgmhgifwaaxreddhemoaxmecxbhexgtbuf')
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
# 视觉模型：Qwen2-VL 或 Qwen3-VL (根据你的账号权限调整)
SILICONFLOW_MODEL = "Qwen/Qwen2.5-VL-72B-Instruct" 
# 注意: Qwen3-VL-Thinking 可能是预览版，如果报错请改回 Qwen2.5-VL-72B-Instruct 或 Qwen2-VL-72B-Instruct



# --- 🚀 CORS 跨域设置 (修复 Network Error) ---
# 允许所有域名访问 (开发环境推荐)
CORS_ALLOW_ALL_ORIGINS = True 

# 允许携带认证信息 (如 Cookies/Session，虽然我们用 JWT 但加上这个更保险)
CORS_ALLOW_CREDENTIALS = True

# 允许的请求头 (通常保持默认即可，但为了保险可以显式加上)
from corsheaders.defaults import default_headers
CORS_ALLOW_HEADERS = list(default_headers) + [
    'authorization', # 允许前端发送 Authorization: Bearer xxx
    'x-requested-with',
]