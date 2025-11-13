# Linux Service Manager

基于Python的Linux服务器服务管理Web工具

## 项目概述

这是一个用于管理远程Linux服务器上各种服务的Web工具。通过SSH连接到目标服务器，可以监控服务状态、执行服务控制操作（启动、停止、重启）以及编辑配置文件。

## 核心功能

### 1. 服务器连接管理
- 多服务器配置存储和切换
- SSH连接状态实时显示
- 连接参数表单（IP、端口、用户名、认证方式）

### 2. 服务状态监控面板
- 实时显示服务状态（sie, vss, nginx/nginxd, lkdc）
- 状态自动刷新（30秒间隔）
- 服务日志查看功能

### 3. 独立服务操作模块
每个服务包含：
- 服务状态指示器（运行/停止/未知）
- 启动按钮（service service_name start）
- 停止按钮（service service_name stop） 
- 重启按钮（service service_name restart）
- 配置管理入口（sie/vss/nginx服务）

### 4. 配置文件编辑器
- 文件树导航（sie:/home/hy_media_server/conf/, nginx:/opt/nginx/conf/）
- 语法高亮代码编辑器
- 保存时自动备份（原文件名.backup_YYYYMMDD_HHMMSS）
- 文件内容对比功能

## 技术栈

- 后端：Python Flask
- 前端：HTML/CSS/JavaScript + Bootstrap 5
- SSH库：Paramiko
- 代码编辑器：Monaco Editor
- 部署：Docker容器化

## 安全要求

- SSH密码加密存储
- 输入参数验证
- 文件路径安全限制
- 会话超时管理

## 部署方式

### 本地运行
```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python app.py
```

### Docker运行
```bash
docker-compose up --build
```

访问 http://localhost:5000 查看应用界面。