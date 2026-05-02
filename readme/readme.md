# 🥗 Health Life Backend (健康生活小程序后端)

> **版本**: v3.0 (2026-01-14 Final)
> 基于 Django + DRF + MongoDB + Redis 的混合架构高性能后端系统，为微信小程序提供智能饮食推荐、LBS 外卖查询及健康数据追踪服务。

## 📖 项目简介

本项目采用了 **DDD (领域驱动设计)** 思想，通过 **Hybrid Persistence (混合存储)** 架构，完美解决了结构化数据（用户/库存）与非结构化数据（菜谱/地理位置）的共存问题。

核心亮点：

* **混合数据库架构**：MySQL (事务) + MongoDB (海量文档/LBS) + Redis (高频缓存)。
* **智能环境感知**：一套代码同时支持 **高性能服务器模式 (MySQL)** 和 **便携演示模式 (SQLite)**，自动降级，零配置迁移。
* **全栈容器化**：提供完整的 Docker Compose 编排，一键启动所有服务 (Web + DB + Cache + Nginx)。
* **LBS 地理服务**：集成高德地图 API，支持基于 Redis GeoHash 缓存的周边外卖推荐。

---

## 🆕 v3.0 版本新特性 (2026-01-14 重大更新)

后端已完成 **Phase 1-3** 全量重构，达到生产级交付标准：

* **🔍 智能搜餐引擎 3.0**：
    * **大扫除模式 (Cleanup Mode)**：智能识别冰箱中的**临期食材**，优先推荐消耗这些食材的菜谱，拒绝浪费。
    * **多维筛选增强**：支持按 **标签**、**烹饪时间**、**难度**、**热量范围** 以及 **厨具** 组合过滤。
    * **智能替代方案**：当菜谱所需食材缺货时，自动推荐替代品（如“生抽”替“盐”）。

* **🧊 冰箱库存 3.0 (精细化管理)**：
    * **效期管理**：支持录入过期时间 (`expiry_date`)，系统自动计算临期状态。
    * **边角料标记**：支持标记“半个洋葱”等边角料 (`is_scrap`)，搜餐时可开启“边角料模式”。
    * **精确扣减**：饮食记录不再是简单删除库存，而是基于 `amount` 进行**数值扣减** (FIFO 先进先出原则)。

* **📊 深度报表与评级**：
    * **健康评级系统**：根据摄入进度自动打分 (`EXCELLENT` / `GOOD` / `WARNING`)。
    * **营养素目标对比**：根据用户目标（减脂/增肌）动态计算碳水/蛋白/脂肪的目标摄入量。

* **🎡 黄金比例转盘**：
    * 重构推荐算法，实现 **"3健康 + 2偏好 + 1放纵"** 的黄金组合，并在结果中明确标注推荐理由。

## 🆕 v3.1 版本新特性 (2026-01-15 Final Polish)

在 v3.0 的基础上，我们引入了 **AI 赋能** 和 **全栈可视化** 能力，实现了 100% 的需求覆盖：

* **🤖 AI 智能服务 (AI-Powered)**：
    * **拍图识热量**：集成 SiliconFlow 多模态大模型 (`Qwen3-VL`)，用户上传食物照片，毫秒级识别菜品并估算卡路里与营养素。
    * **AI 营养师**：基于用户的 BMR 档案与今日摄入，生成个性化的饮食建议与补救方案。

* **📈 可视化报表引擎 (Chart Engine)**：
    * **后端渲染配置**：不再只返回枯燥的数据，而是由后端直接下发图表配置（颜色代码 `#4CAF50`、堆叠逻辑、坐标轴定义），显著降低前端绘图成本。
    * **多维图表支持**：覆盖 **日报进度条**、**周报堆叠柱状图**、**体重趋势折线图**。

* **🛍️ 生活流扩展 (Life Flow)**：
    * **智能购物清单**：一键将菜谱所需食材与冰箱库存比对，自动生成 "待购清单 (Missing)"。
    * **运动打卡**：新增运动记录模块，支持卡路里消耗统计，补全“吃动平衡”闭环。
    * **碳足迹追踪**：基于饮食结构估算每日碳排放，倡导低碳生活。

---
## 🏗 技术栈

