# 📘 健康生活小程序 - 前端深度对接文档 (V3.1 重构版)

**版本**: v3.1.0 (Refactored DDD)
**基准 URL**: `http://127.0.0.1:8000/api/v1`
**鉴权方式**: Header 中携带 `Authorization: Bearer <access_token>` (登录接口除外)

## 📡 1. 通用响应结构

所有接口（除非特殊说明）均返回以下标准 JSON 结构：

```json
{
  "code": 200,      // 200=成功, 400=参数错误, 401=未登录, 500=服务端异常
  "msg": "success", // 提示信息 (可直接用于 Toast)
  "data": { ... }   // 业务数据
}

```

---

## 👤 2. 用户与档案 (User Domain)

### 2.1 微信登录

* **接口**: `POST /user/login/`
* **权限**: 公开
* **描述**: 自动注册或登录。开发环境支持 `TEST_` 开头的 code 模拟登录。

**请求参数**:

```json
{
  "code": "TEST_CODE_V3_AUTO" // 微信 login 获取的 code
}

```

**响应示例**:

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR...", // JWT Token，后续请求必带
    "is_new_user": false
  }
}

```

### 2.2 更新身体档案

* **接口**: `PATCH /diet/profile/`
* **描述**: 更新身体数据，后端会自动重算 `bmr` 和 `daily_kcal_limit`。

**请求参数** (按需传字段):

```json
{
  "nickname": "减肥中的小明",
  "gender": 1,            // 1=男, 2=女
  "height": 175.5,        // cm
  "weight": 70.0,         // kg
  "target_weight": 65.0,  // kg (目标体重)
  "age": 25,
  "activity_level": 1.3,  // 1.2=久坐, 1.375=轻度运动, 1.55=中度...
  "goal_type": "lose",    // lose=减脂, maintain=保持, gain=增肌
  "diet_tags": ["低碳", "高蛋白"],
  "allergens": ["芒果", "花生"]
}

```

**响应示例**:

```json
{
  "code": 200,
  "data": {
    "nickname": "减肥中的小明",
    "bmr": 1650,              // [自动计算] 基础代谢
    "daily_kcal_limit": 1800, // [自动计算] 每日推荐摄入
    "goal_type": "lose"
  }
}

```

---

## 🍎 3. 冰箱库存 (Pantry Domain)

### 3.1 获取冰箱列表

* **接口**: `GET /diet/fridge/`
* **参数**:
* `category`: (可选) 分类筛选，如 `vegetable`。
* `search`: (可选) 搜索关键词。



**响应示例**:

```json
{
  "code": 200,
  "data": {
    "total": 12,
    "items": [
      {
        "id": 10,
        "name": "牛奶",
        "category": "dairy",
        "sub_category": "鲜奶",
        "amount": 2.0,
        "unit": "盒",
        "days_stored": 2,       // 已存放天数
        "freshness": "expiring", // fresh=新鲜, expiring=临期(<=3天), expired=过期
        "expiry_date": "2026-01-30"
      }
    ]
  }
}

```

### 3.2 添加/更新食材

* **接口**: `POST /diet/fridge/` (添加) 或 `PATCH /diet/fridge/{id}/` (更新)

**请求参数**:

```json
{
  "name": "全麦面包",
  "amount": 1,
  "unit": "袋",
  "category": "grain",
  "expiry_date": "2026-02-05", // 可选，过期日期 YYYY-MM-DD
  "is_scrap": false            // 是否为边角料 (用于大扫除模式推荐)
}

```

### 3.3 全量同步库存

* **接口**: `POST /diet/fridge/sync/`
* **描述**: 用于解决前端本地缓存与后端不一致，强制覆盖。

**请求参数**:

```json
{
  "operation": "override",
  "items": [
    {"name": "鸡蛋", "amount": 6, "unit": "个", "category": "protein"}
  ]
}

```

---

## 🔍 4. 搜餐与推荐 (Discovery Domain)

### 4.1 智能搜餐 (含大扫除模式)

* **接口**: `POST /diet/search/`
* **描述**: 统一搜索接口，支持菜谱搜索和外卖搜索。

**场景 A: 搜菜谱 (做饭模式)**

```json
// 请求
{
  "mode": "cook",
  "page": 1,
  "filters": {
    "cleanup_mode": true,   // [核心] 开启大扫除模式 (优先消耗临期/边角料)
    "keyword": "汤",        // (可选) 搜索词
    "tags": ["快手菜"],     // (可选) 标签
    "calorie_max": 600      // (可选) 热量上限
  }
}

// 响应
{
  "code": 200,
  "data": {
    "has_more": true,
    "recommendations": [
      {
        "id": "65b...",
        "name": "番茄鸡蛋汤",
        "image": "http://...",
        "match_score": 95,          // 匹配度
        "match_reason": "消耗临期食材", // 推荐理由
        "missing_ingredients": [],  // 缺少的食材
        "calories": 120,
        "cooking_time": 10
      }
    ]
  }
}

```

**场景 B: 搜外卖 (LBS模式)**

```json
// 请求
{
  "mode": "restaurant",
  "lng": 116.40,
  "lat": 39.90
}

// 响应
{
  "data": {
    "recommendations": [
      {
        "id": "TEST_002",
        "name": "轻食主义沙拉",
        "health_light": "green", // 红绿灯评级 (green/yellow/red)
        "distance": 500
      }
    ]
  }
}

