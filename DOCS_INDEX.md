# 📚 文档索引

欢迎使用 Linux Service Manager！本索引将帮助您快速找到所需的文档。

## 📖 主要文档

### 🌟 [README.md](README.md) - **必读**
**适合**: 所有用户
**内容**: 
- 项目简介和特性
- 快速开始指南
- 完整功能说明
- API 接口文档
- 使用指南
- 常见问题解答

**推荐阅读顺序**: 第一个阅读

### 🎯 [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)
**适合**: 开发者、技术人员
**内容**:
- 项目架构设计
- 核心工作流程
- 模块详细说明
- 数据存储设计
- 技术亮点
- 开发建议

**推荐阅读顺序**: 第二个阅读（深入了解项目）

## 🔧 功能文档

### ⚡ [TEST_CONNECTION_DEMO.md](TEST_CONNECTION_DEMO.md)
**适合**: 所有用户
**内容**:
- 测试连接功能说明
- 使用方法和代码示例
- API 端点说明
- 注意事项

**何时阅读**: 需要使用测试连接功能时

### 📝 [TEST_CONNECTION_IMPLEMENTATION.md](TEST_CONNECTION_IMPLEMENTATION.md)
**适合**: 开发者
**内容**:
- 测试连接功能的实现细节
- 代码修改说明
- 技术实现方案
- 用户体验设计

**何时阅读**: 需要了解测试连接功能的实现时

### 🚀 [OPTIMIZATION_REPORT.md](OPTIMIZATION_REPORT.md)
**适合**: 开发者、技术人员
**内容**:
- 三大性能优化说明
- 合并测试连接函数（减少150行代码）
- 统一 API 请求模式
- DOM 元素缓存
- 代码减少统计
- 性能提升数据

**何时阅读**: 需要了解项目优化策略和性能提升时

### 💡 [OPTIMIZATION_EXAMPLES.js](OPTIMIZATION_EXAMPLES.js)
**适合**: 开发者
**内容**:
- 优化前后代码对比
- DOMCache 使用示例
- API 辅助器使用示例
- 批量替换模式

**何时阅读**: 需要应用优化模式到其他函数时

### ⚙️ [DOM_CACHE_INIT.js](DOM_CACHE_INIT.js)
**适合**: 开发者
**内容**:
- DOMCache 初始化脚本
- 验证函数
- 使用说明

**何时阅读**: 需要初始化 DOM 缓存时

---

## 🐍 后端优化文档

### 🚀 [BACKEND_OPTIMIZATION_GUIDE.md](BACKEND_OPTIMIZATION_GUIDE.md)
**适合**: Python 开发者、后端工程师
**内容**:
- 统一异常处理系统
- JSON 文件管理工具类
- 配置文件管理模块
- 实施步骤和迁移指南
- 优化前后代码对比

**何时阅读**: 需要了解后端优化策略时

### ⚡ [BACKEND_OPTIMIZATION_QUICK_REF.md](BACKEND_OPTIMIZATION_QUICK_REF.md)
**适合**: Python 开发者
**内容**:
- 快速使用指南
- API 速查表
- 常见使用模式
- 迁移检查清单

**何时阅读**: 需要快速查阅后端 API 时

### 📦 新增 Python 模块
**适合**: 开发者
**模块**:
- `exceptions.py` - 统一异常处理
- `json_manager.py` - JSON 文件管理
- `config_manager.py` - 配置管理

**何时使用**: 在代码中导入并使用这些模块

---

## 🎨 JavaScript 模块化文档

### 🚀 [JAVASCRIPT_MODULARIZATION_GUIDE.md](JAVASCRIPT_MODULARIZATION_GUIDE.md)
**适合**: JavaScript 开发者
**内容**:
- 模块化架构设计
- 7 个独立模块说明
- 模块依赖关系
- 迁移步骤指南
- 最佳实践

**何时阅读**: 需要了解 JavaScript 模块化重构时

### ⚡ [JAVASCRIPT_MODULES_QUICK_REF.md](JAVASCRIPT_MODULES_QUICK_REF.md)
**适合**: JavaScript 开发者
**内容**:
- 模块 API 速查表
- 常用操作示例
- 错误排查指南
- 快速引入方法

**何时阅读**: 需要快速查阅模块 API 时

### 📦 JavaScript 模块文件
**位置**: `static/js/`
**模块**:
- `core-utils.js` - 核心工具
- `server-manager.js` - 服务器管理
- `service-manager.js` - 服务控制
- `config-manager.js` - 配置文件管理
- `log-manager.js` - 日志管理
- `connection-tester.js` - 连接测试
- `app.js` - 主应用

