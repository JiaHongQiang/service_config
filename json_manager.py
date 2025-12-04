"""
JSON 文件管理工具类
提供线程安全的 JSON 文件读写操作
"""

import os
import json
import threading
from typing import Any, Optional, Callable
from datetime import datetime
import shutil


class JSONFileManager:
    """
    JSON 文件管理器
    提供线程安全的 JSON 文件读写、备份和恢复功能
    """
    
    def __init__(self, file_path: str, auto_backup: bool = True, backup_dir: str = None):
        """
        初始化 JSON 文件管理器
        
        Args:
            file_path: JSON 文件路径
            auto_backup: 是否自动备份
            backup_dir: 备份目录（默认为文件所在目录的 backup 子目录）
        """
        self.file_path = file_path
        self.auto_backup = auto_backup
        self.backup_dir = backup_dir or os.path.join(os.path.dirname(file_path), 'backup')
        self._lock = threading.RLock()  # 可重入锁，支持同一线程多次获取
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
        if auto_backup:
            os.makedirs(self.backup_dir, exist_ok=True)
    
    def read(self, default: Any = None) -> Any:
        """
        读取 JSON 文件
        
        Args:
            default: 文件不存在或读取失败时的默认返回值
        
        Returns:
            JSON 数据或默认值
        """
        with self._lock:
            try:
                if not os.path.exists(self.file_path):
                    return default
                
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"JSON 解析错误: {self.file_path}, 错误: {e}")
                return default
            except Exception as e:
                print(f"读取文件失败: {self.file_path}, 错误: {e}")
                return default
    
    def write(self, data: Any, indent: int = 4, create_backup: bool = None) -> bool:
        """
        写入 JSON 文件
        
        Args:
            data: 要写入的数据
            indent: 缩进空格数
            create_backup: 是否创建备份（默认使用 auto_backup 设置）
        
        Returns:
            是否写入成功
        """
        with self._lock:
            try:
                # 如果设置了自动备份，先备份现有文件
                if (create_backup is True) or (create_backup is None and self.auto_backup):
                    self.create_backup()
                
                # 写入临时文件
                temp_file = f"{self.file_path}.tmp"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=indent)
                
                # 原子性替换
                if os.path.exists(self.file_path):
                    os.replace(temp_file, self.file_path)
                else:
                    os.rename(temp_file, self.file_path)
                
                return True
            except Exception as e:
                print(f"写入文件失败: {self.file_path}, 错误: {e}")
                # 清理临时文件
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                return False
    
    def update(self, updater: Callable[[Any], Any], default: Any = None) -> bool:
        """
        原子性更新 JSON 文件
        读取 → 修改 → 写入过程中持有锁，确保线程安全
        
        Args:
            updater: 更新函数，接收当前数据，返回新数据
            default: 文件不存在时的默认值
        
        Returns:
            是否更新成功
        """
        with self._lock:
            try:
                # 读取当前数据
                current_data = self.read(default)
                
                # 应用更新函数
                new_data = updater(current_data)
                
                # 写入新数据
                return self.write(new_data)
            except Exception as e:
                print(f"更新文件失败: {self.file_path}, 错误: {e}")
                return False
    
    def create_backup(self) -> Optional[str]:
        """
        创建文件备份
        
        Returns:
            备份文件路径，如果备份失败则返回 None
        """
        with self._lock:
            try:
                if not os.path.exists(self.file_path):
                    return None
                
                # 生成备份文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = os.path.basename(self.file_path)
                name, ext = os.path.splitext(filename)
                backup_filename = f"{name}_backup_{timestamp}{ext}"
                backup_path = os.path.join(self.backup_dir, backup_filename)
                
                # 复制文件
                shutil.copy2(self.file_path, backup_path)
                print(f"已创建备份: {backup_path}")
                
                return backup_path
            except Exception as e:
                print(f"创建备份失败: {self.file_path}, 错误: {e}")
                return None
    
    def list_backups(self) -> list:
        """
        列出所有备份文件
        
        Returns:
            备份文件列表，按时间倒序排列
        """
        try:
            if not os.path.exists(self.backup_dir):
                return []
            
            filename = os.path.basename(self.file_path)
            name, ext = os.path.splitext(filename)
            prefix = f"{name}_backup_"
            
            backups = []
            for f in os.listdir(self.backup_dir):
                if f.startswith(prefix) and f.endswith(ext):
                    full_path = os.path.join(self.backup_dir, f)
                    backups.append({
                        'filename': f,
                        'path': full_path,
                        'mtime': os.path.getmtime(full_path),
                        'size': os.path.getsize(full_path)
                    })
            
            # 按修改时间倒序排序
            backups.sort(key=lambda x: x['mtime'], reverse=True)
            return backups
        except Exception as e:
            print(f"列出备份失败: {e}")
            return []
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """
        从备份恢复文件
        
        Args:
            backup_path: 备份文件路径
        
        Returns:
            是否恢复成功
        """
        with self._lock:
            try:
                if not os.path.exists(backup_path):
                    print(f"备份文件不存在: {backup_path}")
                    return False
                
                # 备份当前文件
                self.create_backup()
                
                # 恢复备份
                shutil.copy2(backup_path, self.file_path)
                print(f"已从备份恢复: {backup_path}")
                
                return True
            except Exception as e:
                print(f"恢复备份失败: {e}")
                return False
    
    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        清理旧备份文件，只保留最近的 N 个
        
        Args:
            keep_count: 保留的备份数量
        
        Returns:
            删除的备份数量
        """
        try:
            backups = self.list_backups()
            if len(backups) <= keep_count:
                return 0
            
            # 删除超出数量的旧备份
            deleted_count = 0
            for backup in backups[keep_count:]:
                try:
                    os.remove(backup['path'])
                    deleted_count += 1
                    print(f"已删除旧备份: {backup['filename']}")
                except Exception as e:
                    print(f"删除备份失败: {backup['filename']}, 错误: {e}")
            
            return deleted_count
        except Exception as e:
            print(f"清理备份失败: {e}")
            return 0
    
    def exists(self) -> bool:
        """检查文件是否存在"""
        return os.path.exists(self.file_path)
    
    def delete(self) -> bool:
        """
        删除文件
        
        Returns:
            是否删除成功
        """
        with self._lock:
            try:
                if os.path.exists(self.file_path):
                    # 删除前创建备份
                    self.create_backup()
                    os.remove(self.file_path)
                    print(f"已删除文件: {self.file_path}")
                    return True
                return False
            except Exception as e:
                print(f"删除文件失败: {self.file_path}, 错误: {e}")
                return False


# ==========================
# 使用示例
# ==========================

"""
# 1. 基本使用
manager = JSONFileManager('data/servers.json')

# 读取数据
servers = manager.read(default=[])

# 写入数据
manager.write(servers)

# 2. 原子性更新
def add_server(servers):
    servers.append({'id': '1', 'name': 'Server1'})
    return servers

manager.update(add_server, default=[])

# 3. 备份管理
# 创建备份
manager.create_backup()

# 列出备份
backups = manager.list_backups()

# 恢复备份
manager.restore_from_backup(backups[0]['path'])

# 清理旧备份
manager.cleanup_old_backups(keep_count=5)
"""
