# 📦 JavaScript 模块快速参考

## 🚀 快速引入

```html
<!-- 在 index.html 的 </body> 之前按顺序添加 -->
<script src="/static/js/core-utils.js"></script>
<script src="/static/js/log-manager.js"></script>
<script src="/static/js/server-manager.js"></script>
<script src="/static/js/service-manager.js"></script>
<script src="/static/js/config-manager.js"></script>
<script src="/static/js/connection-tester.js"></script>
<script src="/static/js/app.js"></script>
```

---

## 📋 模块 API 速查

### CoreUtils
```javascript
const { DOMCache, API, showToast, escapeHtml } = window.CoreUtils;

// DOM 缓存
DOMCache.init();
DOMCache.serverSelector.value;

// API 请求
await API.get('/servers');
await API.post('/servers', data);
await API.put('/servers/1', data);
await API.delete('/servers/1');

// 通知
showToast('标题', '消息', 'success');  // success, error, warning, info

// HTML 转义
const safe = escapeHtml(userInput);
```

### ServerManager
```javascript
// 服务器操作
await ServerManager.loadServers();
await ServerManager.addServer();
await ServerManager.connectToServer();
await ServerManager.deleteSelectedServer();
ServerManager.handleServerSelection();

// 获取数据
const servers = ServerManager.getCurrentServers();
```

### ServiceManager
```javascript
// 服务操作
await ServiceManager.loadServices();
await ServiceManager.refreshServiceStatus();
await ServiceManager.serviceAction('nginx', 'start');
ServiceManager.clearServices();

// 获取数据
const services = ServiceManager.getServices();
```

### ConfigManager
```javascript
// 文件操作
ConfigManager.openConfig('nginx');
await ConfigManager.loadFileTree();
await ConfigManager.loadFileContent(path);
await ConfigManager.saveCurrentFile();
await ConfigManager.deleteConfigFile(path, event);

// 目录操作
await ConfigManager.browseDirectory(path);
ConfigManager.browseUpDirectory(path);

// 获取数据
const filePath = ConfigManager.getCurrentFilePath();
```

### LogManager
```javascript
// 操作日志
LogManager.loadOperationLog();
LogManager.addOperationLog('操作', '详情');
LogManager.clearOperationLog();

// 服务日志
LogManager.updateServiceLogs('nginx', errors);
LogManager.clearServiceLogs();
```

### ConnectionTester
```javascript
// 测试连接
await ConnectionTester.testAddConnection();
await ConnectionTester.testEditConnection();
```

### App
```javascript
// 应用控制
await App.init();
App.toggleSftpView();
App.logout();

// 获取编辑器
const editor = App.getEditor();
```

---

## 🔧 HTML 中使用

### 方法 1: 完整路径
```html
<button onclick="window.ServerManager.addServer()">添加</button>
```

### 方法 2: 全局别名
```html
<script>
// 定义全局别名
const addServer = () => window.ServerManager.addServer();
const loadServers = () => window.ServerManager.loadServers();
</script>

<button onclick="addServer()">添加</button>
```

---

## ⚡ 常用操作

### 初始化
```javascript
// 自动执行（在 app.js 中）
window.addEventListener('DOMContentLoaded', () => {
    App.init();
});
```

### 加载服务器列表
```javascript
await ServerManager.loadServers();
```

### 连接服务器并加载服务
```javascript
await ServerManager.connectToServer();
// 自动调用 ServiceManager.loadServices()
```

### 打开配置文件
```javascript
ConfigManager.openConfig('nginx');
// 自动加载文件树
```

### 保存文件
```javascript
await ConfigManager.saveCurrentFile();
// 自动备份和记录日志
```

### 添加日志
```javascript
LogManager.addOperationLog('操作名称', '操作详情');
```

---

## 📊 模块大小

| 模块 | 行数 | 大小 | 功能数 |
|------|------|------|--------|
| core-utils.js | 180 | 6KB | 4 |
| server-manager.js | 240 | 9KB | 9 |
| service-manager.js | 180 | 7KB | 4 |
| config-manager.js | 350 | 13KB | 9 |
| log-manager.js | 140 | 5KB | 5 |
| connection-tester.js | 140 | 5KB | 2 |
| app.js | 120 | 4KB | 4 |
| **总计** | **1,350** | **49KB** | **37** |

---

## 🔍 错误排查

### 模块未定义
```javascript
// 错误: CoreUtils is not defined
// 原因: 模块加载顺序错误或未加载
// 解决: 检查 HTML 中的 script 标签顺序
```

### 函数未定义
```javascript
// 错误: addServer is not defined
// 原因: 使用了未定义的全局别名
// 解决: 使用完整路径 window.ServerManager.addServer()
```

### DOM 元素为 null
```javascript
// 错误: Cannot read property 'value' of null
// 原因: DOMCache 未初始化
// 解决: 确保调用了 DOMCache.init()
```

---

**版本**: v3.0  
**更新时间**: 2025-12-04 16:00