**何时使用**: 在 HTML 中引入这些模块

## 📋 辅助文档

### 📰 [README_UPDATE_NOTES.md](README_UPDATE_NOTES.md)
**适合**: 项目维护者
**内容**:
- README 文档的更新说明
- 新版文档的改进点
- 文档结构说明

**何时阅读**: 需要了解文档更新历史时

## 🚀 快速导航

### 我是新用户，想快速开始使用
1. 阅读 **[README.md](README.md)** 的"快速开始"部分
2. 按照步骤安装和运行
3. 查看"使用指南"了解基本操作

### 我想深入了解项目技术
1. 先阅读 **[README.md](README.md)** 了解整体
2. 再阅读 **[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)** 了解架构
3. 查看源代码中的注释

### 我想使用测试连接功能
1. 查看 **[TEST_CONNECTION_DEMO.md](TEST_CONNECTION_DEMO.md)** 了解用法
2. 在添加服务器时点击"测试连接"按钮
3. 如果遇到问题，查看 README 的"常见问题"部分

### 我想参与开发
1. 阅读 **[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)** 的"开发建议"部分
2. 了解代码结构和架构设计
3. 查看 **[TEST_CONNECTION_IMPLEMENTATION.md](TEST_CONNECTION_IMPLEMENTATION.md)** 作为实现示例

### 我想了解性能优化
1. 查看 **[OPTIMIZATION_REPORT.md](OPTIMIZATION_REPORT.md)** 了解优化策略
2. 阅读 **[OPTIMIZATION_EXAMPLES.js](OPTIMIZATION_EXAMPLES.js)** 查看代码示例
3. 使用 **[DOM_CACHE_INIT.js](DOM_CACHE_INIT.js)** 初始化 DOM 缓存

### 我想部署到生产环境
1. 阅读 **[README.md](README.md)** 的"配置说明"部分
2. 查看"生产环境部署"建议
3. 确保修改了 secret_key 等安全配置

## 📂 其他资源

### 源代码文件
- `app.py` - Flask 应用入口，有详细注释
- `routes.py` - API 路由和业务逻辑，每个函数都有中文注释
- `models.py` - 用户管理模型，包含完整文档字符串
- `utils.py` - 工具函数集合

### 配置文件
- `requirements.txt` - Python 依赖包列表
- `Dockerfile` - Docker 镜像构建配置
- `docker-compose.yml` - Docker Compose 配置

### 前端模板
- `templates/index.html` - 主界面（包含大量 JavaScript 注释）
- `templates/login.html` - 登录界面
- `templates/sftp.html` - SFTP 文件管理页面

## 🔍 按主题查找

### 用户认证
- **README.md** → "安全特性" → "认证与授权"
- **PROJECT_OVERVIEW.md** → "核心工作流程" → "用户认证流程"
- **models.py** → `UserManager` 类

### 服务器管理
- **README.md** → "核心功能详解" → "服务器管理"
- **TEST_CONNECTION_DEMO.md** → 测试连接功能
- **routes.py** → 服务器管理相关 API

### 服务控制
- **README.md** → "核心功能详解" → "服务监控与控制"
- **PROJECT_OVERVIEW.md** → "核心工作流程" → "服务控制流程"
- **routes.py** → `service_action` 函数

### 配置文件编辑
- **README.md** → "核心功能详解" → "配置文件管理"
- **PROJECT_OVERVIEW.md** → "核心工作流程" → "配置编辑流程"
- **routes.py** → 配置文件相关 API

### SFTP 文件管理
- **README.md** → "核心功能详解" → "SFTP 文件管理"
- **templates/sftp.html** → 完整的 SFTP 实现
- **routes.py** → SFTP API 部分

### 日志监控
- **README.md** → "核心功能详解" → "日志监控"
- **PROJECT_OVERVIEW.md** → "技术亮点" → "实时日志监控"
- **routes.py** → `watch_log` 函数

## 💡 提示

- 📌 所有文档都使用 Markdown 格式，可以在任何 Markdown 阅读器中查看
- 📌 建议使用支持目录的 Markdown 编辑器（如 VS Code、Typora）
- 📌 代码中的注释也是重要的文档来源
- 📌 遇到问题时，先查看 README 的"常见问题"部分

## 🆕 最近更新

- **2023-12-04**: 重写 README.md，新增详细的功能说明和 API 文档
- **2023-12-04**: 创建 PROJECT_OVERVIEW.md，提供架构和技术细节
- **2023-12-04**: 完善测试连接功能文档

---

**文档版本**: 1.0  
**最后更新**: 2023-12-04  
**维护者**: 项目团队

如有文档问题或建议，欢迎提出 Issue！
