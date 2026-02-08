# 🥗 Diet Domain (核心饮食业务领域)

> **目录位置**: `/apps/diet/`
> **模块定位**: 本模块是系统的“心脏”。它负责解决“今天吃什么”这一终极难题，管理着用户的冰箱库存、饮食记录、以及复杂的 LBS 外卖推荐算法。

## 📖 1. 模块概览

此模块展示了 **Hybrid Persistence (混合存储)** 的最佳实践：

* **结构化数据 (MySQL)**: 谁(User)吃了什么(Intake)？冰箱里有什么(Fridge)？这需要强一致性。
* **非结构化/LBS数据 (MongoDB)**: 菜谱(Recipe)包含复杂的嵌套成分，商家(Restaurant)需要按经纬度查询。这需要 NoSQL 的灵活性。
* **业务逻辑 (Service)**: 所有复杂的计算（匹配、搜索、去重）都封装在 Service 层。

### 📁 文件清单

| 文件名 | 核心作用 | 技术亮点 |
| --- | --- | --- |
| **`models.py`** | **MySQL 模型**。定义冰箱库存、饮食日记、用户偏好。 | ✅ **JSONField** (存储营养素)<br>

<br>✅ **事务支持** |
| **`documents.py`** | **MongoDB 文档**。定义菜谱结构和商家缓存。 | ✅ **GeoSpatial Index** (地理索引)<br>

<br>✅ **Embedded Fields** |
| **`services.py`** | **业务逻辑大脑**。LBS 搜寻、大转盘算法、库存扣减。 | ✅ **LBS 三级缓存** (Redis/Mongo/API)<br>

<br>✅ **聚合管道** |
| **`views.py`** | **API 接口**。参数校验与 Service 调用。 | ✅ **瘦视图模式** (Thin View) |
| **`management/`** | **ETL 工具**。包含 `load_data` 命令。 | ✅ **批量导入优化** |

---

## 💾 2. 混合数据架构 (Hybrid Architecture)

这是本项目最显著的架构特征，我们在 `models.py` 和 `documents.py` 中分别定义了两种不同类型的数据实体。

### 2.1 关系型数据 (MySQL)

用于存储需要 **ACID 事务保障** 的用户私有数据。

* **`FridgeItem` (冰箱库存)**:
    * 记录用户买了什么食材。
    * **(v1.1新增)** `amount` (数值) 和 `unit` (单位)：支持精确记录（如 `2.5 kg`），为后续的精确扣减做准备。
    * **业务价值**: 用于与菜谱进行“食材匹配”，计算匹配度。


* **`DailyIntake` (饮食记录)**:
* 记录用户每一顿饭摄入的热量。
* **`nutrients` 字段**: 使用 MySQL 8.0/SQLite 的 `JSONField` 存储 `{ "carb": 20, "protein": 10 }`，既保留了扩展性，又支持 SQL 查询。


* **`UserPreference` (用户偏好)**:
* 记录用户“拉黑”的菜谱或商家，在推荐算法中进行过滤。

* **`(v2.1新增)`** `amount` (Float) 和 `unit` (String): 支持精确库存管理（如 `2.5 kg`）。
    * **交互升级**: 支持 `PATCH` 请求修改余量，支持 `search` 参数进行模糊搜索。

### 2.2 文档型数据 (MongoDB)

用于存储 **海量、读多写少、结构复杂** 的公共数据。

* **`Recipe` (菜谱)**:
* 包含 `ingredients` (列表)、`instructions` (步骤列表) 等嵌套结构，用 SQL 存非常痛苦，用 Mongo 原生支持。


* **`Restaurant` (LBS 商家缓存)**:
* **核心字段**: `location = PointField()`。
* **作用**: 这是一个“地理位置缓存池”。我们不存全网商家，只存用户查询过的区域附近的商家。利用 MongoDB 的 `$near` 操作符实现“查找周围 3km 的店”。



---

## 🧠 3. 核心业务逻辑解析 (`services.py`)

这里是代码含金量最高的地方。

### 3.1 LBS 智能外卖推荐 (`get_restaurant_recommendations`)

为了节省高德 API 调用额度并提升速度，我们设计了 **“三级火箭”缓存策略**：

1. **一级缓存 (Redis GeoHash)**:
* 将用户坐标 `(lng, lat)` 计算为 GeoHash 键（保留2位小数，约覆盖几公里范围）。
* **命中**: 直接返回 JSON，耗时 < 10ms。
* **未命中**: 进入下一级。


2. **二级缓存 (MongoDB LBS)**:
* 在 `restaurant_cache` 集合中执行 `$near` 查询。
* **命中**: 说明该区域之前有人查过，返回数据并写入 Redis。
* **未命中** (或数据量不足): 进入下一级。


3. **三级兜底 (AMap API)**:
* 实时调用高德地图 Web 服务 API。
* **数据回写**: 将抓取到的商家数据**清洗**后存入 MongoDB，同时也写入 Redis。下次有人在附近查，就能直接命中了。

