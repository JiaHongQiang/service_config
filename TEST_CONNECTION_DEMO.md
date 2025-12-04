# 测试连接功能说明

## 后端API

后端已经实现了测试连接的API（在routes.py第543-578行）：

```python
@api_bp.route('/servers/<server_id>/test_connection', methods=['POST'])
@login_required
def test_server_connection(server_id):
```

## 使用方法

### 方式1：直接在添加完服务器后测试（推荐）

在addServer函数中，添加服务器成功后，可以选择测试连接：

```javascript
async function addServer() {
    const data = {
        id: Date.now().toString(),
        name: document.getElementById('serverName').value,
        host: document.getElementById('serverHost').value,
        port: parseInt(document.getElementById('serverPort').value),
        username: document.getElementById('serverUsername').value,
        auth_method: document.getElementById('authMethod').value,
        password: document.getElementById('serverPassword').value
    };

    try {
        // 添加服务器
        const res = await fetch('/servers', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(data) 
        });
        
        if (res.ok) {
            const newServer = await res.json();
            showToast('✓ 添加成功', data.name, 'success');
            
            // 询问是否测试连接
            if (confirm('服务器添加成功！是否测试连接？')) {
                await testConnection(newServer.id);
            }
            
            bootstrap.Modal.getInstance(document.getElementById('addServerModal')).hide();
            loadServers();
        }
    } catch (e) { 
        showToast('✗ 错误', '网络异常', 'error'); 
    }
}

async function testConnection(serverId) {
    try {
        showToast('测试中...', '正在连接服务器', 'info');
        
        const res = await fetch(`/servers/${serverId}/test_connection`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (res.ok) {
            const result = await res.json();
            showToast('✓ 连接成功', result.message, 'success');
        } else {
            const err = await res.json();
            showToast('✗ 连接失败', err.error, 'error');
        }
    } catch (e) {
        showToast('✗ 错误', '测试连接失败', 'error');
    }
}
```

### 方式2：在模态框中添加测试按钮

如果要在添加服务器的模态框footer中添加"测试连接"按钮（需要找到正确的HTML模板文件）：

```html
<div class=\"modal-footer bg-light d-flex justify-content-between\">
    <button type=\"button\" class=\"btn btn-outline-info\" id=\"testAddConnectionBtn\" onclick=\"testCurrentConnection()\">
        <i class=\"fas fa-plug me-1\"></i> 测试连接
    </button>
    <div>
        <button type=\"button\" class=\"btn btn-light text-secondary\" data-bs-dismiss=\"modal\">取消</button>
        <button type=\"button\" class=\"btn btn-primary px-4\" id=\"submitAddServer\">确认添加</button>
    </div>
</div>
```

对应的JavaScript函数：

```javascript
async function testCurrentConnection() {
    // 获取表单数据（无需保存到服务器）
    const data = {
        id: 'temp-' + Date.now().toString(), // 临时ID
        name: document.getElementById('serverName').value,
        host: document.getElementById('serverHost').value,
        port: parseInt(document.getElementById('serverPort').value),
        username: document.getElementById('serverUsername').value,
        auth_method: document.getElementById('authMethod').value,
        password: document.getElementById('serverPassword').value
    };
    
    // 验证必填字段
    if (!data.host || !data.username || !data.password) {
        showToast('⚠ 提示', '请先填写完整的服务器信息', 'warning');
        return;
    }
    
    try {
        // 先临时添加服务器（用于测试）
        const addRes = await fetch('/servers', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(data) 
        });
        
        if (addRes.ok) {
            const server = await addRes.json();
            
            // 测试连接
            showToast('测试中...', '正在测试连接', 'info');
            const testRes = await fetch(`/servers/${server.id}/test_connection`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            // 删除临时服务器
            await fetch(`/servers/${server.id}`, { method: 'DELETE' });
            
            // 显示测试结果
            if (testRes.ok) {
                const result = await testRes.json();
                showToast('✓ 连接成功', result.message, 'success', 5000);
            } else {
                const err = await testRes.json();
                showToast('✗ 连接失败', err.error, 'error', 5000);
            }
        }
    } catch (e) {
        console.error(e);
        showToast('✗ 错误', '测试连接失败', 'error');
    }
}
```

## API端点说明

**端点**: `POST /servers/<server_id>/test_connection`

**说明**: 测试指定服务器的SSH连接

**响应**:
- 成功: `{\"message\": \"连接成功: 服务器名称 (IP地址)\"}`
- 失败: `{\"error\": \"错误信息\"}`

## 注意事项

1. 测试连接API会创建临时SSH连接，测试后自动关闭
2. 不会影响现有的SSH连接
3. 超时时间为8秒
4. 需要在登录状态下使用（有@login_required装饰器）