```

### 4.2 智能大转盘

* **接口**: `POST /diet/wheel/`
* **描述**: 三步递进式推荐。

**请求参数**:

* Step 1: `{ "step": 1 }` -> 返回菜系列表
* Step 2: `{ "step": 2, "cuisine": "川菜" }` -> 返回口味列表
* Step 3: `{ "step": 3, "cuisine": "川菜", "flavor": "麻辣" }` -> 返回最终推荐结果

**Step 3 响应示例**:

```json
{
  "data": {
    "recommendations": [
      {
        "name": "麻婆豆腐",
        "match_reason": "健康轻食", // 3个健康
        "type": "recipe"
      },
      {
        "name": "水煮牛肉",
        "match_reason": "偶尔放纵", // 1个放纵
        "type": "recipe"
      }
    ]
  }
}

```

### 4.3 菜谱详情

* **接口**: `GET /diet/recipe/{id}/`
* **响应示例** (含替代品):

```json
{
  "data": {
    "id": "...",
    "name": "红烧肉",
    "ingredients": [
      {
        "name": "五花肉",
        "in_fridge": true,
        "substitutes": []
      },
      {
        "name": "冰糖",
        "in_fridge": false,
        "substitutes": [{"name": "白糖", "reason": "甜味来源"}] // [v3.1] 替代方案
      }
    ],
    "steps": [{"step": 1, "description": "..."}]
  }
}

```

---

## 📝 5. 饮食记录 (Journal Domain)

### 5.1 记录饮食

* **接口**: `POST /diet/log/`
* **核心逻辑**: 如果是菜谱来源，会自动扣减冰箱库存。

**请求参数**:

```json
{
  "source_type": 1,       // 1=菜谱, 2=外卖, 3=自定义
  "source_id": "65b...",  // 菜谱ID 或 商家ID
  "portion": 1.0,         // 份数
  "deduct_fridge": true,  // [核心] 是否扣减冰箱库存
  "meal_time": "12:30",   // (可选) 具体时间
  "meal_type": "lunch",   // breakfast, lunch, dinner, snack
  
  // 仅 source_type=3 时需要传
  "food_name": "黑咖啡",
  "calories": 15
}

```

**响应示例**:

```json
{
  "code": 200,
  "msg": "记录成功 (+350 kcal)",
  "data": {
    "log_id": 12,
    "remaining_calories": 1200, // 今日剩余额度
    "daily_summary": { ... }    // 返回最新汇总，方便前端更新进度条
  }
}

```

### 5.2 运动打卡

* **接口**: `POST /diet/workout/save/`

**请求参数**:

```json
{
  "type": "running",
  "duration": 30,       // 分钟
  "calories_burned": 300,
  "date": "2026-01-29"
}

```

---

## 📊 6. 数据报表 (Analytics Domain)

### 6.1 获取图表数据 (前端渲染专用)

* **接口**:
* 日视图: `GET /diet/report/charts/daily/?date=2026-01-29`
* 周视图: `GET /diet/report/charts/weekly/`
* 体重图: `GET /diet/report/charts/weight/`



**日视图响应 (ECharts 结构)**:

```json
{
  "data": {
    "calorie_chart": {
      "type": "progress_bar",
      "consumed": 1200,
      "target": 1800,
      "percent": 66.6,
      "colors": {"consumed": "#4CAF50", "remaining": "#2196F3"}
    },
    "nutrient_chart": {
      "type": "semi_donut",
      "data": [
        {"name": "碳水", "value": 150, "color": "#2196F3"},
        {"name": "蛋白质", "value": 80, "color": "#FF9800"},
        {"name": "脂肪", "value": 40, "color": "#9C27B0"}
      ]
    }
  }
}

```

### 6.2 每日汇总 (含评级)

* **接口**: `GET /diet/summary/?date=YYYY-MM-DD`
* **响应示例**:

```json
{
  "data": {
    "summary": {
      "health_level": "excellent", // excellent, good, warning, danger
      "health_tip": "今日表现完美，继续保持！",
      "intake_actual": 1500,
      "macros": {
        "protein": {"consumed": 80, "target": 100, "percentage": 80}
      }
    }
  }
}

```

---

## 🤖 7. AI 与工具 (Tools Domain)

### 7.1 拍图识热量 (AI)

* **接口**: `POST /diet/ai/food-recognition/`
* **Content-Type**: `multipart/form-data`

**请求参数**:

* `image`: 文件对象 (jpg/png)

**响应示例**:

```json
{
  "code": 200,
  "data": {
    "food_name": "香煎鸡胸肉配西兰花",
    "calories": 320,
    "nutrition": {
      "carbohydrates": 10,
      "protein": 40,
      "fat": 5
    },
    "description": "非常健康的减脂餐，高蛋白低碳水。"
  }
}

```

### 7.2 生成购物清单

* **接口**: `POST /diet/shopping-list/generate/`
* **描述**: 对比选中菜谱所需的食材和冰箱库存，生成缺货清单。

**请求参数**:

```json
{
  "recipe_ids": ["65b1...", "65b2..."]
}

```

**响应示例**:

```json
{
  "data": {
    "list": [
      {
        "name": "料酒",
        "status": "missing", // missing=缺货, check=库存有但可能不够
        "related_recipes": ["红烧肉"]
      }
    ]
  }
}

```

### 7.3 挑战任务

* **接口**: `GET /diet/challenge/tasks/`
* **响应**:

```json
{
  "data": [
    {
      "title": "早餐打卡",
      "desc": "记录一顿健康的早餐",
      "reward": 10,
      "status": "completed" // completed / pending
    }
  ]
}

```