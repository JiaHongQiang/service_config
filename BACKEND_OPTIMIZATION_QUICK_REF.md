# 🔧 后端优化快速参考

## ⚡ 快速开始

### 1. 异常处理
```python
from exceptions import handle_exceptions, ValidationError, validate_required_fields

@api_bp.route('/api/endpoint', methods=['POST'])
@handle_exceptions  # ← 添加这个装饰器
def my_route():
    data = request.json
    validate_required_fields(data, ['field1', 'field2'])  # ← 简单验证
    
    if error_condition:
        raise ValidationError("错误信息")  # ← 抛出异常
    
    return jsonify({"success": True})
```

### 2. JSON 文件管理
```python
from json_manager import JSONFileManager

# 创建管理器
manager = JSONFileManager('data/config.json', auto_backup=True)

# 读取
data = manager.read(default={})

# 写入（自动备份）
manager.write(data)

# 原子性更新
manager.update(lambda d: {**d, 'new_key': 'value'}, default={})
```

### 3. 配置管理
```python
from config_manager import app_config, error_patterns_config

# 应用配置
secret = app_config.secret_key
app_config.port = 8000

# 错误模式
patterns = error_patterns_config.get_patterns()
error_patterns_config.add_pattern('ERROR', '错误')
```

---

## 📊 主要模块对比

| 模块 | 功能 | 主要类/函数 | 使用场景 |
|------|------|-------------|----------|
| **exceptions.py** | 统一异常处理 | `@handle_exceptions`<br>`ValidationError`<br>`validate_required_fields` | 所有 API 路由<br>参数验证 |
| **json_manager.py** | JSON 文件管理 | `JSONFileManager`<br>`.read()`<br>`.write()`<br>`.update()` | 配置文件读写<br>数据持久化 |
| **config_manager.py** | 配置管理 | `ConfigManager`<br>`app_config`<br>`error_patterns_config` | 应用配置<br>错误模式配置 |

---

## 🎯 异常处理速查

### 异常类

| 异常类 | HTTP 状态码 | 使用场景 |
|--------|-------------|----------|
| `ValidationError` | 400 | 参数验证失败 |
| `AuthenticationError` | 401 | 认证失败 |
| `PermissionError` | 403 | 权限不足 |
| `ResourceNotFoundError` | 404 | 资源不存在 |
| `ServerConnectionError` | 500 | SSH/网络连接错误 |
| `FileOperationError` | 500 | 文件操作错误 |

### 验证函数

```python
# 验证必需字段
validate_required_fields(data, ['name', 'host', 'port'])

# 验证不为空
validate_not_empty(value, '字段名')

# 验证服务器ID
validate_server_id(server_id)
```

### 装饰器

```python
@handle_exceptions        # 通用异常处理
@handle_ssh_exceptions    # SSH 专用异常处理
```

---

## 💾 JSON 文件管理速查

### 基本操作

```python
manager = JSONFileManager('path/to/file.json', auto_backup=True)

# 读取
data = manager.read(default=[])        # 返回默认值如果文件不存在
data = manager.read()                  # 返回 None 如果文件不存在

# 写入
manager.write(data)                    # 自动备份
manager.write(data, create_backup=False)  # 不备份

# 原子性更新
def updater(current_data):
    current_data.append(new_item)
    return current_data

manager.update(updater, default=[])
```

### 备份管理

```python
# 创建备份
backup_path = manager.create_backup()

# 列出备份
backups = manager.list_backups()
# [{'filename': '...', 'path': '...', 'mtime': ..., 'size': ...}, ...]

# 恢复备份
manager.restore_from_backup(backups[0]['path'])

# 清理旧备份（保留最新 10 个）
manager.cleanup_old_backups(keep_count=10)

# 检查文件是否存在
if manager.exists():
    # ...

# 删除文件（会先备份）
manager.delete()
```

---

## ⚙️ 配置管理速查

### 应用配置

```python
from config_manager import app_config

# 读取
secret = app_config.secret_key     # str
debug = app_config.debug           # bool
host = app_config.host             # str
port = app_config.port             # int
timeout = app_config.ssh_timeout   # int
max_backups = app_config.max_backup_count  # int

# 设置
app_config.secret_key = "new-key"
app_config.debug = True
app_config.port = 8000

# 批量操作
all_config = app_config.get_all()
app_config.update_all({'debug': False, 'port': 5000})
```

### 错误模式配置

```python
from config_manager import error_patterns_config

# 获取所有
patterns = error_patterns_config.get_patterns()

# 添加
error_patterns_config.add_pattern('ERROR', '错误')

# 删除
error_patterns_config.remove_pattern('ERROR')

# 批量更新
new_patterns = [
    {'keyword': 'ERROR', 'name': '错误'},
    {'keyword': 'WARN', 'name': '警告'}
]
error_patterns_config.update_patterns(new_patterns)
```

### 通用配置管理

