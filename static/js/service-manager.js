/**
 * 服务控制模块
 * Service management module
 */

const ServiceManager = (function () {
    const { DOMCache, API, showToast, escapeHtml } = window.CoreUtils;

    // 私有变量
    let services = [];

    // 加载服务状态
    async function loadServices() {
        const id = DOMCache.serverSelector.value;
        const isConnected = !DOMCache.connectionStatus.classList.contains('d-none');

        if (!isConnected || !id) {
            services = [];
            renderServiceCards();
            return;
        }

        try {
            const res = await fetch(`/services/status?server_id=${id}`);
            services = res.ok ? await res.json() : [];
            renderServiceCards();
        } catch (e) {
            services = [];
            renderServiceCards();
        }
    }

    // 刷新服务状态
    async function refreshServiceStatus() {
        if (DOMCache.connectionStatus.classList.contains('d-none')) return;
        await loadServices();
        showToast('✓', '状态已刷新', 'success');
    }

    // 渲染服务卡片
    function renderServiceCards() {
        if (services.length === 0) {
            DOMCache.serviceContainer.innerHTML = `
                <div class="text-center text-muted mt-5 small">
                    <i class="fas fa-server fa-2x mb-3 opacity-25"></i>
                    <p>暂无服务或未连接</p>
                </div>
            `;
            return;
        }

        const fragment = document.createDocumentFragment();
        services.forEach(svc => {
            const isActive = svc.status === 'active';
            const statusClass = isActive ? 'status-running' :
                (svc.status === 'inactive' || svc.status === 'failed' ? 'status-stopped' : 'status-unknown');
            const statusText = isActive ? '运行' : (svc.status === 'inactive' ? '停止' : '未知');
            const statusColor = isActive ? 'text-success' : 'text-danger';

            const card = document.createElement('div');
            card.className = 'service-card';
            card.innerHTML = `
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <h6 class="card-title mb-0 fw-bold text-dark text-truncate" 
                            style="max-width: 140px; font-size: 0.9rem;" 
                            title="${escapeHtml(svc.display_name)}">
                            ${escapeHtml(svc.display_name)}
                        </h6>
                        <div class="d-flex align-items-center">
                            <span class="status-indicator ${statusClass}"></span>
                            <span class="small fw-medium ${statusColor}" style="font-size: 0.75rem;">${statusText}</span>
                        </div>
                    </div>
                    <div class="text-secondary small font-monospace mb-2" style="font-size:0.75rem">
                        ${escapeHtml(svc.name)}
                    </div>
                    <div class="service-footer d-flex justify-content-between align-items-center">
                        <div>
                            ${svc.has_config ? `
                                <button class="btn btn-sm btn-link text-decoration-none text-primary p-0" 
                                        style="font-size:0.8rem" 
                                        onclick="window.ConfigManager.openConfig('${escapeHtml(svc.name)}')" 
                                        title="编辑配置">
                                    <i class="fas fa-cog"></i> 配置
                                </button>
                            ` : ''}
                        </div>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-light text-success p-1 px-2" 
                                    onclick="window.ServiceManager.serviceAction('${escapeHtml(svc.name)}', 'start')" 
                                    title="启动">
                                <i class="fas fa-play fa-xs"></i>
                            </button>
                            <button class="btn btn-light text-warning p-1 px-2" 
                                    onclick="window.ServiceManager.serviceAction('${escapeHtml(svc.name)}', 'restart')" 
                                    title="重启">
                                <i class="fas fa-redo fa-xs"></i>
                            </button>
                            <button class="btn btn-light text-danger p-1 px-2" 
                                    onclick="window.ServiceManager.serviceAction('${escapeHtml(svc.name)}', 'stop')" 
                                    title="停止">
                                <i class="fas fa-stop fa-xs"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
            fragment.appendChild(card);
        });

        DOMCache.serviceContainer.innerHTML = '';
        DOMCache.serviceContainer.appendChild(fragment);
    }

    // 服务操作
    async function serviceAction(name, action) {
        const id = DOMCache.serverSelector.value;
        try {
            const res = await fetch(`/services/${name}/${action}?server_id=${id}`, { method: 'POST' });
            if (res.ok) {
                const actionText = { start: '启动', stop: '停止', restart: '重启' }[action];
                showToast('✓', `${name} ${actionText} 指令已发送`, 'success');
                window.LogManager.addOperationLog('服务操作', `向服务 ${name} 发送 ${action} 命令`);

                if (action === 'start') {
                    setTimeout(() => fetchServiceErrors(name), 2000);
                }

                setTimeout(loadServices, 1000);
            } else {
                showToast('✗', '操作失败', 'error');
            }
        } catch (e) {
            showToast('✗', '网络异常', 'error');
        }
    }

    // 获取服务错误日志
    async function fetchServiceErrors(serviceName) {
        const serverId = DOMCache.serverSelector.value;
        if (!serverId) return;

        try {
            const response = await fetch(`/services/${serviceName}/errors?server_id=${serverId}`);
            if (response.ok) {
                const errors = await response.json();
                if (window.LogManager) {
                    window.LogManager.updateServiceLogs(serviceName, errors);
                }
            }
        } catch (error) {
            console.error('获取服务错误日志失败:', error);
        }
    }

    // 清空服务列表
    function clearServices() {
        services = [];
        renderServiceCards();
    }

    // 公共 API
    return {
        loadServices,
        refreshServiceStatus,
        serviceAction,
        clearServices,
        getServices: () => services
    };
})();

// 导出到全局
window.ServiceManager = ServiceManager;
