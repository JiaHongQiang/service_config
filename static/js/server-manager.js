/**
 * 服务器管理模块
 * Server management module
 */

const ServerManager = (function () {
    const { DOMCache, API, showToast, escapeHtml } = window.CoreUtils;

    // 私有变量
    let currentServers = [];

    // 切换认证字段显示
    function toggleAuthFields() {
        const method = document.getElementById('authMethod').value;
        document.getElementById('passwordField').classList.toggle('d-none', method !== 'password');
        document.getElementById('keyField').classList.toggle('d-none', method !== 'key');
    }

    function toggleEditAuthFields() {
        const method = document.getElementById('editAuthMethod').value;
        document.getElementById('editPasswordField').classList.toggle('d-none', method !== 'password');
        document.getElementById('editKeyField').classList.toggle('d-none', method !== 'key');
    }

    // 打开编辑服务器模态框
    function openEditServerModal() {
        const serverId = DOMCache.serverSelector.value;
        if (!serverId) {
            showToast('⚠ 未选择', '请先选择要编辑的服务器', 'warning');
            return false;
        }

        const server = currentServers.find(s => s.id == serverId);
        if (!server) {
            showToast('✗ 错误', '未找到服务器信息', 'error');
            return false;
        }

        // 填充表单
        document.getElementById('editServerName').value = server.name;
        document.getElementById('editServerHost').value = server.host;
        document.getElementById('editServerPort').value = server.port;
        document.getElementById('editServerUsername').value = server.username;
        document.getElementById('editAuthMethod').value = server.auth_method || 'password';
        document.getElementById('editServerPassword').value = '';

        toggleEditAuthFields();
    }

    // 提交编辑服务器
    async function submitEditServer() {
        const serverId = DOMCache.serverSelector.value;
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
            const updatedServer = await API.put(`/servers/${serverId}`, data);
            showToast('✓ 更新成功', data.name, 'success');
            bootstrap.Modal.getInstance(document.getElementById('editServerModal')).hide();
            await loadServers();
            DOMCache.serverSelector.value = serverId;
            window.LogManager.addOperationLog('编辑服务器', `成功更新服务器: ${updatedServer.name}`);
        } catch (e) {
            showToast('✗ 失败', e.message, 'error');
        }
    }

    // 添加服务器
    async function addServer() {
        const data = {
            id: Date.now().toString(),
            name: document.getElementById('serverName').value,
            host: document.getElementById('serverHost').value,
            port: parseInt(document.getElementById('serverPort').value),
            username: document.getElementById('serverUsername').value,
            auth_method: document.getElementById('authMethod').value
        };

        if (data.auth_method === 'password') {
            data.password = document.getElementById('serverPassword').value;
        }

        try {
            const newServer = await API.post('/servers', data);
            showToast('✓ 添加成功', data.name, 'success');
            bootstrap.Modal.getInstance(document.getElementById('addServerModal')).hide();
            loadServers();
            window.LogManager.addOperationLog('添加服务器', `成功添加服务器: ${newServer.name}`);
        } catch (e) {
            showToast('✗ 失败', e.message, 'error');
        }
    }

    // 删除服务器
    async function deleteSelectedServer() {
        const id = DOMCache.serverSelector.value;
        if (!id) return;
        if (!confirm('确定删除该服务器配置吗？')) return;

        try {
            await API.delete(`/servers/${id}`);
            showToast('✓ 删除成功', '', 'success');
            sessionStorage.removeItem('lastSelectedServer');
            loadServers();
            window.LogManager.addOperationLog('删除服务器', '服务器已删除');
        } catch (e) {
            showToast('✗ 错误', e.message, 'error');
        }
    }

    // 加载服务器列表
    async function loadServers() {
        try {
            const servers = await API.get('/servers');
            currentServers = servers;
            DOMCache.serverSelector.innerHTML = '<option value="">选择服务器...</option>';

            servers.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.id;
                opt.textContent = `${escapeHtml(s.name)} (${escapeHtml(s.host)}) [${escapeHtml(s.username)}]`;
                DOMCache.serverSelector.appendChild(opt);
            });

            const last = sessionStorage.getItem('lastSelectedServer');
            if (last && servers.some(s => s.id == last)) {
                DOMCache.serverSelector.value = last;
            }

            handleServerSelection();
        } catch (e) {
            console.error('加载服务器失败:', e);
        }
    }

    // 处理服务器选择
    function handleServerSelection() {
        const id = DOMCache.serverSelector.value;
        sessionStorage.setItem('lastSelectedServer', id);

        // 切换服务器时重置为未连接状态
        DOMCache.connectionStatus.classList.add('d-none');
        DOMCache.disconnectedStatus.classList.remove('d-none');

        // 清空服务列表
        if (window.ServiceManager) {
            window.ServiceManager.clearServices();
        }

        // 更新文件树
        DOMCache.fileTree.innerHTML = id ?
            '<li class="text-center text-muted small mt-4">请连接服务器</li>' :
            '<li class="text-center text-muted small mt-4">暂无文件</li>';

        // 清空编辑器
        if (window.editor) {
            window.editor.setValue('');
        }
    }

    // 连接到服务器
    async function connectToServer() {
        const id = DOMCache.serverSelector.value;
        if (!id) {
            showToast('⚠', '请先选择服务器', 'warning');
            return;
        }

        const originalHtml = DOMCache.connectBtn.innerHTML;
        DOMCache.connectBtn.disabled = true;
        DOMCache.connectBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> 连接中';

        try {
            const result = await API.post(`/servers/${id}/connect`);
            DOMCache.connectionStatus.classList.remove('d-none');
            DOMCache.disconnectedStatus.classList.add('d-none');
            showToast('✓', '连接成功', 'success');
            window.LogManager.addOperationLog('连接服务器', result.message || '已连接');

            // 加载服务列表
            if (window.ServiceManager) {
                window.ServiceManager.loadServices();
            }
        } catch (e) {
            showToast('✗', '连接失败', 'error');
        } finally {
            DOMCache.connectBtn.disabled = false;
            DOMCache.connectBtn.innerHTML = originalHtml;
        }
    }

    // 公共 API
    return {
        toggleAuthFields,
        toggleEditAuthFields,
        openEditServerModal,
        submitEditServer,
        addServer,
        deleteSelectedServer,
        loadServers,
        handleServerSelection,
        connectToServer,
        getCurrentServers: () => currentServers
    };
})();

// 导出到全局
window.ServerManager = ServerManager;
