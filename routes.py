import os
import json
import stat

import paramiko
from flask import Blueprint, jsonify, request, render_template, session, redirect
from models import UserManager
from functools import wraps
from difflib import unified_diff
import time
import threading

# ==========================
# Blueprint 配置
# ==========================
api_bp = Blueprint('api', __name__)

# ==========================
# 全局变量
# ==========================
# 服务器配置文件路径将根据用户ID动态生成
active_connections = {}                 # 存储每个 server_id 的 SSH 连接，key为 user_id-server_id
log_watchers = {}                       # 存储日志监听器
detected_errors = {}                    # 存储检测到的错误日志

# 模拟服务列表
services = [
    {"name": "sie", "display_name": "流媒体服务", "config_path": "/home/hy_media_server/conf/", "log_path": "/home/hy_media_server/log/666-1/run/log-666-1-run.log", "has_config": True},
    {"name": "vss", "display_name": "业务服务", "config_path": "/home/hy_media_server/conf/", "log_path": "", "has_config": True},
    {"name": "nginx", "display_name": "Nginx", "config_path": "/opt/nginx/conf/", "log_path": "", "has_config": True},
    {"name": "nginxd", "display_name": "NginxD", "config_path": "/opt/nginx/conf/", "log_path": "", "has_config": True},
    {"name": "lkdc", "display_name": "密钥管理服务", "config_path": "", "log_path": "", "has_config": False},
    {"name": "hy_file_server", "display_name": "文件服务", "config_path": "/home/hy_file_server/", "log_path": "", "has_config": True},
    {"name": "hy_message_push_server", "display_name": "离线推送服务", "config_path": "/home/hy_message_push_server/", "log_path": "", "has_config": True}
]

# 初始化用户管理器
user_manager = UserManager('data')

