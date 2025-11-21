import os
import json
import stat
import time
from typing import Optional, Dict, Any
import paramiko
from flask import jsonify, session


def get_user_servers_file(user_id: str) -> str:
    """根据用户ID生成对应的服务器配置文件路径"""
    return f'data/servers_{user_id}.json'


def get_error_patterns_file() -> str:
    """获取错误日志模式配置文件路径"""
    return 'data/error_log_patterns.json'


def decode_line(line) -> str:
    """解码日志行内容，支持多种字符编码"""
    # 如果已经是字符串，直接返回
    if isinstance(line, str):
        return line
    
    # 尝试多种常见字符编码进行解码
    encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin1', 'ascii']
    for encoding in encodings:
        try:
            return line.decode(encoding)
        except (UnicodeDecodeError, AttributeError):
            # 解码失败，尝试下一种编码
            continue
    
    # 如果所有编码都失败，使用UTF-8忽略错误模式解码
    try:
        return line.decode('utf-8', errors='ignore')
    except:
        # 最后手段，转换为字符串表示
        return str(line)


def format_ssh_error(error) -> str:
    """格式化SSH连接错误信息，提供更友好的中文提示"""
    error_msg = str(error)
    
    # 根据不同的错误类型返回相应的中文提示
    if "Administratively prohibited" in error_msg:
        return "操作被拒绝（请重新连接）"
    elif "Permission denied" in error_msg:
        return "权限被拒绝"
    elif "No such file" in error_msg:
        return "文件或目录不存在"
    elif "Network is unreachable" in error_msg:
        return "网络不可达"
    elif "Connection refused" in error_msg:
        return "连接被拒绝"
    elif "Authentication failed" in error_msg:
        return "身份验证失败"
    elif "timed out" in error_msg.lower():
        return "连接超时"
    else:
        # 未识别的错误类型，返回原始错误信息
        return error_msg


def get_ssh_client(server_id: str, active_connections: dict):
    """获取指定服务器的SSH客户端连接"""
    # 检查用户是否已登录
    if 'user_id' not in session:
        return None, jsonify({"error": "用户未登录"}), 401
    
    # 构造用户-服务器唯一标识
    user_server_id = f"{session['user_id']}-{server_id}"
    
    # 检查服务器ID是否为空
    if not server_id:
        return None, jsonify({"error": "Missing server_id"}), 400
    
    # 从活跃连接中查找对应SSH客户端
    client = active_connections.get(user_server_id)
    
    # 如果找不到对应连接，返回错误
    if not client:
        return None, jsonify({"error": "该服务器未连接"}), 400
    
    # 返回SSH客户端连接
    return client, None, None


def load_servers():
    """加载当前用户的服务器配置列表"""
    # 检查用户是否已登录
    if 'user_id' not in session:
        return []
    
    # 获取当前用户的服务器配置文件路径
    servers_file = get_user_servers_file(session['user_id'])
    
    try:
        # 如果配置文件不存在，返回空列表
        if not os.path.exists(servers_file):
            return []
        
        # 读取并解析JSON格式的服务器配置文件
        with open(servers_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        # 发生异常时返回空列表
        return []


def save_servers(servers):
    """保存服务器配置列表到文件"""
    # 检查用户是否已登录
    if 'user_id' not in session:
        return False
    
    # 获取当前用户的服务器配置文件路径
    servers_file = get_user_servers_file(session['user_id'])
    
    # 确保数据目录存在
    os.makedirs('data', exist_ok=True)
    
    # 将服务器配置写入文件，使用UTF-8编码和4空格缩进
    with open(servers_file, 'w', encoding='utf-8') as f:
        json.dump(servers, f, ensure_ascii=False, indent=4)
    
    return True


def find_server(server_id):
    """根据服务器ID查找服务器配置"""
    servers = load_servers()
    # 使用生成器表达式查找匹配的服务器配置
    return next((s for s in servers if str(s["id"]) == str(server_id)), None)