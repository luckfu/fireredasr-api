# FireRedASR API

FireRedASR语音识别模型的 API 服务。

## 功能特性

- 支持 NVIDIA CUDA 加速
- 基于 Flask 的 REST API
- 支持多种 ASR 模型（AED 和 LLM）
- 支持 VAD 的音频文件处理
- Docker 容器化部署

## 模型设置

### 模型目录结构

在运行应用程序之前，您需要下载并按以下结构组织预训练模型：

```
pretrained_models/
├── FireRedASR-AED-L/         # 从 HuggingFace 下载
│   ├── model.pth.tar         # 不要解压，直接使用
│   ├── cmvn.ark
│   ├── cmvn.txt
│   ├── config.yaml
│   ├── dict.txt
│   └── train_bpe1000.model
└── FireRedASR-LLM-L/         # 从 HuggingFace 下载
    ├── model.pth.tar         # 不要解压，直接使用
    ├── cmvn.ark
    ├── cmvn.txt
    ├── config.yaml
    └── Qwen2-7B-Instruct/    # 从 HuggingFace 下载
        ├── model-00001-of-00004.safetensors
        ├── model-00002-of-00004.safetensors
        ├── model-00003-of-00004.safetensors
        └── model-00004-of-00004.safetensors
```

### 模型下载链接

**AED 模型：**
- 从以下地址下载 `model.pth.tar`：https://huggingface.co/FireRedTeam/FireRedASR-AED-L
- 将其放置在 `pretrained_models/FireRedASR-AED-L/` 目录中

**LLM 模型：**
- 从以下地址下载 `model.pth.tar`：https://huggingface.co/FireRedTeam/FireRedASR-LLM-L
- 将其放置在 `pretrained_models/FireRedASR-LLM-L/` 目录中
- 下载 Qwen2-7B-Instruct 模型文件并将它们放置在 `pretrained_models/FireRedASR-LLM-L/Qwen2-7B-Instruct/` 目录中：


## 快速开始

### 使用 Docker

```bash
# 构建镜像
docker build -t fireredasr-api .

# 运行容器并映射模型目录
docker run --gpus all -p 5078:5078 \
  -v /path/to/your/pretrained_models:/app/pretrained_models \
  fireredasr-api:latest
```

**注意：** 请将 `/path/to/your/pretrained_models` 替换为您主机上模型目录的实际路径。模型将被映射到容器内的 `/app/pretrained_models` 目录。

### 使用 Docker Compose

```bash
# 更新 docker-compose.yml 以包含模型卷映射：
# volumes:
#   - ./pretrained_models:/app/pretrained_models
#   - ./logs:/app/logs
#   - ./static/tmp:/app/static/tmp

docker-compose up -d
```

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用程序
python app.py
```

## API 使用

### 转录接口

**使用 AED 模型：**
```bash
curl -X POST http://localhost:5078/v1/audio/transcriptions \
  -F "file=@audio.wav" \
  -F "model=AED"
```

**使用 LLM 模型：**
```bash
curl -X POST http://localhost:5078/v1/audio/transcriptions \
  -F "file=@audio.wav" \
  -F "model=LLM" \
  -F "response_format=json"
```



**参数说明：**
- `file`: 音频文件路径（支持 WAV、MP3 等格式）
- `model`: 模型类型，可选值为 `AED` 或 `LLM`

## Docker Hub

Docker Hub 上提供了支持 CUDA 的预构建镜像。 
> docker pull luckfu/fireredasr-api:cuda-12.1

## 阿里云镜像仓库 

> docker pull registry.cn-shanghai.aliyuncs.com/luckfu/fireredasr-api:cuda-12.1


## 许可证

MIT 许可证