| 模块 | 技术选型 | 说明 |
| --- | --- | --- |
| **Web 框架** | Django 4.2 + DRF | 高效的 RESTful API 开发 |
| **结构化存储** | MySQL 8.0 / SQLite3 | 存储用户档案、冰箱库存、饮食日志 (自动切换) |
| **文档存储** | MongoDB 6.0 | 存储海量菜谱 (Recipe) 和 商家数据 (Restaurant) |
| **缓存/会话** | Redis 7.0 / LocMem | 接口缓存、LBS 坐标缓存、JWT 黑名单 |
| **认证授权** | JWT (SimpleJWT) | 无状态认证，支持微信小程序登录 |
| **API 文档** | drf-spectacular | 自动生成 Swagger/OpenAPI 文档 |
| **部署** | Docker + Nginx + Gunicorn | 生产级容器化部署方案 |

---

## 📂 目录结构

```text
health_life_backend/
├── apps/                   # 业务领域模块
│   ├── common/             # 公共组件 (异常处理, 渲染器, 工具类)
│   ├── diet/               # 饮食核心 (LBS推荐, 大转盘, 库存管理)
│   └── users/              # 用户中心 (微信登录, 身体档案)
├── docker/                 # Docker 构建配置
│   ├── nginx/              # Nginx 配置
│   └── Dockerfile          # Django 镜像构建文件
├── health_life/            # 项目配置中心 (settings.py)
├── scripts/                # 数据维护脚本 (导入菜谱, 重置商家)
├── .env                    # 环境变量 (敏感信息)
├── docker-compose.yml      # 容器编排文件
├── manage.py               # Django 管理入口
├── requirements.txt        # 依赖清单
└── test_suite_all.py       # 全量自动化测试套件

```

---
## 🆕 v2.3 版本新特性 (2026-01-09 最终版)

后端已完成全量业务闭环，达到生产级交付标准：

* **🔍 智能搜餐引擎 V2**：
    * 新增多维度筛选：支持按 **标签** (Tags)、**烹饪时间**、**难度**、**热量范围** 组合过滤。
    * 新增 **Jaccard 匹配算法**：计算冰箱食材与菜谱的重合度，返回 `match_score` 及 `missing_ingredients`。
    * **防御性架构**：Service 层增加了针对 MongoDB 脏数据（如字段缺失/None值）的自动熔断与跳过机制，保障接口高可用。

* **📊 深度报表系统**：
    * **周报 (Weekly)**：自动计算本周“热量炸弹”（最高卡路里餐）与“轻食之星”，生成每日趋势图。
    * **月历 (Calendar)**：聚合每日摄入状态，以 `perfect`/`exceeded`/`insufficient` 三态展示。

* **🧊 冰箱库存 2.0**：
    * 支持 **模糊搜索** (`?search=西红`) 和 **分类筛选**。
    * 修复排序逻辑：按入库时间 (`created_at`) 正序排列，优先消耗旧食材。

* **❤️ 偏好与交互**：
    * **统一偏好服务**：收藏/拉黑逻辑收敛至 `PreferenceService`，支持跨库（MySQL关系 -> Mongo详情）聚合查询。
    * **头像上传**：集成文件存储系统，支持图片上传与 URL 生成。

* **🧪 全自动化测试**：
    * 内置 `test_suite_all.py`，一键覆盖 8 大模块（Auth, Profile, Fridge, Search, LBS, Log, Report, Wheel）的 20+ 个核心场景。


## 🚀 快速开始 (两种方式)

### 方式一：Docker 容器化部署 (推荐 ⭐️)

*适用场景：服务器部署、测试环境、不想安装本地数据库*

1. **准备环境**：确保已安装 Docker 和 Docker Desktop。
2. **配置环境**：确保根目录下有 `.env` 文件，且包含 `FORCE_MYSQL=True`。
3. **一键启动**：
```bash
docker-compose up -d --build

```


4. **初始化数据** (首次运行需执行)：
```bash
# 1. 导入 MySQL 基础数据
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py loaddata data_backup.json

# 2. 导入 MongoDB 菜谱与商家数据
docker-compose exec web python -m scripts.import_full_recipes
docker-compose exec web python -m scripts.reset_restaurant_data

```


5. **访问服务**：
* API 根地址: `http://127.0.0.1/api/v1/` (端口 80)
* Swagger 文档: `http://127.0.0.1/api/docs/`



---

### 方式二：本地 Python 运行 (便携模式)

*适用场景：答辩演示、新电脑快速运行 (无需安装 MySQL/Redis)*

1. **准备环境**：
```bash
# 创建并激活虚拟环境
python -m venv venv
# Windows
.\venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

```


