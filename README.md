# 🖥️ Linux Service Manager

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 一个现代化的 Linux 远程服务器管理 Web 平台，提供服务监控、配置管理、文件操作等全方位管理功能

## 📖 项目简介

Linux Service Manager 是一个基于 Python Flask 框架开发的 Web 应用程序，专为简化 Linux 服务器管理而设计。通过直观的 Web 界面，您可以轻松管理多台远程服务器，监控服务状态，编辑配置文件，执行服务控制操作，以及进行文件管理。

### ✨ 主要特性

- 🔐 **安全的用户认证** - 支持多用户注册登录，密码加密存储
- 🖥️ **多服务器管理** - 同时管理多台服务器，快速切换
- 📊 **实时服务监控** - 可视化显示服务运行状态
- 📝 **在线配置编辑** - Monaco 编辑器，语法高亮，自动备份
- 📂 **SFTP 文件管理** - 完整的远程文件浏览、上传、下载、编辑功能
- 🔍 **日志实时监控** - 自动检测错误日志，服务启动状态追踪
- 🔄 **服务控制** - 一键启动、停止、重启服务
- 🔌 **连接测试** - 添加服务器前测试 SSH 连接
- 💾 **自动备份** - 配置文件修改自动备份，支持历史版本对比和恢复
- 🎨 **现代化 UI** - 基于 Bootstrap 5，响应式设计

## 🎯 适用场景

- 开发团队需要管理多台测试/生产服务器
- 运维人员需要快速查看和管理服务状态
- 需要频繁修改服务器配置文件
- 需要实时监控服务日志和错误信息
- 需要通过 Web 界面进行文件管理

## 🚀 快速开始

### 前置要求

- Python 3.8 或更高版本
- 目标 Linux 服务器需开启 SSH 服务
- 建议：Docker（可选，用于容器化部署）

### 方式一：本地运行

1. **克隆项目**
```bash
git clone <项目地址>
cd service_config_V2
```

2. **创建虚拟环境（推荐）**
```bash
# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **运行应用**
```bash
python app.py
```

5. **访问应用**
打开浏览器访问：`http://localhost:5000`

### 方式二：Docker 运行

```bash
# 构建并启动容器
docker-compose up --build

# 后台运行
docker-compose up -d --build

# 停止容器
docker-compose down
```

访问：`http://localhost:5000`

## 📁 项目结构

```
service_config_V2/
├── app.py                          # Flask 应用入口
├── routes.py                       # API 路由和业务逻辑（核心）
├── models.py                       # 用户和会话管理模型
├── utils.py                        # 工具函数（SSH、文件操作等）
├── requirements.txt                # Python 依赖包
├── Dockerfile                      # Docker 镜像配置
├── docker-compose.yml              # Docker Compose 配置
│
├── data/                           # 数据存储目录
│   ├── users.json                  # 用户数据
│   ├── sessions.json               # 会话数据
│   └── servers_<user_id>.json      # 各用户的服务器配置
│
├── templates/                      # HTML 模板
│   ├── index.html                  # 主界面（服务管理）
│   ├── login.html                  # 登录/注册页面
│   ├── sftp.html                   # SFTP 文件管理页面
│   └── base.html                   # 基础模板
│
├── static/                         # 静态资源
│   └── favicon.ico                 # 网站图标
│
└── docs/                           # 文档（可选）
    ├── TEST_CONNECTION_DEMO.md     # 测试连接功能说明
    └── TEST_CONNECTION_IMPLEMENTATION.md  # 实现文档
```

## 🔧 核心功能详解

### 1. 服务器管理

#### 添加服务器
- 填写服务器名称、IP地址、SSH端口、用户名
- 支持密码认证和密钥认证
- **测试连接功能**：添加前可测试连接是否正常

#### 编辑服务器
- 修改服务器配置信息
- 支持更新密码（留空则保持原密码）
- 同样支持测试连接

#### 删除服务器
- 删除服务器配置
- 自动关闭相关 SSH 连接和日志监视器

### 2. 服务监控与控制

支持的服务类型（可自定义）：
- 流媒体服务（sie）
- 业务服务（vss）
- Nginx/Nginxd
- Logstash/LKDC
- 文件服务
- 消息推送服务
- 等...

