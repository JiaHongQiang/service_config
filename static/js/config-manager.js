/**
 * 配置文件管理模块
 * Configuration file management module
 */

const ConfigManager = (function () {
    const { DOMCache, API, showToast, escapeHtml } = window.CoreUtils;

    // 私有变量
    let currentServiceName = null;
    let currentFilePath = null;

    // 打开配置
    function openConfig(serviceName) {
        const id = DOMCache.serverSelector.value;
        if (!id) {
            showToast('⚠', '未选择服务器', 'warning');
            return;
        }

        currentServiceName = serviceName;

        // 确保显示编辑器视图
        DOMCache.sftpContainer.classList.add('d-none');
        DOMCache.configEditorContainer.classList.remove('d-none');

        loadFileTree(serviceName);
    }

    // 加载文件树
    async function loadFileTree(serviceName = currentServiceName) {
        if (!serviceName) return;

        const serverId = DOMCache.serverSelector.value;
        if (!serverId) {
            showToast('⚠ 选择服务器', '未选择服务器', 'warning');
            return;
        }

        try {
            const response = await fetch(`/config/files?service=${encodeURIComponent(serviceName)}&server_id=${serverId}`);
            if (response.ok) {
                const files = await response.json();
                renderFileTree(files, serviceName);
            } else {
                showToast('✗ 加载失败', '无法加载文件列表', 'error');
            }
        } catch (error) {
            showToast('✗ 加载失败', error.message, 'error');
        }
    }

    // 渲染文件树
    function renderFileTree(files, serviceName) {
        DOMCache.fileTree.innerHTML = '';

        if (files[serviceName]) {
            const serviceNode = document.createElement('li');
            serviceNode.className = 'mb-2';
            serviceNode.innerHTML = `
                <div class="fw-bold text-dark px-2 py-1 bg-light rounded mb-2 border">
                    <i class="fas fa-box me-2 text-secondary"></i>${serviceName}
                </div>
            `;

            const fileList = document.createElement('ul');
            fileList.className = 'list-unstyled ms-2 border-start border-2 border-light ps-2';

            // 排序：文件夹在前，文件在后
            const sortedFiles = [...files[serviceName]].sort((a, b) => {
                if (a.type === 'directory' && b.type !== 'directory') return -1;
                if (a.type !== 'directory' && b.type === 'directory') return 1;
                return a.name.localeCompare(b.name);
            });

            sortedFiles.forEach(fileItem => {
                const fileName = fileItem.name;
                const fileNode = document.createElement('li');
                fileNode.className = 'd-flex justify-content-between align-items-center mb-1 rounded';

                const iconClass = fileItem.type === 'directory' ? 'fa-folder' : 'fa-file';
                const textClass = fileItem.type === 'directory' ? 'text-warning' : 'text-secondary';
                const displayName = fileName.length > 25 ? fileName.substring(0, 22) + '...' : fileName;

                fileNode.innerHTML = `
                    <div class="text-truncate px-2 py-1 w-100 file-item-hover" 
                         style="cursor:pointer; font-size: 0.85rem;" 
                         onclick="window.ConfigManager.handleFileClick('${fileItem.path}', '${fileItem.type}')">
                        <i class="fas ${iconClass} me-2 ${textClass}" style="width: 16px; text-align:center;"></i>${displayName}
                    </div>
                    ${fileItem.type !== 'directory' ? `
                        <button class="btn btn-link text-danger p-0 ms-1 opacity-50 hover-opacity-100" 
                                style="font-size:0.8rem;" 
                                onclick="window.ConfigManager.deleteConfigFile('${fileItem.path}', event)" 
                                title="删除文件">
                            <i class="fas fa-times"></i>
                        </button>
                    ` : ''}
                `;
                fileList.appendChild(fileNode);
            });

            serviceNode.appendChild(fileList);
            DOMCache.fileTree.appendChild(serviceNode);
        } else {
            DOMCache.fileTree.innerHTML = '<li class="text-center text-muted small mt-4">请选择服务打开配置文件</li>';
        }
    }

    // 处理文件点击
    async function handleFileClick(filePath, fileType) {
        if (fileType === 'directory') {
            await browseDirectory(filePath);
        } else {
            loadFileContent(filePath);
        }
    }

    // 浏览目录
    async function browseDirectory(dirPath) {
        const serverId = DOMCache.serverSelector.value;
        if (!serverId) {
            showToast('⚠ 选择服务器', '未选择服务器', 'warning');
            return;
        }

        try {
            const response = await fetch(`/api/sftp/list?server_id=${serverId}&path=${encodeURIComponent(dirPath)}`);
            if (response.ok) {
                const items = await response.json();
                renderDirectoryContents(items, dirPath);
            } else {
                const errorData = await response.json();
                showToast('✗ 加载失败', errorData.error || '无法加载目录内容', 'error');
            }
        } catch (error) {
            showToast('✗ 加载失败', error.message, 'error');
        }
    }

    // 渲染目录内容
    function renderDirectoryContents(items, dirPath) {
        DOMCache.fileTree.innerHTML = '';

        const parentPath = dirPath.substring(0, dirPath.lastIndexOf('/'));
        const parentItem = document.createElement('li');
        parentItem.className = 'mb-2';
        parentItem.innerHTML = `
            <div class="text-primary px-2 py-1 fw-bold small" 
                 style="cursor:pointer;" 
                 onclick="window.ConfigManager.browseUpDirectory('${parentPath}')">
                <i class="fas fa-level-up-alt me-2"></i>返回上级
            </div>
            <div class="text-muted small px-2 mb-2 font-monospace bg-light rounded py-1 text-truncate" 
                 title="${dirPath}">${dirPath}</div>
        `;
        DOMCache.fileTree.appendChild(parentItem);

        const sortedItems = [...items].sort((a, b) => {
            if (a.type === 'directory' && b.type !== 'directory') return -1;
            if (a.type !== 'directory' && b.type === 'directory') return 1;
            return a.name.localeCompare(b.name);
        });

        sortedItems.forEach(item => {
            const itemNode = document.createElement('li');
            itemNode.className = 'd-flex justify-content-between align-items-center mb-1 rounded';

            const iconClass = item.type === 'directory' ? 'fa-folder' : 'fa-file';
            const textClass = item.type === 'directory' ? 'text-warning' : 'text-secondary';
            const displayName = item.name.length > 25 ? item.name.substring(0, 22) + '...' : item.name;

            itemNode.innerHTML = `
                <div class="text-truncate px-2 py-1 w-100 file-item-hover" 
                     style="cursor:pointer; font-size: 0.85rem;" 
                     onclick="window.ConfigManager.handleFileClick('${item.path}', '${item.type}')">
                    <i class="fas ${iconClass} me-2 ${textClass}" style="width: 16px;"></i>${displayName}
                </div>
                ${item.type !== 'directory' ? `
                    <button class="btn btn-link text-danger p-0 ms-1 opacity-50 hover-opacity-100" 
                            style="font-size:0.8rem;" 
                            onclick="window.ConfigManager.deleteConfigFile('${item.path}', event)">
                        <i class="fas fa-times"></i>
                    </button>
                ` : ''}
            `;
            DOMCache.fileTree.appendChild(itemNode);
        });
    }

    // 返回上级目录
    function browseUpDirectory(path) {
        if (!path && path !== '') {
            if (currentServiceName) loadFileTree(currentServiceName);
            return;
        }
        browseDirectory(path);
    }

    // 加载文件内容
    async function loadFileContent(filePath) {
        try {
            const normalizedPath = filePath.replace(/\\/g, '/');
            const serverId = DOMCache.serverSelector.value;
            if (!serverId) {
                showToast('⚠ 选择服务器', '未选择服务器', 'warning');
                return;
            }

            const response = await fetch(`/config/files/${encodeURIComponent(normalizedPath)}?server_id=${serverId}`);
            if (!response.ok) throw new Error('加载失败');

            const fileData = await response.json();
            currentFilePath = normalizedPath;

            if (window.editor) {
                window.editor.setValue(fileData.content || '');
                window.editor.focus();
                window.editor.revealLine(1);
            }

            DOMCache.currentFileName.textContent = normalizedPath.split('/').pop();
            DOMCache.lastSavedTime.textContent = '';
            DOMCache.saveFileBtn.disabled = true;
            DOMCache.compareBtn.disabled = false;
            DOMCache.backupListBtn.disabled = false;
        } catch (error) {
            showToast('✗ 加载失败', error.message, 'error');
        }
    }

    // 保存当前文件
    async function saveCurrentFile() {
        if (!currentFilePath) {
            showToast('⚠', '请先选择要保存的文件', 'warning');
            return;
        }

        const serverId = DOMCache.serverSelector.value;
        if (!serverId) {
            showToast('⚠', '未选择服务器', 'warning');
            return;
        }

        DOMCache.saveFileBtn.disabled = true;
        DOMCache.saveFileBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 保存中';

        try {
            const content = window.editor.getValue();
            const response = await fetch(`/config/files/${encodeURIComponent(currentFilePath)}?server_id=${serverId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });

            if (response.ok) {
                DOMCache.lastSavedTime.textContent = `已保存 ${new Date().toLocaleTimeString()}`;
                showToast('✓ 保存成功', '文件已更新并备份', 'success');
                window.LogManager.addOperationLog('保存文件', `文件保存成功: ${currentFilePath}`);
                if (currentServiceName) loadFileTree(currentServiceName);
            } else {
                throw new Error('保存失败');
            }
        } catch (error) {
            showToast('✗ 保存失败', error.message, 'error');
            window.LogManager.addOperationLog('保存文件', `保存失败: ${error.message}`);
            DOMCache.saveFileBtn.disabled = false;
        } finally {
            if (DOMCache.saveFileBtn.innerHTML.includes('保存中')) {
                DOMCache.saveFileBtn.innerHTML = '<i class="fas fa-save me-1"></i> 保存更改';
            }
        }
    }

    // 删除配置文件
    async function deleteConfigFile(filePath, event) {
        event.stopPropagation();
        const serverId = DOMCache.serverSelector.value;

        const isDirectory = event.target.closest('li').querySelector('.fa-folder') !== null;
        const type = isDirectory ? '文件夹' : '文件';

        if (!confirm(`确定要删除${type} "${filePath}" 吗？\n\n删除后将无法恢复，请确认！`)) return;

        try {
            const response = await fetch(`/config/files/${encodeURIComponent(filePath)}?server_id=${serverId}`, { method: 'DELETE' });
            if (response.ok) {
                showToast('✓ 删除成功', `${type}已删除`, 'success');
                window.LogManager.addOperationLog('删除文件', `${type}已删除: ${filePath}`);
                if (currentServiceName) loadFileTree(currentServiceName);
            } else {
                const errorData = await response.json();
                showToast('✗ 删除失败', errorData.error, 'error');
            }
        } catch (error) {
            showToast('✗ 删除失败', error.message, 'error');
        }
    }

    // 公共 API
    return {
        openConfig,
        loadFileTree,
        handleFileClick,
        browseDirectory,
        browseUpDirectory,
        loadFileContent,
        saveCurrentFile,
        deleteConfigFile,
        getCurrentFilePath: () => currentFilePath
    };
})();

// 导出到全局
window.ConfigManager = ConfigManager;