### 3.12 智能购物清单算法 (`ShoppingListService`) **(v3.1 新增)**

解决了“想做这几道菜，还需要买什么？”的痛点。

* **逻辑**:
    1. **聚合需求**: 遍历用户选中的多个菜谱，提取所有食材标准名 (`Recipe.ingredients_search`)。
    2. **库存快照**: 获取用户当前冰箱库存 (`FridgeItem`)。
    3. **差集计算**: `Need - Have = Buy`。
    4. **状态标记**:
        * `missing` (缺货): 库存为 0。
        * `check` (需核对): 库存 > 0，但无法确定具体份量是否足够（提醒用户检查）。

### 3.13 图表数据生成服务 (`ChartService`) **(v3.1 新增)**

为了极致的前端性能优化，我们将图表数据的加工逻辑全部移至后端。

* **设计思想**: **Server-Side Configuration**。
* **输出示例**:
    ```json
    {
      "type": "progress_bar",
      "data": { "consumed": 1800, "target": 2000 },
      "config": { "colors": { "consumed": "#4CAF50", "remaining": "#2196F3" } }
    }
    ```
* **优势**: 前端无需处理复杂的颜色逻辑和百分比计算，拿到 JSON 直接喂给 ECharts/Canvas 即可渲染。

### 3.2 动态大转盘算法 (`get_wheel_options`)

“今天吃什么”大转盘不是静态的，而是基于菜谱库动态生成的。

* **Step 1 (选菜系)**: 硬编码热门菜系（川、鲁、粤...）。
* **Step 2 (选口味)**: **MongoDB 聚合查询**。
* 使用 pipeline: `Match(菜系)` -> `Unwind(keywords)` -> `Group(keywords, count)` -> `Sort(count)`。
* 实时分析出该菜系下最热门的口味（如选“川菜”，自动推荐“麻辣”、“水煮”、“干锅”）。


* **Step 3 (选菜)**: 在限定范围内随机抽取 8 道菜。

### 3.3 原子化饮食记录 (`log_intake`)

当用户点击“我吃了这道菜”时，后端执行一个 **Transaction (事务)**：

1. 在 `DailyIntake` 表插入一条记录（增加热量）。
2. (可选) 自动从 `FridgeItem` 表中**删除**对应的食材（扣减库存）。
3. **原子性**: 如果扣减库存失败，饮食记录也会回滚，保证数据绝对一致。

### 3.4 食材同义词引擎 (Synonym Engine) **(v1.1新增)**
为了解决“用户存西红柿，菜谱写番茄”导致匹配失败的问题，我们在 Service 层引入了归一化逻辑。
* **原理**: 在匹配前，调用 `_normalize_ingredients` 方法，将 `FridgeItem` 和 `Recipe` 中的食材都通过字典映射为标准名（如 `洋芋` -> `土豆`），从而大幅提升“自己做”模式的召回率。

### 3.5 月报日历聚合 (`get_monthly_calendar`) **(v1.1新增)**
* **场景**: 前端日历组件，需要展示某个月每一天的打卡状态。
* **逻辑**: 
    1. 接收 `year`, `month` 参数。
    2. 聚合该月所有 `DailyIntake` 记录。
    3. 对比 `daily_kcal_limit`，计算每日状态：
        * `perfect` (绿色): 摄入量在目标 ±10% 范围内。
        * `exceeded` (红色): 严重超标。
        * `insufficient` (黄色): 摄入不足。
        * `none` (灰色): 未记录。

### 3.6 报表结构化分组 (`grouped_items`) **(v2.1新增)**
为了减轻前端处理日报时间轴的压力，后端 `get_daily_summary` 接口不再只返回扁平列表，而是根据 `meal_time` 自动归类：
* **结构**: `{ "breakfast": [...], "lunch": [...], "snack": [...] }`
* **逻辑**: 自动根据记录时间判定餐段（6-10点为早餐，10-14点为午餐等）。

### 3.7 外卖热量估算引擎 **(v2.1新增)**
在 LBS 搜索结果中，为了支持前端的“健康红绿灯”展示，后端增加了预估逻辑：
* **规则**:
    * 店铺类型包含“轻食/沙拉” -> `400 kcal`
    * 店铺类型包含“炸鸡/汉堡” -> `800 kcal`
    * 其他 -> `600 kcal`

### 3.8 智能搜餐引擎 V2 (`get_cook_recommendations`) **(v2.3新增)**

为了满足前端复杂的筛选需求，我们在 Mongo 查询构建上做了深度优化：

* **动态 Query 构建**:
    * `filters` 参数支持字典解包。
    * **范围查询**: `calories__gte` / `calories__lte`。
    * **模糊匹配**: `name__icontains`。
* **鲁棒性设计 (Defensive Coding)**:
    * 针对 MongoDB 中可能存在的脏数据（如 `ingredients_search` 为 `None` 或非列表），在代码层面做了 `try-except` 单条隔离。
    * **效果**: 即使数据库中有坏数据，接口也不会 500，只会跳过该条目。

### 3.9 统一偏好服务 (`PreferenceService`) **(v2.3新增)**

