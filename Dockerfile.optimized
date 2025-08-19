# 多阶段构建 - 构建阶段
FROM nvidia/cuda:12.8.0-devel-ubuntu22.04 as builder

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装构建依赖
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    git \
    wget \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 创建符号链接
RUN ln -s /usr/bin/python3 /usr/bin/python

# 设置工作目录
WORKDIR /app

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖到临时目录
RUN pip3 install --user --no-cache-dir -r requirements.txt && \
    pip3 install --user --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 运行时阶段
FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/root/.local/lib/python3.10/site-packages:$PYTHONPATH

# 只安装运行时必需的依赖
RUN apt-get update && apt-get install -y \
    python3 \
    python3-distutils \
    ffmpeg \
    libsndfile1 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# 创建符号链接
RUN ln -s /usr/bin/python3 /usr/bin/python

# 设置工作目录
WORKDIR /app

# 从构建阶段复制已安装的Python包
COPY --from=builder /root/.local /root/.local

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p logs static/tmp

# 设置权限
RUN chmod +x app.py

# 暴露端口
EXPOSE 5078

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5078/ || exit 1

# 启动命令
CMD ["python", "app.py"]