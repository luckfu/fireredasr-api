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

# --- 增加調試指令 ---
# 為了調試 "not found" 錯誤，我們先嘗試將整個建置上下文 (build context)
# 複製到一個臨時目錄中，然後列出其內容。
# 如果這一步成功，日誌將會顯示 GitHub Actions 傳遞給 Docker 的所有檔案。
COPY . /tmp/context
RUN ls -laR /tmp/context
# ---------------------

# 從正確的子目錄 fireredasr-api 複製 requirements.txt
COPY fireredasr-api/requirements.txt .

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

# 從正確的子目錄 fireredasr-api 複製應用程式碼到當前工作目錄
COPY fireredasr-api/ .

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