从 v2.x 的“整行删除”升级为“数值扣减”，实现了真实的库存流转。

* **输入**: 菜谱 ID + 份数 (Portion)。
* **流程**:
    1.  **归一化**: 将菜谱食材 (`番茄`) 映射为标准名 (`西红柿`)。
    2.  **FIFO 匹配**: 在 MySQL 中查找该用户所有的 `西红柿` 库存，按 `created_at` 正序排列。
    3.  **递归扣减**:
        * 若第一批库存不够，扣完删除，剩余需求转嫁到第二批库存。
        * 若库存充足，仅更新 `amount` 字段。
* **事务性**: 整个过程包裹在 `transaction.atomic` 中，确保数据强一致。

### 3.10 场景化搜餐算法 (`RecommendationService`) **(v3.0 新增)**

为了解决“食材浪费”痛点，我们引入了特殊的排序权重：

* **大扫除模式 (`cleanup_mode`)**:
    * 筛选出 `expiry_date <= T+3` 的食材集合 $S_{exp}$。
    * 查询包含 $S_{exp}$ 任意元素的菜谱。
    * **加权**: 命中临期食材的菜谱 `match_score + 20`。
* **替代方案推荐 (`get_recipe_substitutes`)**:
    * 当计算出 `missing_ingredients` 后，查询内置的替换规则字典。
    * 输出: `{"name": "生抽", "in_fridge": false, "substitutes": [{"name": "盐", "reason": "咸味替代"}]}`。

### 3.11 黄金比例转盘 (`get_smart_wheel_candidates`) **(v3.0 重构)**

解决了“推荐太健康不想吃”或“推荐太放纵不敢吃”的矛盾。

* **池子 A (健康)**: 3个。筛选 `calories < TDEE/3` 且非黑名单的菜品。
* **池子 B (偏好)**: 2个。基于用户历史口味标签或高分菜谱。
* **池子 C (放纵)**: 1个。允许高热量，但必须符合用户口味。
* **风控**: 全局过滤 `Profile.allergens` (过敏源) 和 `UserPreference.block` (黑名单)。
---

## 📊 4. 推荐与报表算法

### ... (保留 4.1 - 4.2) ...

### 4.3 周报深度聚合 (`get_weekly_report`) **(v2.3新增)**

不仅仅是简单的求和，我们为用户生成了一份“饮食周报”：

* **Timeline**: 完整的时间轴记录。
* **极值分析**: 使用 `order_by('-calories').first()` 快速找出本周热量最高的一餐（"热量炸弹"）。
* **趋势分析**: 补全日期空洞，确保前端图表 X 轴连续。


## 📊 4. 推荐与报表算法

### 4.1 冰箱食材匹配算法

* **逻辑**: 简单的集合运算 (Set Intersection)。
* **公式**: `匹配度 = (冰箱食材 ∩ 菜谱食材) / 菜谱所需总食材`。
* **效果**: 优先推荐那些能消耗你冰箱库存的菜谱。

### 4.2 历史趋势分析 (`DietHistoryView`)

* **功能**: 获取过去 7 天的热量摄入趋势。
* **实现**: 循环 `today - i days`，对每一天的 `DailyIntake` 进行 `Sum('calories')` 聚合。

---

## 🛠 5. 数据导入与维护 (`management/`)

### 5.1 数据清洗 (`import_full_recipes.py`)

由于原始菜谱数据（2GB JSON）质量参差不齐，我们在导入脚本中做了清洗：

* **提取食材**: 从 `100g 羊肉` 中提取出 `羊肉` 用于搜索。
* **打标**: 根据菜名自动打上“川菜”、“快手”等 Tag。
* **批量写入**: 使用 `Recipe.objects.insert(batch, load_bulk=True)` 每 500 条一次 IO，极大地提升了导入速度。

### 5.2 重置商家 (`reset_restaurant_data.py`)

用于开发环境。它会清空 MongoDB 中的商家数据，并插入几条位于“测试坐标”的标准数据，确保 LBS 接口在没有外网时也能返回 Mock 数据。

---

## ❓ 常见问题 (FAQ)

**Q1: 为什么我的“附近外卖”搜不到东西？**

> A:
> 1. 检查 `.env` 是否配置了 `AMAP_WEB_KEY`。
> 2. 检查 MongoDB 是否运行正常（没有 Mongo 也可以跑，但只会返回空列表）。
> 3. 你的坐标可能太偏僻，高德 API 没返回数据。
> 
> 

**Q2: 为什么 `FridgeItem` 没有数量单位？**

> A: 初期设计为了简化交互，只存了 `quantity` 字符串（如 "2个"）。后期可扩展为 `amount` (float) + `unit` (enum) 以支持精确换算。

**Q3: 修改了 `Recipe` 结构，需要 `makemigrations` 吗？**

> A: **不需要**。`Recipe` 是 MongoDB 文档，Schema-less（无模式），直接改代码即可，无需迁移数据库文件。但 MySQL 的 `models.py` 修改后必须迁移。