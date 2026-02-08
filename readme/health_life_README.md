# ⚙️ Health Life Configuration Center (核心配置中心)

> **目录位置**: `/health_life/`
> **模块定位**: 本文件夹是整个后端项目的“大脑”和“神经中枢”。它不包含具体的业务逻辑（如点餐、登录），但决定了项目**如何运行**、**连接哪个数据库**以及**对外暴露哪些路由**。

## 📖 1. 模块概览

此模块不仅仅是存放静态配置的地方，它引入了 **“环境感知 (Environment Awareness)”** 机制。
这意味着代码能够根据运行环境（是开发者的 MacBook，还是没装 MySQL 的演示台式机，或是 Docker 容器）**自动调整**底层基础设施的连接策略，而无需人工修改代码。

### 📁 文件清单

| 文件名 | 核心作用 | 技术亮点 |
| --- | --- | --- |
| **`settings.py`** | **全剧核心**。管理所有数据库连接、缓存策略、安全密钥和第三方 API 配置。 | ✅ **智能环境切换** (Auto-Switch)<br>

<br>✅ **混合存储配置** (MySQL+Mongo+Redis) |
| **`urls.py`** | **路由入口**。定义 API 的顶级路径结构。 | ✅ **Swagger/OpenAPI 集成**<br>

<br>✅ API 版本控制 (`/api/v1/`) |
| **`wsgi.py`** | **WSGI 入口**。生产环境（如 Gunicorn）的启动钩子。 | 标准 WSGI 协议实现 |
| **`__init__.py`** | 包标识文件。 | (空) |

---

## 🧠 2. 核心机制深度解析 (`settings.py`)

这是本项目最值得讲解的技术点之一。传统的 Django 项目往往需要维护 `settings_dev.py` 和 `settings_prod.py`，而本项目通过**动态逻辑**实现了“一套配置走天下”。

### 2.1 智能数据库切换 (Smart Database Switch)

为了解决“演示电脑可能没装 MySQL”的痛点，我们在 `settings.py` 中编写了探测逻辑。

* **工作原理**：
1. 代码首先读取环境变量 `.env` 中的 `FORCE_MYSQL` 字段。
2. **高性能模式**：如果 `FORCE_MYSQL=True`，系统尝试连接 MySQL。这适合开发和生产环境，支持高并发和复杂事务。
3. **便携模式**：如果 `FORCE_MYSQL=False` 或未配置，系统**自动降级**为 `SQLite3`。Django 会在根目录生成一个 `db.sqlite3` 文件。这使得项目可以像“绿色软件”一样，拷贝到任何有 Python 的电脑上直接运行。


* **代码逻辑图解**：
```python
# 伪代码逻辑演示
USE_MYSQL = os.environ.get('FORCE_MYSQL') == 'True'

if USE_MYSQL:
    DATABASES = { 'ENGINE': 'mysql', ... } # 🚀 连接 MySQL
    print("模式: 生产/高性能")
else:
    DATABASES = { 'ENGINE': 'sqlite3', ... } # 🚗 降级 SQLite
    print("模式: 便携/演示")

```



### 2.2 混合存储配置 (Hybrid Persistence)

本项目同时使用了三种数据库，配置中心负责将它们协调工作：

1. **MySQL / SQLite**:
* **配置项**: `DATABASES['default']`
* **用途**: 存储 `User`, `Profile`, `FridgeItem`, `DailyIntake` 等核心事务数据。


2. **MongoDB**:
* **配置项**: `mongoengine.connect()`
* **用途**: 存储 `Recipe` (菜谱) 和 `Restaurant` (商家LBS) 等非结构化数据。
* **容错**: 配置了 `serverSelectionTimeoutMS`，防止 MongoDB 连不上时拖死整个应用启动。


3. **Redis / LocMemCache**:
* **机制**: 同样具备“智能切换”。系统会尝试 `import django_redis`。
* **有 Redis**: 启用 `django_redis.cache.RedisCache`，支持 GeoHash LBS 缓存。
* **无 Redis**: 自动降级为 `LocMemCache` (本地内存)，重启后缓存丢失，但能保证系统不报错。



