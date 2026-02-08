# 👤 User Domain (用户与认证领域)

> **目录位置**: `/apps/users/`
> **模块定位**: 本模块负责处理“我是谁”的问题。它包含用户模型定义、微信登录逻辑、JWT 令牌颁发以及用户的身体档案（Profile）定义。

## 📖 1. 模块概览

在健康生活小程序中，用户体系有两个特殊性：

1. **无感登录**：用户不需要输入账号密码，点击“微信一键登录”即可进入。
2. **身体档案强绑定**：用户的 BMR（基础代谢率）是核心业务数据，它直接决定了系统的推荐逻辑。因此，我们在设计用户模型时，将“账号信息”与“身体档案”分离，但保持强关联。

### 📁 文件清单

| 文件名 | 核心作用 | 技术亮点 |
| --- | --- | --- |
| **`models.py`** | **数据模型定义**。定义 `User` (账号) 和 `Profile` (身体档案)。 | ✅ **充血模型** (Rich Model)<br>

<br>✅ **BMR 自动计算逻辑** |
| **`views.py`** | **认证接口**。核心是微信登录接口，实现“注册/登录”二合一。 | ✅ **原子化注册** (Atomic Registration) |
| **`utils.py`** | **微信工具**。封装 `code2session` API 调用（与 `common` 模块配合）。 | ✅ **OpenID 隐蔽处理** |
| **`serializers.py`** | **数据序列化**。负责用户信息的输入输出格式化。 | (标准 DRF 序列化) |

---

## 🧬 2. 核心模型解析 (`models.py`)

### 2.1 User (账号本体)

继承自 Django 的 `AbstractUser`。

* **核心字段**:
* `openid`: (String, Unique) 微信用户的唯一标识，也是登录的凭证。
* `username`: 自动生成（如 `wx_123456`），用户不可见。
* `avatar`, `nickname`: 冗余存储微信头像昵称，用于前端展示。



### 2.2 Profile (身体档案)
这是一个典型的 **One-to-One** 扩展模型。它存储了计算代谢率所需的所有生理参数。

* **核心字段**:
    * `height` (cm), `weight` (kg), `age`, `gender` (1男/2女)。
    * `activity_level`: 活动系数 (1.2 ~ 1.9)。
    * **`daily_kcal_limit`**: **核心衍生字段**。系统根据上述参数自动计算出的每日推荐摄入量。
    * **`diet_tags` (JSON)**: 存储饮食偏好标签，如 `["低碳", "高蛋白", "微辣"]`。
    * **`allergens` (JSON)**: **(v1.1新增)** 存储过敏源列表，如 `["花生", "海鲜"]`。在推荐算法中用于强制过滤。
    * **`goal_type`**: **(v2.1新增)** 健康目标。枚举值：`lose` (减脂), `maintain` (保持), `gain` (增肌)。
        * *逻辑联动*: 修改此字段会直接改变 `daily_kcal_limit` 计算公式。

* **⚡️ 核心业务逻辑 (BMR Calculation)**:
    我们在 `Profile` 模型中实现了 `calculate_and_save_daily_limit()` 方法。每当用户的身高体重发生变化时，系统会自动调用此方法更新摄入目标。

### 2.3 目标驱动代谢 (Goal Driven BMR) **(v2.2新增)**

`Profile` 模型不再是静态的数据表，而是一个动态的 **BMR 计算器**。

* **触发机制**: 每当更新 `weight`、`age` 或 `goal_type` 时，自动触发重算。
* **公式矩阵 (Mifflin-St Jeor)**:
    * `BMR` = (10 × weight) + (6.25 × height) - (5 × age) + (5 or -161)
* **TDEE 修正系数**:
    * **`lose` (减脂)**: `daily_limit = BMR * activity * 0.85` (制造热量缺口)
    * **`gain` (增肌)**: `daily_limit = BMR * activity * 1.10` (制造热量盈余)
    * **`maintain` (保持)**: `daily_limit = BMR * activity * 1.0`

### 2.4 序列化增强 (`serializers.py`)

* **扁平化输出**: `ProfileSerializer` 通过 `source='user.nickname'` 将 User 表的昵称无缝合并到 Profile 接口中，前端无需请求两次。
* **只读保护**: 自动计算字段 (`bmr`, `daily_kcal_limit`) 设为 `read_only`，防止前端误传脏数据覆盖算法结果。