每个服务卡片提供：
- 🟢 **状态指示器**：运行中 / 已停止 / 未知
- ▶️ **启动按钮**：启动服务
- ⏹️ **停止按钮**：停止服务
- 🔄 **重启按钮**：重启服务
- ⚙️ **配置按钮**：打开配置文件编辑

### 3. 配置文件管理

#### 文件树导航
- 左侧面板显示服务配置文件树
- 支持目录展开折叠
- 文件图标区分

#### Monaco 代码编辑器
- 语法高亮（支持多种配置文件格式）
- 代码自动补全
- 行号显示
- 迷你地图
- 实时保存状态提示

#### 文件操作
- **保存更改**：自动创建备份（格式：`filename.backup_YYYYMMDD_HHMMSS`）
- **对比差异**：对比本地编辑内容与服务器文件
- **历史版本**：查看备份历史，支持恢复
- **刷新**：重新加载服务器文件

### 4. SFTP 文件管理

完整的远程文件管理功能：
- 📂 **目录浏览**：可视化目录树
- ⬆️ **文件上传**：支持拖拽上传
- ⬇️ **文件下载**：批量下载
- ✏️ **在线编辑**：支持文本文件在线编辑
- 🗑️ **删除文件/目录**：支持递归删除
- 📝 **重命名**：文件和目录重命名
- ➕ **新建**：创建文件和目录
- 🔒 **权限管理**：修改文件权限（chmod）
- 📊 **文件信息**：显示大小、修改时间、权限

### 5. 日志监控

#### 错误日志监控
- 实时监控服务日志文件
- 自定义错误匹配规则（关键字匹配）
- 自动显示错误日志和时间戳
- 支持清空日志记录

#### 服务启动检测
- 自动检测服务启动状态
- 多日志文件并发监控
- 启动超时检测（可配置）
- 启动成功/失败通知

#### 操作记录
- 记录所有用户操作
- 时间戳和操作详情
- 支持手动清空

## 🛡️ 安全特性

### 认证与授权
- ✅ SHA256 密码哈希存储
- ✅ Session 会话管理（24小时过期）
- ✅ 登录验证装饰器保护所有API
- ✅ 用户数据隔离（每个用户独立的服务器配置）

### SSH 连接安全
- ✅ 使用 Paramiko 库安全连接
- ✅ 支持密钥认证
- ✅ 连接超时控制（8秒）
- ✅ 自动清理连接

### 文件操作安全
- ✅ 路径验证，防止目录穿越
- ✅ 文件自动备份
- ✅ 操作权限验证
- ✅ 输入参数验证

## 🔌 API 接口

### 用户认证
- `POST /auth/register` - 用户注册
- `POST /auth/login` - 用户登录
- `POST /auth/logout` - 用户登出
- `GET /auth/status` - 检查登录状态

### 服务器管理
- `GET /servers` - 获取服务器列表
- `POST /servers` - 添加服务器
- `PUT /servers/<id>` - 编辑服务器
- `DELETE /servers/<id>` - 删除服务器
- `POST /servers/<id>/connect` - 连接服务器
- `POST /servers/<id>/test_connection` - 测试连接 ⭐

### 服务控制
- `GET /services/status` - 获取服务状态列表
- `POST /services/<name>/start` - 启动服务
- `POST /services/<name>/stop` - 停止服务
- `POST /services/<name>/restart` - 重启服务

### 配置文件
- `GET /config/files` - 获取配置文件列表
- `GET /config/file_content` - 读取文件内容
- `POST /config/save_file` - 保存文件
- `GET /config/compare` - 对比文件差异
- `GET /config/backups` - 获取备份列表
- `POST /config/restore_backup` - 恢复备份

### SFTP 操作
- `GET /api/sftp/list` - 列出目录内容
- `POST /api/sftp/upload` - 上传文件
- `GET /api/sftp/download` - 下载文件
- `POST /api/sftp/delete` - 删除文件/目录
- `POST /api/sftp/rename` - 重命名
- `POST /api/sftp/mkdir` - 创建目录
- `POST /api/sftp/chmod` - 修改权限
- `GET /api/sftp/read_file` - 读取文件内容
- `POST /api/sftp/write_file` - 写入文件内容

