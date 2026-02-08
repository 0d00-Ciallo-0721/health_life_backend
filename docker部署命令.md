### 第一阶段：整理文件结构

首先，我们需要把之前生成的 Docker 代码文件放到正确的位置。请确保你的项目根目录结构如下（如果缺少文件夹请手动创建）：

```text
health_life_backend/  (根目录)
├── docker/
│   ├── nginx/
│   │   └── default.conf      <-- (1) Nginx 配置文件
│   └── Dockerfile            <-- (2) Django 镜像构建文件
├── docker-compose.yml        <-- (3) 容器编排文件
├── .env                      <-- (4) 环境变量文件
├── requirements.txt          <-- (5) 依赖清单
├── data_backup.json          <-- (6) 刚才备份的MySQL数据
└── ... (其他源码文件)

```

**检查点**：

* **`.env`**: 确保里面有一行 `FORCE_MYSQL=True`（因为 Docker 里我们是用 MySQL 容器，不是 SQLite）。
* **`settings.py`**: 确保你已经按照我上一条回复，修改了 `DATABASES` 配置，使用了 `os.environ.get('DB_HOST', ...)`。这非常关键，否则 Django 会傻傻地去连 `127.0.0.1` 而不是 Docker 里的 `db` 容器。

---

### 第二阶段：启动 Docker 集群

1. **启动软件**：确保你电脑右下角的 **Docker Desktop** 图标已经是绿色的（Running）。
2. **打开终端**：在项目根目录（即 `docker-compose.yml` 所在的文件夹）打开 PowerShell 或 CMD。
3. **构建并启动**：
执行以下命令，Docker 会自动下载 MySQL、Mongo、Redis 镜像，并打包你的 Django 代码：
```powershell
docker-compose up -d --build

```


* `-d`: 后台静默运行。
* `--build`: 强制重新构建镜像（确保你的最新代码被打包进去）。
* *首次运行可能需要几分钟下载镜像，请耐心等待。*


4. **检查状态**：
执行：
```powershell
docker-compose ps

```


你应该能看到 `web`, `nginx`, `db`, `mongo`, `redis` 这 5 个服务的状态都是 **Up** (Running)。

---

### 第三阶段：初始化数据 (最关键一步)

Docker 启动的数据库是**空的**！我们需要把之前备份的数据导入进去。
因为我们使用了 `volumes: - .:/app` 映射，你的本地文件 `data_backup.json` 在容器里也能看到。

请**依次**在终端执行以下命令（这些命令会穿透到 Docker 容器内部执行）：

**1. 导入 MySQL 数据 (用户、档案、冰箱)**
*(注意：migrate 命令通常在启动时已自动运行，如果没有表结构报错，请先运行 `docker-compose exec web python manage.py migrate`)*

```powershell
docker-compose exec web python manage.py loaddata data_backup.json

```

**2. 导入 MongoDB 数据 (菜谱)**

```powershell
docker-compose exec web python -m scripts.import_full_recipes

```

**3. 初始化商家数据 (LBS)**

```powershell
docker-compose exec web python -m scripts.reset_restaurant_data

```

**4. 创建超级管理员 (可选)**
如果你想登录后台：

```powershell
docker-compose exec web python manage.py createsuperuser

```

---

### 第四阶段：访问测试

现在，整个项目已经在 Docker 中运行了。

* **API 访问地址**: `http://127.0.0.1/api/...`
* 注意：**端口是 80**（默认端口，不用输），而不是原来的 `8000`。因为 Nginx (端口 80) 会把请求转发给 Django (端口 8000)。


* **Swagger 文档**: `http://127.0.0.1/api/docs/`
* **Django 后台**: `http://127.0.0.1/admin/`

**测试建议**：
你可以运行之前写的 `test_suite_all.py` 脚本来进行全量测试。

* **修改测试脚本的 URL**：把 `BASE_URL` 改为 `http://127.0.0.1/api/v1` (去掉 :8000)。
* 运行脚本，如果全绿，恭喜你！你的项目已经成功实现了**全栈容器化部署**！🎉

---

### 常用 Docker 维护命令

* **停止所有服务**: `docker-compose stop`
* **停止并删除容器**: `docker-compose down`
* **查看后台日志** (排查报错用): `docker-compose logs -f web`