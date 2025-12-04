/**
 * DOM缓存初始化脚本
 * 将此代码添加到 index.html 的 DOMContentLoaded 事件监听器中
 */

// 在现有的 window.addEventListener('DOMContentLoaded', ...) 中添加
window.addEventListener('DOMContentLoaded', function () {
    // ============================================
    // 第一步: 初始化 DOM 缓存
    // ============================================
    DOMCache.init();
    console.log('✓ DOM 缓存已初始化');

    // ============================================
    // 原有的初始化代码
    // ============================================
    initializeEditor();
    loadOperationLog();
    loadServers();
    checkLoginStatus().then(loggedIn => {
        if (!loggedIn) window.location.href = '/login';
    });
    startErrorLogRefresh();

    // 设置定时刷新
    setInterval(() => {
        if (!DOMCache.connectionStatus.classList.contains('d-none')) {  // 使用缓存
            loadServices();
        }
    }, 30000);
});

// ============================================
// 验证缓存是否正确初始化
// ============================================
function validateDOMCache() {
    const requiredElements = [
        'serverSelector',
        'connectionStatus',
        'disconnectedStatus',
        'connectBtn',
        'saveFileBtn',
        'compareBtn',
        'backupListBtn',
        'serviceContainer',
        'fileTree',
        'operationLog',
        'errorLogList',
        'sftpContainer',
        'configEditorContainer',
        'currentFileName',
        'lastSavedTime'
    ];

    const missing = requiredElements.filter(key => !DOMCache[key]);

    if (missing.length > 0) {
        console.error('❌ DOMCache 缺少以下元素:', missing);
        return false;
    }

    console.log('✅ DOMCache 验证通过,所有元素已缓存');
    return true;
}

// 在开发环境中可以调用此函数验证
// validateDOMCache();
