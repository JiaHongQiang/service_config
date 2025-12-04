/**
 * 主应用模块
 * Main application module
 */

const App = (function () {
    const { DOMCache } = window.CoreUtils;

    // Monaco 编辑器实例
    let editor = null;

    // 初始化编辑器
    function initializeEditor() {
        require.config({
            paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.34.1/min/vs' }
        });

        require(['vs/editor/editor.main'], () => {
            editor = monaco.editor.create(document.getElementById('editor'), {
                value: '',
                language: 'ini',
                theme: 'vs',
                automaticLayout: true,
                fontSize: 13,
                fontFamily: "'JetBrains Mono', Consolas, monospace",
                minimap: { enabled: true, scale: 0.75 },
                scrollBeyondLastLine: false
            });

            editor.onDidChangeModelContent(() => {
                if (window.ConfigManager && window.ConfigManager.getCurrentFilePath()) {
                    DOMCache.saveFileBtn.disabled = false;
                }
            });

            console.log('✓ Monaco 编辑器已初始化');
        });
    }

    // 切换 SFTP 视图
    function toggleSftpView() {
        const serverId = DOMCache.serverSelector.value;
        const isConnected = !DOMCache.connectionStatus.classList.contains('d-none');

        if (DOMCache.sftpContainer.classList.contains('d-none')) {
            if (!serverId) {
                window.CoreUtils.showToast('⚠ 选择服务器', '请先选择服务器', 'warning');
                return;
            }
            if (!isConnected) {
                window.CoreUtils.showToast('⚠ 未连接', '请先连接服务器', 'warning');
                return;
            }

            DOMCache.sftpContainer.classList.remove('d-none');
            DOMCache.configEditorContainer.classList.add('d-none');

            const iframe = document.getElementById('sftpIframe');
            if (iframe) iframe.src = `/sftp_page?server_id=${encodeURIComponent(serverId)}`;
        } else {
            DOMCache.sftpContainer.classList.add('d-none');
            DOMCache.configEditorContainer.classList.remove('d-none');

            const iframe = document.getElementById('sftpIframe');
            if (iframe) iframe.src = '';
        }
    }

    // 检查登录状态
    async function checkLoginStatus() {
        try {
            const res = await fetch('/auth/status');
            if (res.ok) {
                const data = await res.json();
                return data.logged_in;
            }
            return false;
        } catch (e) {
            return false;
        }
    }

    // 登出
    async function logout() {
        try {
            await fetch('/auth/logout', { method: 'POST' });
            window.location.href = '/login';
        } catch (e) {
            window.CoreUtils.showToast('错误', '登出失败', 'error');
        }
    }

    // 初始化应用
    async function init() {
        console.log('🚀 应用初始化开始...');

        // 1. 初始化 DOM 缓存
        DOMCache.init();

        // 2. 初始化编辑器
        initializeEditor();

        // 3. 加载操作日志
        window.LogManager.loadOperationLog();

        // 4. 加载服务器列表
        await window.ServerManager.loadServers();

        // 5. 检查登录状态
        const loggedIn = await checkLoginStatus();
        if (!loggedIn) {
            window.location.href = '/login';
            return;
        }

        // 6. 设置定时刷新
        setInterval(() => {
            if (!DOMCache.connectionStatus.classList.contains('d-none')) {
                window.ServiceManager.loadServices();
            }
        }, 30000);

        console.log('✓ 应用初始化完成');
    }

    // 导出编辑器实例供其他模块使用
    function getEditor() {
        return editor;
    }

    // 公共 API
    return {
        init,
        toggleSftpView,
        logout,
        getEditor
    };
})();

// 导出到全局
window.App = App;
window.editor = null;

// 在 editor 被获取时更新全局变量
Object.defineProperty(window, 'editor', {
    get() {
        return window.App.getEditor();
    }
});

// 页面加载完成后初始化
window.addEventListener('DOMContentLoaded', function () {
    console.log('📄 DOM 加载完成');
    window.App.init();
});
