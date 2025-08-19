# GitHub Actions 设置指南

## 配置 Docker Hub 自动构建

### 1. 设置 GitHub Secrets

在你的 GitHub 仓库中，进入 `Settings` > `Secrets and variables` > `Actions`，添加以下 secrets：

- `DOCKER_USERNAME`: 你的 Docker Hub 用户名
- `DOCKER_PASSWORD`: 你的 Docker Hub 访问令牌（推荐使用访问令牌而不是密码）

### 2. 获取 Docker Hub 访问令牌

1. 登录 [Docker Hub](https://hub.docker.com/)
2. 点击右上角头像 > `Account Settings`
3. 选择 `Security` 标签
4. 点击 `New Access Token`
5. 输入令牌描述，选择权限（推荐 `Read, Write, Delete`）
6. 复制生成的令牌

### 3. 工作流说明

当前的 GitHub Actions 工作流会在以下情况下触发：

- 推送到 `main` 或 `develop` 分支
- 创建新的版本标签（如 `v1.0.0`）
- 手动触发
- Pull Request 到 `main` 分支（仅构建，不推送）

### 4. Docker 镜像标签

工作流会自动生成以下标签：

- `latest`: 最新的 main 分支构建
- `cuda-12.8`: 标识 CUDA 版本
- `main`: main 分支构建
- `v1.0.0`: 版本标签（如果推送了版本标签）

### 5. 使用构建的镜像

```bash
# 拉取最新镜像
docker pull your-dockerhub-username/fireredasr-api:latest

# 运行容器
docker run --gpus all -p 5078:5078 your-dockerhub-username/fireredasr-api:latest
```

### 6. 本地测试

```bash
# 构建镜像
docker build -t fireredasr-api .

# 使用 docker-compose 运行
docker-compose up -d
```

## 注意事项

1. 确保你的 Docker Hub 仓库存在或设置为自动创建
2. CUDA 镜像较大，构建时间可能较长
3. 工作流仅支持 linux/amd64 平台
4. 需要 GPU 支持的环境才能正常运行