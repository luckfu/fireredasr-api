# 多階段構建 - 構建階段
FROM nvidia/cuda:12.8.0-devel-ubuntu22.04 as builder

# 設置環境變數
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安裝構建依賴
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    git \
    wget \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 創建符號連結
RUN ln -s /usr/bin/python3 /usr/bin/python

# 設置工作目錄
WORKDIR /app

# --- 修正點 ---
# 複製 requirements.txt (建置上下文已變更為 fireredasr-api 目錄)
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 && \
    pip3 install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache/pip

# 運行時階段
FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04

# 設置環境變數
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 只安裝運行時必需的依賴
RUN apt-get update && apt-get install -y \
    python3 \
    python3-distutils \
    ffmpeg \
    libsndfile1 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 創建符號連結
RUN ln -s /usr/bin/python3 /usr/bin/python

# 設置工作目錄
WORKDIR /app

# 從構建階段複製已安裝的Python包
COPY --from=builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages

# --- 修正點 ---
# 複製應用程式碼 (建置上下文已變更為 fireredasr-api 目錄)
COPY . .

# 創建必要的目錄
RUN mkdir -p logs static/tmp

# 設置權限
RUN chmod +x app.py

# 暴露端口
EXPOSE 5078

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5078/ || exit 1

# 啟動命令
CMD ["python", "app.py"]