### 2.5 用户元数据扩展 (`UserMetaView`) **(v3.1 增强)**

为了支撑“个人中心”页面的丰富展示，我们扩展了元数据接口：

* **坚持天数 (`days_joined`)**: 动态计算 `Today - DateJoined`。
* **目标展示**: 将数据库枚举值 (`lose`) 自动转译为中文文案 (`减脂`)，减少前端硬编码。



## 🔐 3. 微信静默登录流程 (`views.py`)

本模块的 `WeChatLoginView` 实现了复杂的 OAuth 2.0 简化流程。

### 3.1 流程图解

1. **前端**: 调用 `wx.login()` 拿到临时票据 `code`，发送给后端 `/api/v1/user/login/`。
2. **后端 (Service)**: 调用微信服务器接口 `jscode2session`，用 `code` 换取 `openid`。
3. **后端 (View)**:
* **查询**: 数据库里有没有这个 `openid`？
* **有 (Login)**: 直接生成 JWT Token 返回。
* **无 (Register)**: 自动创建一个新 `User`，并初始化一个空的 `Profile`，然后生成 JWT Token 返回。


## 👤 4. 用户元数据服务 (`UserMetaView`)

专为“我的”页面设计，提供非档案类的元数据。

* **接口**: `GET /api/v1/user/meta/`
* **功能**:
    * 返回头像 (`avatar`) 和昵称 (`nickname`)。
    * **动态计算**用户坚持天数 (`days_joined`)。
    * 返回当前健康目标展示文案。

### 3.2 关键代码逻辑

```python
# 伪代码演示
@transaction.atomic
def post(self, request):
    code = request.data.get('code')
    # 1. 换取 openid (调用 apps.users.utils.WeChatService)
    wechat_data = WeChatService.get_openid(code)
    openid = wechat_data['openid']
    
    # 2. 查找或创建用户
    user, created = User.objects.get_or_create(openid=openid, defaults={...})
    
    # 3. 如果是新用户，初始化档案
    if created:
        Profile.objects.create(user=user)
        
    # 4. 颁发 JWT
    refresh = RefreshToken.for_user(user)
    return Response({
        'token': str(refresh.access_token),
        'is_new_user': created  # 告诉前端是否需要跳转去填资料
    })

```

---

## 🛠 4. 工具与依赖

### 4.1 WeChatService (`utils.py`)

这是连接微信生态的桥梁。

* **依赖**: `requests` 库。
* **配置**: 读取 `.env` 中的 `WECHAT_APP_ID` 和 `WECHAT_APP_SECRET`。
* **安全**: `session_key` 属于敏感数据，仅在需要解密手机号时暂存 Redis，**绝不落库**。

### 4.2 JWT 配置

依赖 `djangorestframework-simplejwt` 库。
在 `settings.py` 中配置了：

* `ACCESS_TOKEN_LIFETIME`: 7天 (为了提升小程序体验，减少重新登录次数)。
* `AUTH_HEADER_TYPES`: `Bearer`。


## 📸 5. 多媒体支持

### 5.1 头像上传 (`ProfileAvatarView`)

* **接口**: `POST /api/v1/diet/profile/avatar/`
* **实现**: 使用 Django `MultiPartParser` 处理文件流。
* **存储**: 默认存储在本地 `media/avatars/YYYY/MM/` 目录。
* **响应**: 返回完整的访问 URL，方便前端直接渲染。




## ❓ 常见问题 (FAQ)

**Q1: 为什么修改了体重，推荐摄入量没有变？**

> A: 请确认你是通过 API (`ProfileUpdateView`) 修改的。我们的 BMR 重算逻辑绑定在 Model 的 `save()` 或 View 的 `perform_update()` 中。如果你直接改数据库，需要手动触发重算逻辑。

**Q2: 为什么登录接口报错 "40101 invalid code"？**

> A: 微信的 `code` 是一次性的，且有效期只有 5 分钟。前端每次调用登录接口前，必须重新执行 `wx.login()` 获取最新的 code。

**Q3: 如何获取用户的手机号？**

> A: 目前版本仅实现了静默登录（获取 OpenID）。获取手机号需要前端调用 `getPhoneNumber` 按钮，后端需要用 `session_key` 进行解密（这部分逻辑预留在了 `utils.py` 中，暂未启用）。