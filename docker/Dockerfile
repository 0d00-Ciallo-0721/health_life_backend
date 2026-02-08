# 使用官方轻量级 Python 镜像
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 设置工作目录
WORKDIR /app

# 安装系统依赖 (MySQL驱动需要 gcc 和 libmysqlclient-dev)
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
# 安装 Gunicorn (生产环境服务器)
RUN pip install gunicorn

# 复制项目代码
COPY . /app/

# 暴露端口 (仅用于容器间通信)
EXPOSE 8000

# 启动命令 (使用 gunicorn)
CMD ["gunicorn", "health_life.wsgi:application", "--bind", "0.0.0.0:8000"]