# ==========================
# 工具函数
# ==========================
def login_required(f):
    """装饰器：确保用户已登录"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查请求类型
        if request.headers.get('Content-Type', '').startswith('application/json') or \
           request.headers.get('Accept', '').find('application/json') != -1:
            # API请求，返回JSON响应
            if 'user_id' not in session:
                return jsonify({"error": "用户未登录"}), 401
        else:
            # HTML页面请求，重定向到登录页
            if 'user_id' not in session:
                return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def get_user_servers_file(user_id: str) -> str:
    """根据用户ID生成服务器配置文件路径"""
    return f'data/servers_{user_id}.json'

def get_error_patterns_file() -> str:
    """获取错误日志模式文件路径"""
    return 'data/error_log_patterns.json'

def get_ssh_client(server_id: str):
    """
    根据 server_id 获取 SSH 连接
    返回 (client, 错误响应, HTTP 状态码)
    """
    # 检查用户是否已登录
    if 'user_id' not in session:
        return None, jsonify({"error": "用户未登录"}), 401
        
    user_server_id = f"{session['user_id']}-{server_id}"
    
    if not server_id:
        return None, jsonify({"error": "Missing server_id"}), 400
    client = active_connections.get(user_server_id)
    if not client:
        return None, jsonify({"error": "该服务器未连接"}), 400
    return client, None, None


def load_servers():
    """读取当前用户的服务器列表"""
    # 检查用户是否已登录
    if 'user_id' not in session:
        return []
        
    servers_file = get_user_servers_file(session['user_id'])
    try:
        if not os.path.exists(servers_file):
            return []
        with open(servers_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def save_servers(servers):
    """保存当前用户的服务器列表"""
    # 检查用户是否已登录
    if 'user_id' not in session:
        return False
        
    servers_file = get_user_servers_file(session['user_id'])
    os.makedirs('data', exist_ok=True)
    with open(servers_file, 'w', encoding='utf-8') as f:
        json.dump(servers, f, ensure_ascii=False, indent=4)
    return True


def find_server(server_id):
    """根据 server_id 查找服务器配置"""
    servers = load_servers()
    return next((s for s in servers if str(s["id"]) == str(server_id)), None)

# ==========================
# 用户认证接口
# ==========================
@api_bp.route('/auth/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"error": "用户名和密码不能为空"}), 400
            
        user = user_manager.create_user(username, password)
        if not user:
            return jsonify({"error": "用户已存在"}), 400
            
        return jsonify({"message": "注册成功", "user_id": user.user_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"error": "用户名和密码不能为空"}), 400
            
        user = user_manager.authenticate_user(username, password)
        if not user:
            return jsonify({"error": "用户名或密码错误"}), 401
            
        # 创建会话
        session_id = user_manager.create_session(user)
        session['user_id'] = user.user_id
        session['session_id'] = session_id
        
        return jsonify({
            "message": "登录成功", 
            "user_id": user.user_id,
            "username": user.username
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/auth/logout', methods=['POST'])
@login_required
def logout():
    """用户登出"""
    try:
        if 'session_id' in session:
            user_manager.destroy_session(session['session_id'])
            
        session.clear()
        return jsonify({"message": "已登出"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/auth/status', methods=['GET'])
def auth_status():
    """检查认证状态"""
    if 'user_id' in session:
        user = user_manager.get_user_by_id(session['user_id'])
        if user:
            return jsonify({
                "logged_in": True,
                "user_id": user.user_id,
                "username": user.username
            }), 200
    
    return jsonify({"logged_in": False}), 401

# ==========================
# 页面路由
# ==========================
@api_bp.route('/')
@login_required
def index():
    return render_template('index.html')

@api_bp.route('/login')
def login_page():
    # 如果用户已登录，重定向到主页
    if 'user_id' in session:
        return render_template('index.html')
    return render_template('login.html')

# ==========================
# 基础接口
# ==========================
@api_bp.route('/servers', methods=['GET'])
@login_required
def get_servers():
    """获取服务器列表"""
    try:
        return jsonify(load_servers())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/servers', methods=['POST'])
@login_required
def add_server():
    """添加服务器"""
    try:
        new_server = request.json
        servers = load_servers()
        if any(s["id"] == new_server["id"] for s in servers):
            return jsonify({"error": "服务器ID已存在"}), 400
        servers.append(new_server)
        save_servers(servers)
        return jsonify(new_server), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/servers/<server_id>', methods=['DELETE'])
@login_required
def delete_server(server_id):
    """删除服务器配置"""
    try:
        servers = load_servers()
        updated = [s for s in servers if str(s["id"]) != str(server_id)]
        if len(updated) == len(servers):
            return jsonify({"error": "未找到该服务器"}), 404
        save_servers(updated)
        # 关闭 SSH 连接
        user_server_id = f"{session['user_id']}-{server_id}"
        if user_server_id in active_connections:
            active_connections[user_server_id].close()
            del active_connections[user_server_id]
        return jsonify({"message": "删除成功"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================
# SSH 连接
# ==========================
@api_bp.route('/servers/<server_id>/connect', methods=['POST'])
@login_required
def connect_server(server_id):
    """连接服务器并保存 SSH 会话"""
    target = find_server(server_id)
    if not target:
        return jsonify({"error": "服务器不存在"}), 404

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=target["host"],
            port=int(target["port"]),
            username=target["username"],
            password=target["password"],
            timeout=8
        )
        user_server_id = f"{session['user_id']}-{server_id}"
        active_connections[user_server_id] = ssh
        return jsonify({"message": f"已成功连接到 {target['name']} ({target['host']})", "server_id": server_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================
# 服务状态
# ==========================
@api_bp.route('/services/status', methods=['GET'])
@login_required
def get_services_status():
    """获取服务状态"""
    server_id = request.args.get('server_id')
    if not server_id:
        return jsonify({"error": "缺少 server_id 参数"}), 400
    
    ssh, err, code = get_ssh_client(server_id)
    if err:
        return err, code

    try:
        result = []
        for s in services:
            # 检查服务是否存在
            stdin, stdout, stderr = ssh.exec_command(f"systemctl list-unit-files | grep -w {s['name']}.service")
            service_exists = stdout.read().decode().strip()
            
            # 如果服务存在，获取其状态
            if service_exists:
                stdin, stdout, stderr = ssh.exec_command(f"sudo systemctl is-active {s['name']}")
                status = stdout.read().decode().strip()
                if status == "active":
                    color = "status-running"
                elif status in ["inactive", "failed"]:
                    color = "status-stopped"
                else:
                    color = "status-unknown"
                result.append({
                    **s,
                    "status": status,
                    "status_indicator": color
                })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================
# 启停重启服务
# ==========================
@api_bp.route('/services/<service_name>/<action>', methods=['POST'])
@login_required
def service_action(service_name, action):
    """操作服务: start/stop/restart"""
    server_id = request.args.get('server_id')
    ssh, err, code = get_ssh_client(server_id)
    if err:
        return err, code

    if action not in ["start", "stop", "restart"]:
        return jsonify({"error": "Invalid action"}), 400

    try:
        # 获取服务信息
        service_info = next((s for s in services if s["name"] == service_name), None)
        log_path = service_info.get("log_path", "") if service_info else ""
        
        # 如果是启动操作且有日志路径，则启动日志监听
        if action == "start" and log_path and server_id:
            start_log_watcher(server_id, service_name, log_path)
        
        cmd = f"sudo systemctl {action} {service_name}"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        err_out = stderr.read().decode()
        if exit_code == 0:
            return jsonify({"message": f"{service_name} {action} 成功", "output": out})
        else:
            return jsonify({"error": err_out or "命令执行失败"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def start_log_watcher(server_id, service_name, log_path):
    """启动日志监听器"""
    user_server_id = f"{session['user_id']}-{server_id}"
    watcher_id = f"{user_server_id}-{service_name}"
    
    # 如果已经存在监听器，则先停止
    if watcher_id in log_watchers:
        log_watchers[watcher_id]['stop'] = True
    
    # 创建新的监听器
    watcher = {
        'stop': False,
        'service_name': service_name,
        'log_path': log_path
    }
    
    log_watchers[watcher_id] = watcher
    
    # 在新线程中启动监听
    thread = threading.Thread(target=watch_log, args=(user_server_id, watcher))
    thread.daemon = True
    thread.start()

def watch_log(user_server_id, watcher):
    """监听日志文件"""
    ssh = active_connections.get(user_server_id)
    if not ssh:
        return
    
    try:
        # 打开SFTP连接来读取日志文件
        sftp = ssh.open_sftp()
        
        # 获取错误模式
        error_patterns = []
        patterns_file = get_error_patterns_file()
        if os.path.exists(patterns_file):
            with open(patterns_file, 'r', encoding='utf-8') as f:
                error_patterns = json.load(f)
        
        # 为这个用户和服务初始化错误存储
        watcher_id = f"{user_server_id}-{watcher['service_name']}"
        if watcher_id not in detected_errors:
            detected_errors[watcher_id] = []
        
        # 读取日志文件末尾内容
        try:
            with sftp.open(watcher['log_path'], 'r') as f:
                # 跳转到文件末尾
                f.seek(0, 2)  # SEEK_END
                last_pos = f.tell()
                
                while not watcher['stop']:
                    f.seek(last_pos)
                    lines = f.readlines()
                    if lines:
                        last_pos = f.tell()
                        # 检查是否有错误模式匹配
                        for line in lines:
                            for pattern in error_patterns:
                                if pattern['keyword'] in line:
                                    # 记录匹配到的错误
                                    error_record = {
                                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                                        'service': watcher['service_name'],
                                        'error_name': pattern['name'],
                                        'log_line': line.strip()
                                    }
                                    # 保存错误记录
                                    detected_errors[watcher_id].append(error_record)
                                    # 保持最多100条错误记录
                                    if len(detected_errors[watcher_id]) > 100:
                                        detected_errors[watcher_id].pop(0)
                                    print(f"Error detected: {error_record}")
                    
                    time.sleep(1)  # 每秒检查一次
                    
        except FileNotFoundError:
            # 日志文件不存在，等待一段时间后重试
            time.sleep(5)
        finally:
            sftp.close()
            
    except Exception as e:
        print(f"Log watching error: {e}")

# ==========================
# 配置文件管理
# ==========================
@api_bp.route('/config/files', methods=['GET'])
@login_required
def get_config_files():
    """列出服务配置文件 - 增强版本"""
    server_id = request.args.get('server_id')
    ssh, err, code = get_ssh_client(server_id)
    if err:
        return err, code

    service_name = request.args.get('service')
    try:
        sftp = ssh.open_sftp()
        result = {}
        for s in services:
            if service_name and s["name"] != service_name:
                continue
            path = s["config_path"]
            if not path:
                result[s["name"]] = []
                continue
            try:
                files = sftp.listdir(path)
                result[s["name"]] = [os.path.join(path, f) for f in files]
            except Exception:
                result[s["name"]] = []
        sftp.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/config/files/<path:file_path>', methods=['GET'])
@login_required
def read_config_file(file_path):
    """读取配置文件内容"""
    server_id = request.args.get('server_id')
    ssh, err, code = get_ssh_client(server_id)
    if err:
        return err, code

    try:
        sftp = ssh.open_sftp()
        with sftp.open('/' + file_path, 'r') as f:
            content = f.read().decode('utf-8', errors='ignore')
        sftp.close()
        return jsonify({"path": file_path, "content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/config/files/<path:file_path>', methods=['POST'])
@login_required
def write_config_file(file_path):
    """写入配置文件内容"""
    server_id = request.args.get('server_id')
    ssh, err, code = get_ssh_client(server_id)
    if err:
        return err, code

    try:
        # 获取请求中的内容
        data = request.get_json()
        content = data.get('content', '')
        
        # 创建备份
        import time
        backup_path = f"/{file_path}.backup_{int(time.time())}"
        
        sftp = ssh.open_sftp()
        # 创建备份文件
        try:
            sftp.rename(f"/{file_path}", backup_path)
        except FileNotFoundError:
            # 如果原文件不存在，则不需要备份
            pass
        
        # 写入新内容
        with sftp.open(f"/{file_path}", 'w') as f:
            f.write(content)
        sftp.close()
        
        return jsonify({
            "message": "文件保存成功", 
            "backup_path": backup_path if 'backup_path' in locals() else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/config/files/<path:file_path>', methods=['DELETE'])
@login_required
def delete_config_file(file_path):
    """删除配置文件"""
    server_id = request.args.get('server_id')
    ssh, err, code = get_ssh_client(server_id)
    if err:
        return err, code

    try:
        sftp = ssh.open_sftp()
        # 尝试删除文件
        sftp.remove(f"/{file_path}")
        sftp.close()
        
        return jsonify({"message": f"文件 {file_path} 删除成功"})
    except FileNotFoundError:
        return jsonify({"error": "文件不存在"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 新增API端点用于获取检测到的错误日志
@api_bp.route('/services/<service_name>/errors', methods=['GET'])
@login_required
def get_service_errors(service_name):
    """获取服务的错误日志"""
    server_id = request.args.get('server_id')
    if not server_id:
        return jsonify({"error": "缺少 server_id 参数"}), 400
    
    user_server_id = f"{session['user_id']}-{server_id}"
    watcher_id = f"{user_server_id}-{service_name}"
    
    errors = detected_errors.get(watcher_id, [])
    return jsonify(errors)


# 在配置文件管理部分添加新路由
@api_bp.route('/config/compare', methods=['POST'])
@login_required
def compare_files():
    """对比两个文件或文件与服务器版本"""
    server_id = request.args.get('server_id')
    ssh, err, code = get_ssh_client(server_id)
    if err:
        return err, code

    try:
        data = request.get_json()
        file_path = data.get('file_path')
        local_content = data.get('local_content')

        if not file_path or local_content is None:
            return jsonify({"error": "缺少必要参数: file_path, local_content"}), 400

        # 从远程服务器读取文件
        sftp = ssh.open_sftp()
        try:
            with sftp.open('/' + file_path, 'r') as f:
                server_content = f.read().decode('utf-8', errors='ignore')
        except FileNotFoundError:
            server_content = ""
        finally:
            sftp.close()

        # 生成 unified diff 格式的对比结果
        server_lines = server_content.splitlines(keepends=True)
        local_lines = local_content.splitlines(keepends=True)

        diff_result = list(unified_diff(
            server_lines,
            local_lines,
            fromfile=f'服务器: {file_path}',
            tofile=f'本地: {file_path}',
            lineterm=''
        ))

        # 统计差异
        added_count = len([line for line in diff_result if line.startswith('+')])
        removed_count = len([line for line in diff_result if line.startswith('-')])

        return jsonify({
            "file_path": file_path,
            "server_content": server_content,
            "local_content": local_content,
            "diff": diff_result,
            "stats": {
                "added": added_count,
                "removed": removed_count,
                "total_changes": added_count + removed_count
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500