/**
 * 测试连接模块
 * Connection testing module
 */

const ConnectionTester = (function () {
    const { showToast } = window.CoreUtils;

    /**
     * 通用的服务器连接测试函数
     * @param {string} mode - 测试模式：'add' 或 'edit'
     */
    async function testServerConnection(mode = 'add') {
        // 获取表单数据
        const data = getServerFormData(mode);
        if (!data) return;

        // 获取测试按钮
        const btnId = mode === 'add' ? 'testAddConnectionBtn' : 'testEditConnectionBtn';
        const testBtn = document.getElementById(btnId);
        const originalHtml = testBtn.innerHTML;

        // 设置按钮加载状态
        testBtn.disabled = true;
        testBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> 测试中...';

        try {
            // 临时添加服务器
            const addRes = await fetch('/servers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (!addRes.ok) {
                const err = await addRes.json();
                showToast('✗ 错误', err.error, 'error');
                return;
            }

            const server = await addRes.json();

            // 测试连接
            showToast('测试中...', '正在测试连接', 'info', 2000);
            const testRes = await fetch(`/servers/${server.id}/test_connection`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            // 清理临时服务器
            await fetch(`/servers/${server.id}`, { method: 'DELETE' });

            // 显示测试结果
            await handleTestResult(testRes, data);

        } catch (e) {
            console.error('测试连接失败:', e);
            showToast('✗ 错误', '测试连接失败：' + e.message, 'error');
        } finally {
            // 恢复按钮状态
            testBtn.disabled = false;
            testBtn.innerHTML = originalHtml;
        }
    }

    /**
     * 获取服务器表单数据
     * @param {string} mode - 表单模式：'add' 或 'edit'
     * @returns {Object|null} 服务器数据对象，验证失败返回null
     */
    function getServerFormData(mode) {
        const prefix = mode === 'add' ? 'server' : 'editServer';
        const authMethodId = mode === 'add' ? 'authMethod' : 'editAuthMethod';

        const data = {
            id: 'temp-test-' + Date.now().toString(),
            name: document.getElementById(prefix + 'Name').value,
            host: document.getElementById(prefix + 'Host').value,
            port: parseInt(document.getElementById(prefix + 'Port').value),
            username: document.getElementById(prefix + 'Username').value,
            auth_method: document.getElementById(authMethodId).value,
            password: document.getElementById(prefix + 'Password').value
        };

        // 编辑模式特殊处理：如果密码为空，使用原密码
        if (mode === 'edit' && !data.password) {
            const serverId = document.getElementById('serverSelector').value;
            if (window.ServerManager) {
                const servers = window.ServerManager.getCurrentServers();
                const server = servers.find(s => s.id == serverId);
                if (server && server.password) {
                    data.password = server.password;
                }
            }
        }

        // 验证必填字段
        if (!data.host || !data.username || (!data.password && data.auth_method === 'password')) {
            showToast('⚠ 提示', '请先填写完整的服务器信息（主机地址、用户名、密码）', 'warning');
            return null;
        }

        return data;
    }

    /**
     * 处理测试连接结果
     * @param {Response} testRes - 测试连接的响应对象
     * @param {Object} data - 服务器数据
     */
    async function handleTestResult(testRes, data) {
        if (testRes.ok) {
            const result = await testRes.json();
            showToast('✓ 连接成功', result.message, 'success', 5000);
            window.LogManager.addOperationLog('测试连接', `测试成功: ${data.name} (${data.host})`);
        } else {
            const err = await testRes.json();
            showToast('✗ 连接失败', err.error, 'error', 5000);
            window.LogManager.addOperationLog('测试连接', `测试失败: ${data.name} - ${err.error}`);
        }
    }

    /**
     * 测试添加服务器时的连接
     */
    async function testAddConnection() {
        await testServerConnection('add');
    }

    /**
     * 测试编辑服务器时的连接
     */
    async function testEditConnection() {
        // 验证是否选择了服务器
        const serverId = document.getElementById('serverSelector').value;
        if (!serverId) {
            showToast('⚠ 未选择', '请先选择要编辑的服务器', 'warning');
            return;
        }
        await testServerConnection('edit');
    }

    // 公共 API
    return {
        testAddConnection,
        testEditConnection
    };
})();

// 导出到全局
window.ConnectionTester = ConnectionTester;