```python
from config_manager import config_manager

# 获取配置
value = config_manager.get('config_name', 'key', default='default')
all_values = config_manager.get('config_name')

# 设置配置
config_manager.set('config_name', 'key', 'value')

# 批量更新
config_manager.update('config_name', {'key1': 'val1', 'key2': 'val2'})

# 删除配置项
config_manager.delete('config_name', 'key')

# 重置配置
config_manager.reset('config_name')

# 备份配置
backup_path = config_manager.backup('config_name')

# 恢复配置
config_manager.restore('config_name', backup_path)

# 列出备份
backups = config_manager.list_backups('config_name')
```

---

## 🔄 常见使用模式

### 模式 1: API 路由标准模板

```python
from exceptions import handle_exceptions, ValidationError, validate_required_fields

@api_bp.route('/api/resource', methods=['POST'])
@login_required
@handle_exceptions
def create_resource():
    # 1. 获取数据
    data = request.json
    
    # 2. 验证数据
    validate_required_fields(data, ['name', 'value'])
    
    # 3. 业务逻辑
    if exists(data['name']):
        raise ValidationError("资源已存在")
    
    # 4. 保存数据
    save_resource(data)
    
    # 5. 返回结果
    return jsonify(data), 201
```

### 模式 2: JSON 文件原子性更新

```python
from json_manager import JSONFileManager

def add_item_to_list(item):
    manager = JSONFileManager('data/items.json', auto_backup=True)
    
    def updater(items):
        if items is None:
            items = []
        
        # 检查是否已存在
        if any(i['id'] == item['id'] for i in items):
            raise ValidationError("项目已存在")
        
        items.append(item)
        return items
    
    return manager.update(updater, default=[])
```

### 模式 3: 配置驱动的应用初始化

```python
from config_manager import app_config

def create_app():
    app = Flask(__name__)
    
    # 所有配置从配置管理器读取
    app.secret_key = app_config.secret_key
    app.config['DEBUG'] = app_config.debug
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    # ...
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(
        debug=app_config.debug,
        host=app_config.host,
        port=app_config.port
    )
```

---

## 🚀 迁移步骤速查

### 步骤 1: 添加装饰器
```python
# 在函数定义上方添加
@handle_exceptions
```

### 步骤 2: 替换异常处理
```python
# ❌ 旧代码
try:
    # ...
    if error:
        return jsonify({"error": "错误"}), 400
except Exception as e:
    return jsonify({"error": str(e)}), 500

# ✅ 新代码
# ...
if error:
    raise ValidationError("错误")
# 异常会自动处理
```

### 步骤 3: 替换验证逻辑
```python
# ❌ 旧代码
if not data.get('name'):
    return jsonify({"error": "缺少名称"}), 400
if not data.get('host'):
    return jsonify({"error": "缺少主机"}), 400

# ✅ 新代码
validate_required_fields(data, ['name', 'host'])
```

### 步骤 4: 使用 JSON 管理器
```python
# ❌ 旧代码
with open('file.json', 'r') as f:
    data = json.load(f)

# ✅ 新代码
manager = JSONFileManager('file.json', auto_backup=True)
data = manager.read(default={})
```

### 步骤 5: 使用配置管理器
```python
# ❌ 旧代码
app.secret_key = 'hardcoded-key'

# ✅ 新代码
from config_manager import app_config
app.secret_key = app_config.secret_key
```

---

## ⚠️ 常见问题

### Q1: 装饰器顺序？
```python
@api_bp.route('/api/endpoint')
@login_required         # 1. 认证
@handle_exceptions      # 2. 异常处理
@handle_ssh_exceptions  # 3. SSH 异常（如果需要）
def my_function():
    pass
```

### Q2: 如何禁用自动备份？
```python
manager = JSONFileManager('file.json', auto_backup=False)
# 或
manager.write(data, create_backup=False)
```

### Q3: 如何自定义备份目录？
```python
manager = JSONFileManager(
    'data/config.json',
    auto_backup=True,
    backup_dir='data/custom_backup'
)
```

### Q4: 如何在调试时显示详细错误？
```python
from config_manager import app_config
app_config.debug = True  # 会在错误响应中包含详细信息
```

---

## 📝 检查清单

### 代码迁移检查
- [ ] 所有路由都添加了 `@handle_exceptions`
- [ ] 所有参数验证都使用了 `validate_*` 函数
- [ ] 所有文件操作都使用了 `JSONFileManager`
- [ ] 所有配置值都从 `config_manager` 读取
- [ ] 删除了所有重复的异常处理代码
- [ ] 删除了所有硬编码的配置值

### 测试检查
- [ ] 测试正常请求
- [ ] 测试参数验证错误
- [ ] 测试资源不存在错误
- [ ] 测试认证错误
- [ ] 测试文件读写
- [ ] 测试配置读写
- [ ] 测试备份和恢复

### 文档检查
- [ ] 更新 API 文档
- [ ] 更新配置说明
- [ ] 添加备份恢复说明

---

**快速参考版本**: v1.0  
**最后更新**: 2025-12-04 15:40
