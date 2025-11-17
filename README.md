# Linux Service Manager

基于Python的Linux服务器服务管理Web工具

## 项目简介

这是一个用于管理远程Linux服务器上各种服务的Web工具。通过SSH连接到目标服务器，可以监控服务状态、执行服务控制操作（启动、停止、重启）以及编辑配置文件。该工具提供了直观的用户界面，使得服务器管理变得更加简单和高效。

## 项目概述

这是一个用于管理远程Linux服务器上各种服务的Web工具。通过SSH连接到目标服务器，可以监控服务状态、执行服务控制操作（启动、停止、重启）以及编辑配置文件。

## 核心功能

### 1. 服务器连接管理
- 多服务器配置存储和切换
- SSH连接状态实时显示
- 连接参数表单（IP、端口、用户名、认证方式）

### 2. 服务状态监控面板
- 实时显示服务状态（sie, vss, nginx/nginxd, lkdc等）
- 状态自动刷新
- 服务日志实时监控和错误检测

### 3. 独立服务操作模块
每个服务包含：
- 服务状态指示器（运行/停止/未知）
- 启动按钮（service service_name start）
- 停止按钮（service service_name stop） 
- 重启按钮（service service_name restart）
- 配置管理入口（sie/vss/nginx等服务）

### 4. 配置文件编辑器
- 文件树导航
- 语法高亮代码编辑器
- 保存时自动备份（原文件名.backup_YYYYMMDD_HHMMSS）
- 文件内容对比功能
- 备份文件恢复功能

## 技术栈

- 后端：Python Flask
- 前端：HTML/CSS/JavaScript + Bootstrap 5
- SSH库：Paramiko
- 代码编辑器：Monaco Editor
- 部署：Docker容器化
- 数据存储：JSON文件

## 安全特性

- SSH密码加密存储
- 输入参数验证
- 文件路径安全限制
- 会话超时管理
- 用户身份验证

## 部署方式

### 本地运行
```bash
# 克隆项目
git clone <项目地址>

# 进入项目目录
cd service_config

# 创建虚拟环境（可选但推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或者在Windows上
# venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行应用
python app.py
```

### Docker运行
```bash
# 构建并启动容器
docker-compose up --build

# 后台运行
docker-compose up -d --build
```

访问 http://localhost:5000 查看应用界面。

## 项目结构

```
.
├── app.py              # 应用入口
├── models.py           # 数据模型
├── routes.py           # 路由和业务逻辑
├── requirements.txt    # 项目依赖
├── README.md           # 项目说明文档
├── Dockerfile          # Docker配置
├── docker-compose.yml  # Docker Compose配置
├── data/               # 数据存储目录
│   ├── users.json      # 用户数据
│   ├── sessions.json   # 会话数据
│   └── servers_*.json  # 服务器配置数据
├── templates/          # HTML模板
│   ├── index.html      # 主界面
│   └── login.html      # 登录界面
└── static/             # 静态资源（目前为空）
```

## 使用说明

1. 启动应用后，访问 `http://localhost:5000`
2. 注册新账户或使用已有账户登录
3. 添加服务器信息（IP地址、端口、用户名、密码）
4. 连接到服务器
5. 查看服务状态并进行管理操作
6. 编辑配置文件并保存

## 注意事项

- 请确保服务器开启了SSH服务并允许相应用户登录
- 服务管理操作需要相应权限，可能需要sudo密码
- 配置文件编辑后会自动备份，可通过备份历史恢复