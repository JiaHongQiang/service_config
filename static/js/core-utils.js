/**
 * 核心工具模块
 * Core utilities and helpers
 */

// DOM 元素缓存
const DOMCache = {
    // 服务器相关
    serverSelector: null,
    connectionStatus: null,
    disconnectedStatus: null,

    // 按钮
    connectBtn: null,
    saveFileBtn: null,
    compareBtn: null,
    backupListBtn: null,

    // 容器
    serviceContainer: null,
    fileTree: null,
    operationLog: null,
    errorLogList: null,
    sftpContainer: null,
    configEditorContainer: null,

    // 文件编辑器
    currentFileName: null,
    lastSavedTime: null,

    // 初始化缓存
    init() {
        this.serverSelector = document.getElementById('serverSelector');
        this.connectionStatus = document.getElementById('connectionStatus');
        this.disconnectedStatus = document.getElementById('disconnectedStatus');
        this.connectBtn = document.getElementById('connectBtn');
        this.saveFileBtn = document.getElementById('saveFileBtn');
        this.compareBtn = document.getElementById('compareBtn');
        this.backupListBtn = document.getElementById('backupListBtn');
        this.serviceContainer = document.getElementById('serviceContainer');
        this.fileTree = document.getElementById('fileTree');
        this.operationLog = document.getElementById('operationLog');
        this.errorLogList = document.getElementById('errorLogList');
        this.sftpContainer = document.getElementById('sftpContainer');
        this.configEditorContainer = document.getElementById('configEditorContainer');
        this.currentFileName = document.getElementById('currentFileName');
        this.lastSavedTime = document.getElementById('lastSavedTime');

        console.log('✓ DOM 缓存已初始化');
    }
};

// 统一 API 辅助器
const API = {
    /**
     * 统一的 API 请求处理
     */
    async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, { ...defaultOptions, ...options });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ error: '请求失败' }));
                throw new Error(error.error || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API Request Error:', error);
            throw error;
        }
    },

    // GET 请求
    async get(url) {
        return this.request(url, { method: 'GET' });
    },

    // POST 请求
    async post(url, data = null) {
        return this.request(url, {
            method: 'POST',
            body: data ? JSON.stringify(data) : undefined
        });
    },

    // PUT 请求
    async put(url, data) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    // DELETE 请求
    async delete(url) {
        return this.request(url, { method: 'DELETE' });
    }
};

// HTML 转义工具
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Toast 通知
function showToast(title, message, type = 'info', duration = 3000) {
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-times-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };

    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#3b82f6'
    };

    const toastHtml = `
        <div class="toast-item" style="animation: slideInRight 0.3s ease-out;">
            <div class="d-flex align-items-center">
                <i class="fas ${icons[type]} toast-icon" style="color: ${colors[type]};"></i>
                <div class="flex-grow-1">
                    <div class="toast-title">${escapeHtml(title)}</div>
                    ${message ? `<div class="toast-message">${escapeHtml(message)}</div>` : ''}
                </div>
                <button class="toast-close" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        </div>
    `;

    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toastElement = document.createElement('div');
    toastElement.innerHTML = toastHtml;
    const toast = toastElement.firstElementChild;
    container.appendChild(toast);

    if (duration > 0) {
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
}

// 导出模块
window.CoreUtils = {
    DOMCache,
    API,
    escapeHtml,
    showToast
};
