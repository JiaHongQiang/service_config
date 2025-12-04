"""
配置文件管理模块
提供应用程序配置管理功能
"""

import os
from typing import Any, Optional
from json_manager import JSONFileManager


class ConfigManager:
    """
    配置管理器
    管理应用程序的各种配置文件
    """
    
    def __init__(self, config_dir: str = 'data'):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = config_dir
        os.makedirs(config_dir, exist_ok=True)
        
        # 配置文件管理器缓存
        self._managers = {}
    
    def _get_manager(self, config_name: str) -> JSONFileManager:
        """
        获取或创建配置文件管理器
        
        Args:
            config_name: 配置文件名（不含扩展名）
        
        Returns:
            JSON文件管理器实例
        """
        if config_name not in self._managers:
            file_path = os.path.join(self.config_dir, f"{config_name}.json")
            self._managers[config_name] = JSONFileManager(file_path, auto_backup=True)
        
        return self._managers[config_name]
    
    def get(self, config_name: str, key: str = None, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            config_name: 配置文件名
            key: 配置键（如果为 None，返回整个配置）
            default: 默认值
        
        Returns:
            配置值或默认值
        """
        manager = self._get_manager(config_name)
        config = manager.read(default={})
        
        if key is None:
            return config
        
        return config.get(key, default)
    
    def set(self, config_name: str, key: str, value: Any) -> bool:
        """
        设置配置值
        
        Args:
            config_name: 配置文件名
            key: 配置键
            value: 配置值
        
        Returns:
            是否设置成功
        """
        manager = self._get_manager(config_name)
        
        def updater(config):
            if config is None:
                config = {}
            config[key] = value
            return config
        
        return manager.update(updater, default={})
    
    def update(self, config_name: str, updates: dict) -> bool:
        """
        批量更新配置
        
        Args:
            config_name: 配置文件名
            updates: 更新字典
        
        Returns:
            是否更新成功
        """
        manager = self._get_manager(config_name)
        
        def updater(config):
            if config is None:
                config = {}
            config.update(updates)
            return config
        
        return manager.update(updater, default={})
    
    def delete(self, config_name: str, key: str) -> bool:
        """
        删除配置项
        
        Args:
            config_name: 配置文件名
            key: 配置键
        
        Returns:
            是否删除成功
        """
        manager = self._get_manager(config_name)
        
        def updater(config):
            if config and key in config:
                del config[key]
            return config
        
        return manager.update(updater, default={})
    
    def reset(self, config_name: str) -> bool:
        """
        重置配置文件
        
        Args:
            config_name: 配置文件名
        
        Returns:
            是否重置成功
        """
        manager = self._get_manager(config_name)
        return manager.write({})
    
    def backup(self, config_name: str) -> Optional[str]:
        """
        备份配置文件
        
        Args:
            config_name: 配置文件名
        
        Returns:
            备份文件路径，失败返回 None
        """
        manager = self._get_manager(config_name)
        return manager.create_backup()
    
    def list_backups(self, config_name: str) -> list:
        """
        列出配置文件备份
        
        Args:
            config_name: 配置文件名
        
        Returns:
            备份列表
        """
        manager = self._get_manager(config_name)
        return manager.list_backups()
    
    def restore(self, config_name: str, backup_path: str) -> bool:
        """
        恢复配置文件
        
        Args:
            config_name: 配置文件名
            backup_path: 备份文件路径
        
        Returns:
            是否恢复成功
        """
        manager = self._get_manager(config_name)
        return manager.restore_from_backup(backup_path)


# ==========================
# 应用程序配置类
# ==========================

class AppConfig:
    """
    应用程序配置
    提供类型安全的配置访问
    """
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.config_name = 'app_config'
    
    @property
    def secret_key(self) -> str:
        """获取密钥"""
        return self.config_manager.get(
            self.config_name,
            'secret_key',
            'your-secret-key-here'
        )
    
    @secret_key.setter
    def secret_key(self, value: str):
        """设置密钥"""
        self.config_manager.set(self.config_name, 'secret_key', value)
    
    @property
    def debug(self) -> bool:
        """是否启用调试模式"""
        return self.config_manager.get(self.config_name, 'debug', False)
    
    @debug.setter
    def debug(self, value: bool):
        """设置调试模式"""
        self.config_manager.set(self.config_name, 'debug', value)
    
    @property
    def host(self) -> str:
        """获取主机地址"""
        return self.config_manager.get(self.config_name, 'host', '0.0.0.0')
    
    @host.setter
    def host(self, value: str):
        """设置主机地址"""
        self.config_manager.set(self.config_name, 'host', value)
    
    @property
    def port(self) -> int:
        """获取端口"""
        return self.config_manager.get(self.config_name, 'port', 5000)
    
    @port.setter
    def port(self, value: int):
        """设置端口"""
        self.config_manager.set(self.config_name, 'port', value)
    
    @property
    def ssh_timeout(self) -> int:
        """SSH连接超时时间（秒）"""
        return self.config_manager.get(self.config_name, 'ssh_timeout', 8)
    
    @ssh_timeout.setter
    def ssh_timeout(self, value: int):
        """设置SSH超时时间"""
        self.config_manager.set(self.config_name, 'ssh_timeout', value)
    
    @property
    def max_backup_count(self) -> int:
        """最大备份文件数量"""
        return self.config_manager.get(self.config_name, 'max_backup_count', 10)
    
    @max_backup_count.setter
    def max_backup_count(self, value: int):
        """设置最大备份数量"""
        self.config_manager.set(self.config_name, 'max_backup_count', value)
    
    def get_all(self) -> dict:
        """获取所有配置"""
        return self.config_manager.get(self.config_name, default={})
    
    def update_all(self, config: dict) -> bool:
        """批量更新配置"""
        return self.config_manager.update(self.config_name, config)


# ==========================
# 错误模式配置类
# ==========================

class ErrorPatternsConfig:
    """
    错误模式配置
    管理日志错误检测模式
    """
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.config_name = 'error_patterns'
    
    def get_patterns(self) -> list:
        """获取所有错误模式"""
        return self.config_manager.get(self.config_name, default=[])
    
    def add_pattern(self, keyword: str, name: str) -> bool:
        """
        添加错误模式
        
        Args:
            keyword: 关键字
            name: 模式名称
        
        Returns:
            是否添加成功
        """
        def updater(patterns):
            if patterns is None:
                patterns = []
            
            # 检查是否已存在
            if any(p.get('keyword') == keyword or p.get('name') == name for p in patterns):
                return patterns
            
            patterns.append({'keyword': keyword, 'name': name})
            return patterns
        
        manager = self.config_manager._get_manager(self.config_name)
        return manager.update(updater, default=[])
    
    def remove_pattern(self, keyword: str) -> bool:
        """
        删除错误模式
        
        Args:
            keyword: 关键字
        
        Returns:
            是否删除成功
        """
        def updater(patterns):
            if patterns is None:
                return []
            return [p for p in patterns if p.get('keyword') != keyword]
        
        manager = self.config_manager._get_manager(self.config_name)
        return manager.update(updater, default=[])
    
    def update_patterns(self, patterns: list) -> bool:
        """
        批量更新错误模式
        
        Args:
            patterns: 错误模式列表
        
        Returns:
            是否更新成功
        """
        manager = self.config_manager._get_manager(self.config_name)
        return manager.write(patterns)


# ==========================
# 全局配置实例
# ==========================

# 创建全局配置管理器
config_manager = ConfigManager()

# 创建应用配置实例
app_config = AppConfig(config_manager)

# 创建错误模式配置实例
error_patterns_config = ErrorPatternsConfig(config_manager)


# ==========================
# 使用示例
# ==========================

"""
# 1. 使用应用配置
from config_manager import app_config

# 获取配置
secret = app_config.secret_key
debug = app_config.debug
port = app_config.port

# 设置配置
app_config.secret_key = "new-secret-key"
app_config.debug = True
app_config.port = 8000

# 批量更新
app_config.update_all({
    'debug': False,
    'port': 5000,
    'host': '127.0.0.1'
})


# 2. 使用错误模式配置
from config_manager import error_patterns_config

# 获取所有模式
patterns = error_patterns_config.get_patterns()

# 添加模式
error_patterns_config.add_pattern('ERROR', '错误')
error_patterns_config.add_pattern('Exception', '异常')

# 删除模式
error_patterns_config.remove_pattern('ERROR')

# 批量更新
new_patterns = [
    {'keyword': 'ERROR', 'name': '错误'},
    {'keyword': 'WARN', 'name': '警告'}
]
error_patterns_config.update_patterns(new_patterns)


# 3. 使用通用配置管理器
from config_manager import config_manager

# 获取配置
value = config_manager.get('my_config', 'key1', default='default_value')

# 设置配置
config_manager.set('my_config', 'key1', 'new_value')

# 批量更新
config_manager.update('my_config', {'key1': 'value1', 'key2': 'value2'})

# 删除配置项
config_manager.delete('my_config', 'key1')

# 备份配置
backup_path = config_manager.backup('my_config')

# 恢复配置
config_manager.restore('my_config', backup_path)
"""