### 日志监控
- `GET /errors/detected` - 获取检测到的错误日志
- `POST /errors/clear` - 清空错误日志
- `GET /errors/patterns` - 获取错误匹配规则
- `POST /errors/patterns` - 添加错误匹配规则
- `DELETE /errors/patterns/<id>` - 删除错误匹配规则

## 🎨 技术栈

### 后端
- **框架**：Flask 2.3.3
- **SSH/SFTP**：Paramiko 3.4.0+
- **加密**：Cryptography 44.0.1+
- **会话管理**：Flask Session
- **数据存储**：JSON 文件

### 前端
- **UI 框架**：Bootstrap 5.3.2
- **图标库**：Font Awesome 6.4.0
- **代码编辑器**：Monaco Editor 0.34.1
- **字体**：Inter, JetBrains Mono
- **差异对比**：Diff.js 5.0.0

### 开发工具
- **容器化**：Docker & Docker Compose
- **环境管理**：Python venv
- **版本控制**：Git

## 📝 使用指南

### 第一次使用

1. **注册账户**
   - 访问登录页面
   - 点击"注册新账户"
   - 输入用户名和密码（至少6位）

2. **添加服务器**
   - 登录后点击顶部"添加服务器"按钮（+）
   - 填写服务器信息
   - 点击"测试连接"确保连接正常
   - 点击"确认添加"保存

3. **连接服务器**
   - 在顶部下拉框选择服务器
   - 点击"连接"按钮
   - 等待连接成功（显示绿色"已连接"标识）

4. **管理服务**
   - 左侧面板查看所有服务状态
   - 点击启动/停止/重启按钮控制服务
   - 点击"配置"按钮编辑配置文件

5. **文件管理**
   - 点击"文件管理"按钮打开SFTP
   - 浏览、上传、下载、编辑文件
   - 修改文件权限

### 配置服务列表

在 `routes.py` 中的 `services` 列表可以自定义监控的服务：

```python
services = [
    {
        "name": "your_service",              # systemd 服务名
        "display_name": "您的服务",           # 显示名称
        "config_path": "/path/to/config/",   # 配置文件目录
        "log_paths": [                       # 日志文件路径（可选）
            "/path/to/log1.log",
            "/path/to/log2.log"
        ],
        "startup_check": {                   # 启动检测配置（可选）
            "enabled": True,
            "keyword": "启动成功",            # 启动成功的关键字
            "required_count": 1,             # 需要检测到的日志文件数量
            "timeout": 30                    # 超时时间（秒）
        },
        "has_config": True                   # 是否有配置文件
    }
]
```

## ⚙️ 配置说明

### 环境变量

创建 `.env` 文件（可选）：
```env
FLASK_SECRET_KEY=your-secret-key-here
FLASK_DEBUG=True
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

### 生产环境部署

1. 修改 `app.py` 中的 `secret_key`
2. 设置 `debug=False`
3. 使用 WSGI 服务器（如 Gunicorn）
4. 配置反向代理（如 Nginx）
5. 启用 HTTPS

示例 Gunicorn 启动：
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:create_app()
```

## 🐛 常见问题

### 1. 无法连接服务器
- 检查服务器 SSH 服务是否开启
- 确认 IP 地址和端口是否正确
- 验证用户名和密码
- 检查防火墙设置

### 2. 服务控制失败
- 确认 SSH 用户是否有管理服务权限
- 某些操作可能需要 sudo 权限
- 检查服务名称是否正确

### 3. 文件无法保存
- 检查 SSH 用户对目标文件是否有写权限
- 确认文件路径是否正确
- 查看操作日志中的错误信息

### 4. Docker 容器无法启动
- 检查端口 5000 是否被占用
- 查看 Docker 日志：`docker-compose logs`

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📮 联系方式

如有问题或建议，欢迎联系项目维护者。

## 🙏 致谢

- [Flask](https://flask.palletsprojects.com/) - Web 框架
- [Paramiko](https://www.paramiko.org/) - SSH 库
- [Monaco Editor](https://microsoft.github.io/monaco-editor/) - 代码编辑器
- [Bootstrap](https://getbootstrap.com/) - UI 框架
- [Font Awesome](https://fontawesome.com/) - 图标库

---

⭐ 如果这个项目对您有帮助，欢迎给个 Star！