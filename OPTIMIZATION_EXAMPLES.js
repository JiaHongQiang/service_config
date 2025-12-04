/**
 * 优化实施示例代码
 * 展示如何应用 DOMCache 和 API 辅助器来优化现有函数
 */

// ============================================
// 示例 1: submitEditServer 优化
// ============================================

// ❌ 优化前
async function submitEditServer_OLD() {
    const serverId = document.getElementById('serverSelector').value;
    if (!serverId) {
        showToast('⚠ 未选择', '请先选择要编辑的服务器', 'warning');
        return;
    }

    const data = {
        id: serverId,
        name: document.getElementById('editServerName').value,
        host: document.getElementById('editServerHost').value,
        port: parseInt(document.getElementById('editServerPort').value),
        username: document.getElementById('editServerUsername').value,
        auth_method: document.getElementById('editAuthMethod').value
    };

    const password = document.getElementById('editServerPassword').value;
    if (password) {
        data.password = password;
    } else {
        const server = currentServers.find(s => s.id == serverId);
        if (server && server.password) {
            data.password = server.password;
        }
    }

    try {
        const res = await fetch(`/servers/${serverId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (res.ok) {
            const updatedServer = await res.json();
            showToast('✓ 更新成功', data.name, 'success');
            bootstrap.Modal.getInstance(document.getElementById('editServerModal')).hide();
            await loadServers();
            document.getElementById('serverSelector').value = serverId;
            addOperationLog('编辑服务器', `成功更新服务器: ${updatedServer.name}`);
        } else {
            const err = await res.json();
            showToast('✗ 失败', err.error, 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('✗ 错误', '网络异常', 'error');
    }
}

// ✅ 优化后
async function submitEditServer_NEW() {
    const serverId = DOMCache.serverSelector.value;  // 使用缓存
    if (!serverId) {
        showToast('⚠ 未选择', '请先选择要编辑的服务器', 'warning');
        return;
    }

    const data = {
        id: serverId,
        name: document.getElementById('editServerName').value,
        host: document.getElementById('editServerHost').value,
        port: parseInt(document.getElementById('editServerPort').value),
        username: document.getElementById('editServerUsername').value,
        auth_method: document.getElementById('editAuthMethod').value
    };

    const password = document.getElementById('editServerPassword').value;
    if (password) {
        data.password = password;
    } else {
        const server = currentServers.find(s => s.id == serverId);
        if (server && server.password) {
            data.password = server.password;
        }
    }

    try {
        const updatedServer = await API.put(`/servers/${serverId}`, data);  // 使用 API 辅助器
        showToast('✓ 更新成功', data.name, 'success');
        bootstrap.Modal.getInstance(document.getElementById('editServerModal')).hide();
        await loadServers();
        DOMCache.serverSelector.value = serverId;  // 使用缓存
        addOperationLog('编辑服务器', `成功更新服务器: ${updatedServer.name}`);
    } catch (e) {
        showToast('✗ 失败', e.message, 'error');  // 简化错误处理
    }
}

// ============================================
// 示例 2: loadServers 优化
// ============================================

// ❌ 优化前
async function loadServers_OLD() {
    try {
        const res = await fetch('/servers');
        if (res.ok) {
            const servers = await res.json();
            currentServers = servers;
            const sel = document.getElementById('serverSelector');
            sel.innerHTML = '<option value="">选择服务器...</option>';
            servers.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.id;
                opt.textContent = `${escapeHtml(s.name)} (${escapeHtml(s.host)}) [${escapeHtml(s.username)}]`;
                sel.appendChild(opt);
            });
            const last = sessionStorage.getItem('lastSelectedServer');
            if (last && servers.some(s => s.id == last)) sel.value = last;
            handleServerSelection();
        }
    } catch (e) { console.error(e); }
}

// ✅ 优化后
async function loadServers_NEW() {
    try {
        const servers = await API.get('/servers');  // 使用 API 辅助器
        currentServers = servers;
        DOMCache.serverSelector.innerHTML = '<option value="">选择服务器...</option>';  // 使用缓存
        servers.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = `${escapeHtml(s.name)} (${escapeHtml(s.host)}) [${escapeHtml(s.username)}]`;
            DOMCache.serverSelector.appendChild(opt);  // 使用缓存
        });
        const last = sessionStorage.getItem('lastSelectedServer');
        if (last && servers.some(s => s.id == last)) DOMCache.serverSelector.value = last;  // 使用缓存
        handleServerSelection();
    } catch (e) {
        console.error('加载服务器失败:', e);
    }
}

// ============================================
// 示例 3: handleServerSelection 优化
// ============================================

// ❌ 优化前
function handleServerSelection_OLD() {
    const id = document.getElementById('serverSelector').value;
    sessionStorage.setItem('lastSelectedServer', id);
    const connected = document.getElementById('connectionStatus');
    const disconnected = document.getElementById('disconnectedStatus');

    connected.classList.add('d-none');
    disconnected.classList.remove('d-none');
    services = [];
    renderServiceCards();
    document.getElementById('fileTree').innerHTML = id ?
        '<li class="text-center text-muted small mt-4">请连接服务器</li>' :
        '<li class="text-center text-muted small mt-4">暂无文件</li>';
    if (editor) editor.setValue('');
}

// ✅ 优化后
function handleServerSelection_NEW() {
    const id = DOMCache.serverSelector.value;  // 使用缓存
    sessionStorage.setItem('lastSelectedServer', id);

    // 使用缓存的 DOM 元素
    DOMCache.connectionStatus.classList.add('d-none');
    DOMCache.disconnectedStatus.classList.remove('d-none');

    services = [];
    renderServiceCards();
    DOMCache.fileTree.innerHTML = id ?
        '<li class="text-center text-muted small mt-4">请连接服务器</li>' :
        '<li class="text-center text-muted small mt-4">暂无文件</li>';
    if (editor) editor.setValue('');
}

// ============================================
// 示例 4: connectToServer 优化
// ============================================

// ❌ 优化前
async function connectToServer_OLD() {
    const id = document.getElementById('serverSelector').value;
    if (!id) return showToast('⚠', '请先选择服务器', 'warning');

    const btn = document.getElementById('connectBtn');
    const originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> 连接中';

    try {
        const res = await fetch(`/servers/${id}/connect`, { method: 'POST' });
        if (res.ok) {
            const result = await res.json();
            document.getElementById('connectionStatus').classList.remove('d-none');
            document.getElementById('disconnectedStatus').classList.add('d-none');
            showToast('✓', '连接成功', 'success');
            addOperationLog('连接服务器', result.message || '已连接');
            loadServices();
        } else throw new Error();
    } catch (e) {
        showToast('✗', '连接失败', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
    }
}

// ✅ 优化后
async function connectToServer_NEW() {
    const id = DOMCache.serverSelector.value;  // 使用缓存
    if (!id) return showToast('⚠', '请先选择服务器', 'warning');

    const originalHtml = DOMCache.connectBtn.innerHTML;  // 使用缓存
    DOMCache.connectBtn.disabled = true;
    DOMCache.connectBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> 连接中';

    try {
        const result = await API.post(`/servers/${id}/connect`);  // 使用 API 辅助器
        DOMCache.connectionStatus.classList.remove('d-none');  // 使用缓存
        DOMCache.disconnectedStatus.classList.add('d-none');
        showToast('✓', '连接成功', 'success');
        addOperationLog('连接服务器', result.message || '已连接');
        loadServices();
    } catch (e) {
        showToast('✗', '连接失败', 'error');
    } finally {
        DOMCache.connectBtn.disabled = false;  // 使用缓存
        DOMCache.connectBtn.innerHTML = originalHtml;
    }
}

// ============================================
// 示例 5: saveCurrentFile 优化
// ============================================

// ❌ 优化前
async function saveCurrentFile_OLD() {
    if (!currentFilePath) {
        showToast('⚠', '请先选择要保存的文件', 'warning');
        return;
    }
    const serverId = document.getElementById('serverSelector').value;
    if (!serverId) {
        showToast('⚠', '未选择服务器', 'warning');
        return;
    }

    const btn = document.getElementById('saveFileBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 保存中';

    try {
        const content = editor.getValue();
        const response = await fetch(`/config/files/${encodeURIComponent(currentFilePath)}?server_id=${serverId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        if (response.ok) {
            document.getElementById('lastSavedTime').textContent = `已保存 ${new Date().toLocaleTimeString()}`;
            showToast('✓ 保存成功', '文件已更新并备份', 'success');
            addOperationLog('保存文件', `文件保存成功: ${currentFilePath}`);
            if (currentServiceName) loadFileTree(currentServiceName);
        } else throw new Error('保存失败');
    } catch (error) {
        showToast('✗ 保存失败', error.message, 'error');
        addOperationLog('保存文件', `保存失败: ${error.message}`);
        btn.disabled = false;
    } finally {
        if (btn.innerHTML.includes('保存中')) {
            btn.innerHTML = '<i class="fas fa-save me-1"></i> 保存更改';
        }
    }
}

// ✅ 优化后
async function saveCurrentFile_NEW() {
    if (!currentFilePath) {
        showToast('⚠', '请先选择要保存的文件', 'warning');
        return;
    }
    const serverId = DOMCache.serverSelector.value;  // 使用缓存
    if (!serverId) {
        showToast('⚠', '未选择服务器', 'warning');
        return;
    }

    DOMCache.saveFileBtn.disabled = true;  // 使用缓存
    DOMCache.saveFileBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 保存中';

    try {
        const content = editor.getValue();
        await API.post(  // 使用 API 辅助器
            `/config/files/${encodeURIComponent(currentFilePath)}?server_id=${serverId}`,
            { content }
        );

        DOMCache.lastSavedTime.textContent = `已保存 ${new Date().toLocaleTimeString()}`;  // 使用缓存
        showToast('✓ 保存成功', '文件已更新并备份', 'success');
        addOperationLog('保存文件', `文件保存成功: ${currentFilePath}`);
        if (currentServiceName) loadFileTree(currentServiceName);
    } catch (error) {
        showToast('✗ 保存失败', error.message, 'error');
        addOperationLog('保存文件', `保存失败: ${error.message}`);
        DOMCache.saveFileBtn.disabled = false;  // 使用缓存
    } finally {
        if (DOMCache.saveFileBtn.innerHTML.includes('保存中')) {
            DOMCache.saveFileBtn.innerHTML = '<i class="fas fa-save me-1"></i> 保存更改';
        }
    }
}

// ============================================
// 示例 6: renderServiceCards 优化
// ============================================

// ❌ 优化前
function renderServiceCards_OLD() {
    const container = document.getElementById('serviceContainer');
    if (services.length === 0) {
        container.innerHTML = `<div class="text-center text-muted mt-5 small">...</div>`;
        return;
    }
    // ... 渲染逻辑
}

// ✅ 优化后
function renderServiceCards_NEW() {
    if (services.length === 0) {
        DOMCache.serviceContainer.innerHTML = `<div class="text-center text-muted mt-5 small">...</div>`;  // 使用缓存
        return;
    }
    // ... 渲染逻辑
}

// ============================================
// 批量替换模式
// ============================================

// 使用查找替换工具批量优化:
//
// 1. 替换 serverSelector:
//    查找: document.getElementById('serverSelector')
//    替换: DOMCache.serverSelector
//
// 2. 替换 connectionStatus:
//    查找: document.getElementById('connectionStatus')
//    替换: DOMCache.connectionStatus
//
// 3. 替换 GET 请求:
//    查找: const res = await fetch\('(.+?)'\); if \(res\.ok\) \{ const (.+?) = await res\.json\(\);
//    替换: const $2 = await API.get('$1');
//
// 4. 替换 POST 请求:
//    查找: const res = await fetch\('(.+?)', \{ method: 'POST', headers: \{ 'Content-Type': 'application/json' \}, body: JSON\.stringify\((.+?)\) \}\); if \(res\.ok\) \{ const (.+?) = await res\.json\(\);
//    替换: const $3 = await API.post('$1', $2);