2. **配置环境**：
修改 `.env` 文件，设置 `FORCE_MYSQL=False` (或者直接删除该行)。
*系统会自动降级使用 SQLite 和 本地内存缓存。*
3. **初始化数据**：
```bash
python manage.py migrate
python manage.py loaddata data_backup.json
# MongoDB 数据需确保本地有 MongoDB 服务或连接云数据库

```


4. **启动服务**：
```bash
python manage.py runserver

```

### 涓ょ數鑴戣仈璋冿紙灞€鍩熺綉锛?

濡傛灉寰俊灏忕▼搴忓墠绔拰 Django 鍚庣鍦ㄤ笉鍚岀數鑴戜笂锛岃鎸変笅闈㈡柟寮忛厤缃細

1. 鍚庣鐢佃剳鍚姩 `start_lan.bat`锛屾垨鎵ц `python manage.py runserver 0.0.0.0:8000`
2. 灏嗗悗绔數鑴戠殑灞€鍩熺綉 IP 鍔犲埌 `.env` 涓殑 `ALLOWED_HOSTS`
3. 灏嗕笟鍔″墠绔墍鍦ㄧ數鑴戠殑鍦板潃鍔犲埌 `.env` 涓殑 `CORS_ALLOWED_ORIGINS`
4. 濡傛灉 HTML 鍚庡彴闇€瑕佽法鍩熸彁浜よ〃鍗曟垨鐧诲綍锛屽悓鏃跺姞鍏?`CSRF_TRUSTED_ORIGINS`
5. 鍦ㄥ墠绔腑灏?API 鍩哄湴鍧€ 鏀逛负 `http://鍚庣鐢佃剳IP:8000`
6. 纭繚 Windows 闃茬伀澧欐斁琛?8000 绔彛

绀轰緥锛?

```ini
ALLOWED_HOSTS=127.0.0.1,localhost,192.168.1.10
CORS_ALLOWED_ORIGINS=http://192.168.1.20:3000,http://192.168.1.20
CSRF_TRUSTED_ORIGINS=http://192.168.1.10:8000,http://192.168.1.20:3000
```



---

## ⚙️ 环境配置 (.env)

请在项目根目录创建 `.env` 文件：

```ini
# --- 核心开关 ---
DEBUG=True
SECRET_KEY=your_secret_key
# True=连接MySQL(Docker/本地高性能), False=使用SQLite(便携演示)
FORCE_MYSQL=True 

# --- 数据库配置 (仅 FORCE_MYSQL=True 时生效) ---
DB_NAME=health_life_db
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=db  # Docker环境下填 'db'，本地填 '127.0.0.1'

# --- 第三方服务 ---
# 高德地图 Web服务 Key (必须配置，否则无法使用外卖搜索)
AMAP_WEB_KEY=your_gaode_key
# 微信小程序 (可选)
WECHAT_APP_ID=your_appid
WECHAT_APP_SECRET=your_secret

```

---

## 🧪 测试与验证

项目内置了全量测试套件，支持交互式菜单选择。

**运行测试：**

```bash
python test_suite_all.py

```

**测试菜单：**

1. **基础鉴权**：测试微信登录接口连通性。
2. **档案与冰箱**：测试 BMR 自动计算、冰箱库存增删改查。
3. **LBS 实时搜索**：测试高德 API 实时兜底与 Redis 缓存写入。
4. **记录与报表**：测试饮食日志记录、营养素聚合、7天历史趋势。

---

## 📚 API 文档

项目集成了 Swagger UI，启动后访问：
👉 **[http://127.0.0.1:8000/api/docs/](https://www.google.com/search?q=http://127.0.0.1:8000/api/docs/)** (本地运行)
👉 **[http://127.0.0.1/api/docs/](https://www.google.com/url?sa=E&source=gmail&q=http://127.0.0.1/api/docs/)** (Docker 运行)

主要模块：

* `/api/v1/user/`: 登录、Token 刷新
* `/api/v1/diet/fridge/`: 冰箱库存管理
* `/api/v1/diet/search/`: 智能搜索 (Cook模式 / Restaurant模式)
* `/api/v1/diet/wheel/`: "今天吃什么" 大转盘
* `/api/v1/diet/log/`: 饮食摄入记录
* `/api/v1/diet/summary/`: 每日营养报表

---

## 🛠 维护与脚本

* **备份数据**：
`python manage.py dumpdata users diet > data_backup.json`
* **重置商家测试数据**：
`python -m scripts.reset_restaurant_data`
* **导入全量菜谱**：
`python -m scripts.import_full_recipes`

---

## 📝 License

This project is licensed under the MIT License.