### 2.3 第三方服务集成

所有敏感 Key 均**不硬编码**在代码中，而是通过 `os.environ.get()` 从 `.env` 文件读取，保障安全性。

* **JWT (SimpleJWT)**: 配置了 Token 有效期（7天）和 刷新期（14天）。
* **高德地图 (AMap)**: `AMAP_WEB_KEY` 用于 LBS 服务。
* **微信小程序**: `WECHAT_APP_ID` 和 `SECRET` 用于 `code2session` 登录。

### 2.4 AI 服务集成 (SiliconFlow) **(v3.1 新增)**

* **配置项**: 从环境变量读取 `SILICONFLOW_API_KEY`。
* **模型选型**: `Qwen/Qwen3-VL-235B-A22B-Thinking` (推理增强版)。
* **依赖**: 升级 `openai` SDK 至 v1.x 版本以支持新的 ChatCompletions 协议。


---


## 🚦 3. 路由架构解析 (`urls.py`)

`urls.py` 是流量的分发中心。本项目采用了 **RESTful 风格** 的路由设计，并集成了自动化文档工具。

### 3.1 路由表结构

```text
/
├── admin/              -> Django 原生后台管理 (上帝模式)
├── api/
│   ├── docs/           -> Swagger UI (交互式接口文档)
│   ├── schema/         -> OpenAPI YAML 元数据
│   └── v1/             -> 业务 API 版本控制入口
│       ├── user/       -> 分发给 apps.users.urls
│       └── diet/       -> 分发给 apps.diet.urls

```

### 3.2 自动化文档 (Swagger)

通过集成 `drf_spectacular`，访问 `/api/docs/` 即可看到自动生成的接口文档。

* **配置**: 在 `settings.py` 的 `SPECTACULAR_SETTINGS` 中定义了文档标题、版本和描述。
* **作用**: 前端开发者无需阅读后端代码，直接在网页上测试接口。

---

## 🛠 4. 环境配置指南 (.env)

要控制本模块的行为，你需要修改根目录下的 `.env` 文件。以下是核心控制参数：

```ini
# --- 核心开关 ---
DEBUG=True                  # 开启调试模式
SECRET_KEY=xxxxxx           # Django 加密密钥

# --- 数据库控制 (最重要) ---
FORCE_MYSQL=True            # 设置为 True 强制用 MySQL；设置为 False 自动切 SQLite
DB_PASSWORD=your_pwd        # MySQL 密码 (仅在 FORCE_MYSQL=True 时生效)

# --- 缓存控制 ---
# 如果填了 URL 且安装了 redis 库，自动开启 Redis；否则用内存缓存
REDIS_URL=redis://127.0.0.1:6379/1 

# --- 第三方 Key ---
AMAP_WEB_KEY=xxxxxx         # 高德地图 Web 服务 Key

```

---

## ❓ 常见问题 (FAQ)

**Q1: 为什么启动时提示 "MongoDB 连接失败"？**

> A: `settings.py` 中有容错处理。如果本地没有 MongoDB，只会打印一条警告，项目依然可以启动。但涉及菜谱搜索和 LBS 的功能会报错。建议安装 MongoDB 或在 `.env` 配置云数据库地址。

**Q2: 如何修改 API 的前缀，比如改成 `/api/v2/`？**

> A: 直接修改 `health_life/urls.py` 中的 `path('api/v1/', ...)` 即可。这不会影响业务逻辑，因为所有 App 的路由都是通过 `include()` 挂载的。

**Q3: 为什么我在新电脑上运行没有报错，但是数据都没了？**

> A: 因为新电脑上可能未配置 MySQL，系统自动切换到了 `SQLite` 模式。SQLite 是一个文件数据库，默认是空的。你需要运行 `python manage.py loaddata data_backup.json` 来导入数据。