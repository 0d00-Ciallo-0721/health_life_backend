# 🐳 Docker Containerization (容器化部署指南)

> **目录位置**: `/docker/`
>
> **模块定位**: 本模块包含项目容器化所需的所有配置文件。通过 Docker，我们可以将 Django、MySQL、MongoDB、Redis 和 Nginx 封装在一个隔离的环境中，实现“一键启动，到处运行”。

## 📖 1. 模块概览

本项目采用了 **Docker Compose** 进行多容器编排。这种方式避免了在服务器上手动安装各种数据库软件的繁琐过程，保证了开发环境与生产环境的高度一致性。

### 📁 文件清单

| 文件名 | 核心作用 |
| :--- | :--- |
| **`Dockerfile`** | **镜像构建蓝图**。定义了如何构建 Django 应用镜像（基于 Python 3.11 Slim），安装依赖、Gunicorn 等。 |
| **`nginx/default.conf`** | **反向代理配置**。定义 Nginx 如何处理静态文件请求，以及如何将 API 流量转发给 Django 容器。 |

*(注：`docker-compose.yml` 位于项目根目录，但它深度依赖本文件夹内的配置)*

---

## 🏗 2. 容器架构图

```mermaid
graph TD
    User[用户/小程序] -->|端口 80| Nginx(Nginx 容器)
    
    subgraph Docker Network
        Nginx -->|/static| StaticVolume[静态文件卷]
        Nginx -->|/api| Web(Django Web 容器)
        
        Web -->|TCP 3306| DB(MySQL 8.0 容器)
        Web -->|TCP 27017| Mongo(MongoDB 6.0 容器)
        Web -->|TCP 6379| Redis(Redis 7.0 容器)
    end
🛠 3. 核心配置解析
3.1 Dockerfile
我们使用了多阶段构建的最佳实践：

Base Image: python:3.11-slim，体积小，构建快。

Dependencies: 安装了 default-libmysqlclient-dev 和 gcc，这是编译 mysqlclient 驱动所必须的。

Command: 使用生产级服务器 gunicorn 启动应用，而不是开发用的 runserver。

3.2 Nginx 配置 (default.conf)
Nginx 在这里扮演两个角色：

静态资源服务器: Django 的 Admin 后台样式文件（CSS/JS）通过 alias /app/static/; 直接由 Nginx 返回，不经过 Python，效率极高。

反向代理: 将 API 请求转发给 web:8000。

🚀 4. 常用运维命令
所有命令均需在项目根目录（docker-compose.yml 所在位置）执行。

启动与停止
Bash

# 后台启动所有服务 (首次运行会自动构建)
docker-compose up -d

# 停止并删除容器 (保留数据卷)
docker-compose down

# 强制重新构建镜像 (当修改了 requirements.txt 或 Dockerfile 后)
docker-compose up -d --build
数据与维护
Bash

# 查看实时日志 (用于排查报错)
docker-compose logs -f web

# 进入 Django 容器内部 (执行 manage.py 命令)
docker-compose exec web bash

# 示例: 在容器内创建管理员
root@Container:/app# python manage.py createsuperuser
数据库备份
由于使用了 Docker Volume (mysql_data, mongo_data)，即使删除容器，数据也不会丢失。 若要导出数据：

Bash

# 导出 MySQL 数据到宿主机
docker-compose exec db mysqldump -u root -p health_life_db > backup.sql
❓ 常见问题 (FAQ)
Q1: 启动后访问 localhost 报错 502 Bad Gateway？

A: 这通常意味着 Django 容器 (web) 还没启动完成，或者报错退出了。请运行 docker-compose logs web 查看具体报错信息（常见原因是数据库连接失败或缺少依赖）。

Q2: 静态文件（Admin后台样式）丢失？

A: 首次部署时需要收集静态文件。请运行： docker-compose exec web python manage.py collectstatic --noinput

Q3: 如何连接容器里的数据库？

A: 数据库端口默认只暴露在 Docker 网络内部。如果需要在宿主机用 Navicat 连接，需要在 docker-compose.yml 中添加 ports 映射（如 "3306:3306"）。