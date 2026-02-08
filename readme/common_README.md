# 🛠 Common Infrastructure (公共基础设施层)

> **目录位置**: `/apps/common/`
> **模块定位**: 本模块是项目的“地基”和“工具箱”。它不处理具体的业务（如吃什么、或是谁登录），而是负责**制定标准**和**封装通用工具**。

## 📖 1. 模块概览

在一个多人协作（特别是前后端分离）的项目中，最大的痛点往往是：

1. **接口格式不统一**：有的接口返回 `{result: ...}`，有的返回 `{data: ...}`。
2. **报错看不懂**：服务器崩了直接吐出一堆 HTML 源码，或者 DRF 默认的英文报错，前端无法解析。
3. **第三方代码耦合**：调用微信 API 的代码散落在各个视图里，难以维护。

`apps/common` 模块通过**AOP (面向切面编程)** 的思想，统一拦截了所有的请求和响应，解决了上述问题。

### 📁 文件清单

| 文件名 | 核心作用 | 技术亮点 |
| --- | --- | --- |
| **`renderers.py`** | **统一响应格式**。拦截所有 HTTP 200/201 响应，包装成标准 JSON。 | ✅ **自动包装** (Auto-Wrapping) |
| **`exceptions.py`** | **全局异常处理**。拦截所有 HTTP 4xx/5xx 错误，转化为标准 JSON。 | ✅ **优雅降级** (Graceful Degradation) |
| **`utils.py`** | **通用工具类**。目前主要封装了微信登录 API 调用。 | ✅ **第三方服务隔离** |
| **`__init__.py`** | 包标识文件。 | (空) |

---

## 🛡 2. API 响应协议防腐层 (The Protocol)

这是本项目对前端工程师最友好的设计。无论后端发生什么（成功、校验失败、服务器爆炸），**前端收到的 JSON 永远保持以下固定结构**。

### 2.1 统一响应结构

所有接口的返回数据均符合以下 TypeScript 接口定义：

```typescript
interface ApiResponse<T> {
  code: number;      // HTTP 状态码 (200, 400, 401, 500 等)
  msg: string;       // 提示信息 ("success", "密码错误", "服务器繁忙")
  data: T | null;    // 具体的业务数据 (对象、数组或 null)
}

```

### 2.2 实现原理 (`renderers.py`)

Django DRF 原生返回的数据可能是列表 `[]` 或字典 `{}`。`CustomRenderer` 类重写了 `render` 方法：

* **工作流**：
1. 视图函数返回数据（例如 `return Response({'name': '牛肉'})`）。
2. `CustomRenderer` 拦截数据。
3. 检查是否已经是标准格式（防止双重包装）。
4. 如果不是，将其塞入 `data` 字段，并补全 `code=200`, `msg='success'`。
5. 最终前端收到：`{ "code": 200, "msg": "success", "data": { "name": "牛肉" } }`。



### 2.3 异常拦截原理 (`exceptions.py`)

Django DRF 原生的报错通常是 `{ "field_name": ["This field is required."] }`。`custom_exception_handler` 函数负责“翻译”这些错误：

* **工作流**：
1. 系统抛出异常（如 `AuthenticationFailed` 或 `ValidationError`）。
2. `custom_exception_handler` 捕获异常。
3. 提取错误详情（支持提取 list 或 dict 中的第一个错误信息）。
4. 构造标准响应：`{ "code": 401, "msg": "身份认证失败", "data": null }`。
5. 前端只需弹窗显示 `msg` 字段即可，无需处理复杂的错误结构。



---

## 🔌 3. 通用工具链 (`utils.py`)

此文件用于存放与具体业务解耦的工具代码，目前核心是 **微信生态对接**。

### 3.1 微信登录服务 (`WeChatService`)

* **背景**：微信小程序登录需要用前端传来的临时 `code` 去换取用户的唯一标识 `openid`。这个过程涉及网络请求，如果不封装，`views.py` 会变得很脏。
* **功能**：
* 自动读取 `settings.WECHAT_APP_ID` 和 `SECRET`。
* 向微信服务器 `https://api.weixin.qq.com/sns/jscode2session` 发起请求。
* **错误处理**：如果微信返回 `errcode` (如 code 无效)，这里会直接抛出 DRF 标准异常，中断登录流程，前端会收到标准的 400 错误。


* **调用示例** (在 `apps/users/views.py` 中)：
```python
try:
    # 一行代码完成复杂的微信交互
    wechat_data = WeChatService.get_openid(code)
except AuthenticationFailed as e:
    return Response(...)

```

### 3.2 食材归一化引擎 (Ingredient Normalization) **(v2.2新增)**

解决了 "用户冰箱存的是**西红柿**，菜谱写的是**番茄**，导致匹配失败" 的痛点。

* **字典库**: 内置 `INGREDIENT_SYNONYMS`，包含常见食材的别名映射。
* **函数**: `normalize_ingredient_name(name)`。
* **逻辑**: 
    * 输入 "洋柿子" -> 输出 "西红柿"
    * 输入 "番茄" -> 输出 "西红柿"
    * 输入 "西红柿" -> 输出 "西红柿"
* **应用场景**: 在 **搜餐 (Search)** 和 **库存匹配** 时双向调用，显著提高了 `match_score` 的准确率。

### 3.3 数据库兼容工具 (`bson.ObjectId`) **(v3.0 新增)**

由于项目使用了 **Django (SQL ID 是整数)** 和 **MongoDB (NoSQL ID 是 ObjectId 字符串)** 的混合架构，在 ID 传递时极易出错。

* **校验器**: 在 Service 层引入 `bson.ObjectId.is_valid()`。
* **场景**: 当 `source_id` 从前端传入时，先校验格式。如果是有效的 ObjectId，查 MongoDB (菜谱)；如果是整数，查 MySQL (自定义)；如果是字符串且非 ObjectId，查 LBS (商家)。这一机制彻底解决了 ID 类型混淆导致的 500 错误。
---

## ⚙️ 4. 配置与启用

这些组件不是写好就能自动运行的，它们是在 `health_life/settings.py` 中被注册激活的：

```python
# health_life/settings.py

REST_FRAMEWORK = {
    # 激活全局异常处理
    'EXCEPTION_HANDLER': 'apps.common.exceptions.custom_exception_handler',
    
    # (可选) 激活统一渲染器
    # 'DEFAULT_RENDERER_CLASSES': (
    #     'apps.common.renderers.CustomRenderer',
    #     ...
    # ),
}

```

> **注意**：在当前代码版本中，为了让开发者更直观地控制视图返回，`DEFAULT_RENDERER_CLASSES` 可能被注释掉了，而在 `views.py` 中手动构建了 Response。但在大型团队开发中，建议开启它以强制规范。

---

## ❓ 常见问题 (FAQ)

**Q1: 为什么有时候我看到的返回没有 data 字段？**

> A: 只有在 `code != 200` (报错) 的情况下，`data` 字段可能为 `null` 或被省略。前端在处理错误时，应优先读取 `msg` 字段进行 Toast 提示。

**Q2: 我想加一个发送短信验证码的功能，代码写哪？**

> A: 请写在 `apps/common/utils.py` 中，或者在 `common` 下新建 `sms.py`。不要写在 `users` 应用里，因为未来可能“商家”也需要收短信，放在 `common` 下可以复用。

**Q3: `WeChatService` 报错 "微信API连接失败" 是怎么回事？**

> A: 这通常是因为你的服务器网络无法访问外网（微信服务器），或者你的 `.env` 文件中 `WECHAT_APP_ID` 配置错误。请检查服务器网络和环境变量。