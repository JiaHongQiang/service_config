/**
 * 日志管理模块
 * Log management module
 */

const LogManager = (function () {
    const { DOMCache, escapeHtml } = window.CoreUtils;

    // 私有变量
    let operationLog = [];
    let serviceLogs = [];

    // 加载操作日志
    function loadOperationLog() {
        try {
            const savedLog = localStorage.getItem('operationLog');
            if (savedLog) operationLog = JSON.parse(savedLog);
        } catch (e) {
            console.error('加载操作日志失败:', e);
        }
        renderOperationLog();
    }

    // 添加操作日志
    function addOperationLog(operation, details = '') {
        const now = new Date();
        const logEntry = {
            id: Date.now(),
            timestamp: now.toLocaleTimeString('zh-CN'),
            operation: operation,
            details: details
        };

        operationLog.unshift(logEntry);
        if (operationLog.length > 100) operationLog.pop();

        try {
            localStorage.setItem('operationLog', JSON.stringify(operationLog));
        } catch (e) {
            console.error('保存操作日志失败:', e);
        }

        renderOperationLog();
    }

    // 渲染操作日志
    function renderOperationLog() {
        if (operationLog.length === 0) {
            DOMCache.operationLog.innerHTML = '<li class="text-muted small text-center mt-4">暂无操作记录</li>';
            return;
        }

        DOMCache.operationLog.innerHTML = '';
        operationLog.forEach(entry => {
            const logItem = document.createElement('li');
            logItem.innerHTML = `
                <div class="d-flex justify-content-between">
                    <span class="fw-bold text-dark">${escapeHtml(entry.operation)}</span>
                    <small class="text-secondary font-monospace">${entry.timestamp}</small>
                </div>
                ${entry.details ? `
                    <div class="text-secondary small mt-1 text-break">${escapeHtml(entry.details)}</div>
                ` : ''}
            `;
            DOMCache.operationLog.appendChild(logItem);
        });
    }

    // 清空操作日志
    function clearOperationLog() {
        operationLog = [];
        localStorage.removeItem('operationLog');
        renderOperationLog();
    }

    // 更新服务日志
    function updateServiceLogs(serviceName, errors) {
        // 移除旧的同名服务日志
        serviceLogs = serviceLogs.filter(log => log.service !== serviceName);
        // 添加新日志
        serviceLogs.push(...errors);
        renderServiceLogs();
    }

    // 渲染服务日志
    function renderServiceLogs() {
        if (!DOMCache.errorLogList) return;

        if (serviceLogs.length === 0) {
            DOMCache.errorLogList.innerHTML = '<li class="text-muted small text-center mt-4">暂无错误日志</li>';
            return;
        }

        // 按时间倒序排序
        const sortedLogs = [...serviceLogs].sort((a, b) =>
            new Date(b.timestamp) - new Date(a.timestamp)
        );

        // 去重
        const uniqueLogs = [];
        const seenErrors = new Set();

        for (const log of sortedLogs) {
            const errorKey = `${log.service}-${log.error_name}-${log.timestamp}`;
            if (!seenErrors.has(errorKey)) {
                seenErrors.add(errorKey);
                uniqueLogs.push(log);
            }
        }

        DOMCache.errorLogList.innerHTML = '';
        uniqueLogs.forEach(entry => {
            const logItem = document.createElement('li');
            logItem.style.borderLeftColor = '#ef4444';
            logItem.innerHTML = `
                <div class="d-flex justify-content-between">
                    <span class="fw-bold text-danger small">
                        [${escapeHtml(entry.service)}] ${escapeHtml(entry.error_name)}
                    </span>
                    <small class="text-secondary font-monospace">
                        ${entry.timestamp.split(' ')[1] || entry.timestamp}
                    </small>
                </div>
                <div class="text-secondary small text-break mt-1 font-monospace">
                    ${escapeHtml(entry.log_line)}
                </div>
            `;
            DOMCache.errorLogList.appendChild(logItem);
        });
    }

    // 清空服务日志
    function clearServiceLogs() {
        serviceLogs = [];
        renderServiceLogs();
    }

    // 公共 API
    return {
        loadOperationLog,
        addOperationLog,
        clearOperationLog,
        updateServiceLogs,
        clearServiceLogs
    };
})();

// 导出到全局
window.LogManager = LogManager;
