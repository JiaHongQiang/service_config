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
active_connections = {}  # 存储每个 server_id 的 SSH 连接，key为 user_id-server_id
log_watchers = {}  # 存储日志监听器
detected_errors = {}  # 存储检测到的错误日志
startup_trackers = {}  # 存储启动检测跟踪器

# 模拟服务列表 - 支持多路径日志
services = [
    {
        "name": "sie",
        "display_name": "流媒体服务",
        "config_path": "/home/hy_media_server/conf/",
        "log_paths": [
            "/home/hy_media_server/log/222-1/run/log-222-1-run.log",
            "/home/hy_media_server/log/222-1/interface/log-222-1-run.log",
            "/home/hy_media_server/log/666-1/run/log-666-1-run.log",
            "/home/hy_media_server/log/666-1/interface/log-666-1-run.log",
            "/home/hy_media_server/log/888-1/run/log-888-1-run.log",
            "/home/hy_media_server/log/888-1/interface/log-888-1-run.log",
            "/home/hy_media_server/log/999-1/run/log-999-1-run.log",
            "/home/hy_media_server/log/999-1/interface/log-999-1-run.log"
        ],
        "startup_check": {
            "enabled": True,
            "keyword": "启动成功",
            "required_count": 3,  # 需要3个不同日志文件都出现
            "timeout": 1.5  # 1.5秒超时
        },
        "has_config": True
    },
    {
        "name": "vss",
        "display_name": "业务服务",
        "config_path": "/home/hy_vss_biz_server/conf/",
        "log_paths": [
            "/home/hy_vss_biz_server/log/3000-1/run/log-3000-1-run.log",
            "/home/hy_vss_biz_server/log/3000-1/interface/log-3000-1-interface.log"
        ],
        "startup_check": {
            "enabled": False
        },
        "has_config": True
    },
    {"name": "nginx", "display_name": "Nginx", "config_path": "/opt/nginx/conf/", "log_paths": [
        "/opt/nginx/logs/error.log"], "startup_check": {"enabled": False}, "has_config": True},
    {"name": "nginxd", "display_name": "NginxD", "config_path": "/opt/nginx/conf/", "log_paths": [
        "/opt/nginx/logs/error.log"], "startup_check": {"enabled": False}, "has_config": True},
    {"name": "lkdc", "display_name": "密钥管理服务", "config_path": "", "log_paths": [],
     "startup_check": {"enabled": False}, "has_config": False},
    {"name": "hy_file_server", "display_name": "文件服务", "config_path": "/home/hy_file_server/", "log_paths": [],
     "startup_check": {"enabled": False}, "has_config": True},
    {"name": "hy_message_push_server", "display_name": "离线推送服务", "config_path": "/home/hy_message_push_server/",
     "log_paths": [], "startup_check": {"enabled": False}, "has_config": True}
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


def decode_line(line):
    """尝试多种编码方式解码日志行"""
    if isinstance(line, str):
        return line

    # 尝试的编码列表（按优先级）
    encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin1', 'ascii']

    for encoding in encodings:
        try:
            return line.decode(encoding)
        except (UnicodeDecodeError, AttributeError):
            continue

    # 如果所有编码都失败，使用 utf-8 并忽略错误
    try:
        return line.decode('utf-8', errors='ignore')
    except:
        return str(line)  # 最后的备选方案


def check_startup_status(tracker_key, log_path, line_str):
    """检查服务启动状态"""
    tracker = startup_trackers.get(tracker_key)
    if not tracker or tracker['reported']:
        return

    # 检查是否包含启动关键字
    if tracker['keyword'] in line_str:
        tracker['detected_files'].add(log_path)
        print(
            f"[STARTUP] Detected '{tracker['keyword']}' in {log_path} ({len(tracker['detected_files'])}/{tracker['required_count']})")

        # 检查是否达到要求数量
        if len(tracker['detected_files']) >= tracker['required_count']:
            # 达到要求，报告成功
            report_startup_result(tracker_key, True)
        return

    # 检查超时
    elapsed = time.time() - tracker['start_time']
    if elapsed > tracker['timeout']:
        # 超时，报告失败
        report_startup_result(tracker_key, False)


def report_startup_result(tracker_key, success):
    """报告启动结果"""
    tracker = startup_trackers.get(tracker_key)
    if not tracker or tracker['reported']:
        return

    tracker['reported'] = True

    # 解析 tracker_key 获取服务信息
    parts = tracker_key.rsplit('-', 1)
    user_server_id = parts[0]
    service_name = parts[1]

    # 创建一个虚拟的 watcher_id 用于存储统一的启动结果
    result_watcher_id = f"{tracker_key}-startup-result"

    if result_watcher_id not in detected_errors:
        detected_errors[result_watcher_id] = []

    if success:
        error_record = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'service': service_name,
            'log_file': 'all',  # 表示来自所有日志文件
            'error_name': '启动成功',
            'log_line': f'服务已在 {len(tracker["detected_files"])} 个日志文件中检测到启动成功',
            'detected_at': time.time()
        }
        print(f"✓ [STARTUP SUCCESS] {service_name} fully started")
    else:
        error_record = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'service': service_name,
            'log_file': 'all',
            'error_name': '启动超时',
            'log_line': f'超时 {tracker["timeout"]}s，只在 {len(tracker["detected_files"])}/{tracker["required_count"]} 个日志文件中检测到启动成功',
            'detected_at': time.time()
        }
        print(f"✗ [STARTUP TIMEOUT] {service_name} startup incomplete")

    detected_errors[result_watcher_id].append(error_record)


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
        # 关闭 SSH 连接和所有相关的日志监听器
        user_server_id = f"{session['user_id']}-{server_id}"
        if user_server_id in active_connections:
            active_connections[user_server_id].close()
            del active_connections[user_server_id]

        # 停止所有相关的日志监听器
        watchers_to_remove = [k for k in log_watchers if k.startswith(user_server_id)]
        for watcher_key in watchers_to_remove:
            log_watchers[watcher_key]['stop'] = True
            del log_watchers[watcher_key]

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
        log_paths = service_info.get("log_paths", []) if service_info else []

        # 如果是停止操作，先停止所有相关的日志监听器
        if action == "stop" and server_id:
            stop_log_watchers(server_id, service_name)

        # 执行服务操作
        cmd = f"sudo systemctl {action} {service_name}"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        err_out = stderr.read().decode()

        if exit_code == 0:
            # 如果是启动操作且有日志路径，则启动日志监听
            if action == "start" and log_paths and server_id:
                start_log_watchers(server_id, service_name, log_paths)

            return jsonify({"message": f"{service_name} {action} 成功", "output": out})
        else:
            return jsonify({"error": err_out or "命令执行失败"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def start_log_watchers(server_id, service_name, log_paths):
    """启动多个日志监听器 - 每个日志文件一个监听器"""
    user_server_id = f"{session['user_id']}-{server_id}"

    # 先停止所有已存在的监听器
    stop_log_watchers(server_id, service_name)

    # 获取服务配置
    service_info = next((s for s in services if s["name"] == service_name), None)
    startup_check = service_info.get("startup_check", {}) if service_info else {}

    # 初始化启动跟踪器（如果服务需要启动检查）
    tracker_key = f"{user_server_id}-{service_name}"
    if startup_check.get("enabled"):
        startup_trackers[tracker_key] = {
            'keyword': startup_check.get('keyword', '启动成功'),
            'required_count': startup_check.get('required_count', 3),
            'timeout': startup_check.get('timeout', 30),
            'start_time': time.time(),
            'detected_files': set(),  # 已检测到启动成功的日志文件
            'reported': False  # 是否已报告结果
        }

    # 为每个日志路径创建一个监听器
    for log_path in log_paths:
        if not log_path:  # 跳过空路径
            continue

        watcher_id = f"{user_server_id}-{service_name}-{hash(log_path)}"

        # 创建新的监听器
        watcher = {
            'stop': False,
            'service_name': service_name,
            'log_path': log_path,
            'tracker_key': tracker_key if startup_check.get("enabled") else None
        }

        log_watchers[watcher_id] = watcher

        # 在新线程中启动监听
        thread = threading.Thread(target=watch_log, args=(user_server_id, watcher, log_path))
        thread.daemon = True
        thread.start()

        print(f"Started log watcher for {service_name}: {log_path}")


def stop_log_watchers(server_id, service_name):
    """停止指定服务的所有日志监听器"""
    user_server_id = f"{session['user_id']}-{server_id}"
    prefix = f"{user_server_id}-{service_name}-"

    # 找到所有相关的监听器并停止
    watchers_to_stop = [k for k in log_watchers if k.startswith(prefix)]
    for watcher_key in watchers_to_stop:
        log_watchers[watcher_key]['stop'] = True
        print(f"Stopped log watcher: {watcher_key}")


def watch_log(user_server_id, watcher, log_path):
    """监听单个日志文件 - 只监控启动后的新日志"""
    ssh = active_connections.get(user_server_id)
    if not ssh:
        return

    # 为这个特定的日志文件创建唯一的错误存储键
    watcher_id = f"{user_server_id}-{watcher['service_name']}-{hash(log_path)}"

    try:
        # 打开SFTP连接来读取日志文件
        sftp = ssh.open_sftp()

        # 获取错误模式
        error_patterns = []
        patterns_file = get_error_patterns_file()
        if os.path.exists(patterns_file):
            with open(patterns_file, 'r', encoding='utf-8') as f:
                error_patterns = json.load(f)

        # 为这个日志文件初始化错误存储（清空旧的错误记录）
        detected_errors[watcher_id] = []

        # 记录监听开始时间
        start_time = time.time()
        print(f"Started watching log file at {time.strftime('%Y-%m-%d %H:%M:%S')}: {log_path}")

        # 读取日志文件末尾内容
        last_pos = 0
        file_opened = False

        while not watcher['stop']:
            try:
                # 使用二进制模式打开文件，避免自动解码
                with sftp.open(log_path, 'rb') as f:
                    if not file_opened:
                        # 首次打开，跳转到文件末尾（忽略历史日志）
                        f.seek(0, 2)  # SEEK_END
                        last_pos = f.tell()
                        file_opened = True
                        print(f"Initialized log watcher at position {last_pos}: {log_path}")
                    else:
                        # 从上次位置继续读取（只读取新增的内容）
                        f.seek(last_pos)
                        lines = f.readlines()
                        if lines:
                            last_pos = f.tell()
                            # 检查是否有错误模式匹配
                            for line in lines:
                                # 尝试多种编码方式解码
                                line_str = decode_line(line)

                                # 检查启动跟踪器
                                tracker_key = watcher.get('tracker_key')
                                if tracker_key and tracker_key in startup_trackers:
                                    check_startup_status(tracker_key, log_path, line_str)

                                # 检查错误模式
                                for pattern in error_patterns:
                                    if pattern['keyword'] in line_str:
                                        # 记录匹配到的错误（使用当前时间）
                                        error_record = {
                                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                                            'service': watcher['service_name'],
                                            'log_file': log_path,
                                            'error_name': pattern['name'],
                                            'log_line': line_str.strip(),
                                            'detected_at': time.time()  # 添加检测时间戳用于调试
                                        }
                                        # 保存错误记录
                                        detected_errors[watcher_id].append(error_record)
                                        # 保持最多100条错误记录
                                        if len(detected_errors[watcher_id]) > 100:
                                            detected_errors[watcher_id].pop(0)
                                        print(f"[NEW ERROR] Detected in {log_path}: {error_record['error_name']}")

            except FileNotFoundError:
                # 日志文件不存在，等待一段时间后重试
                if file_opened:
                    print(f"Log file disappeared: {log_path}")
                file_opened = False
                time.sleep(5)
                continue
            except UnicodeDecodeError as e:
                # 编码错误，尝试重新定位到文件末尾
                print(f"Encoding error in log file {log_path}: {e}, repositioning to end")
                try:
                    f.seek(0, 2)  # 跳转到文件末尾
                    last_pos = f.tell()
                except:
                    pass
                time.sleep(1)
                continue
            except Exception as e:
                print(f"Error reading log file {log_path}: {e}")
                time.sleep(5)
                continue

            time.sleep(1)  # 每秒检查一次

        sftp.close()
        print(f"Log watcher stopped for: {log_path}")

    except Exception as e:
        print(f"Log watching error for {log_path}: {e}")


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


# ==========================
# 日志和错误检测接口
# ==========================
@api_bp.route('/services/<service_name>/errors', methods=['GET'])
@login_required
def get_service_errors(service_name):
    """获取服务的所有错误日志（来自所有日志文件）"""
    server_id = request.args.get('server_id')
    if not server_id:
        return jsonify({"error": "缺少 server_id 参数"}), 400

    user_server_id = f"{session['user_id']}-{server_id}"
    prefix = f"{user_server_id}-{service_name}-"

    # 收集所有相关日志文件的错误
    all_errors = []

    # 首先检查是否有启动结果
    result_key = f"{user_server_id}-{service_name}-startup-result"
    if result_key in detected_errors:
        all_errors.extend(detected_errors[result_key])

    # 然后收集其他错误（排除启动成功的重复记录）
    for watcher_key, errors in detected_errors.items():
        if watcher_key.startswith(prefix) and watcher_key != result_key:
            # 过滤掉单个日志文件的"启动成功"记录（因为已经有统一的结果了）
            tracker_key = f"{user_server_id}-{service_name}"
            if tracker_key in startup_trackers:
                keyword = startup_trackers[tracker_key]['keyword']
                filtered_errors = [e for e in errors if e.get('error_name') != keyword]
                all_errors.extend(filtered_errors)
            else:
                all_errors.extend(errors)

    # 按时间戳排序
    all_errors.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    return jsonify(all_errors)


@api_bp.route('/services/<service_name>/log_files', methods=['GET'])
@login_required
def get_service_log_files(service_name):
    """获取服务的所有日志文件路径"""
    service_info = next((s for s in services if s["name"] == service_name), None)

    if not service_info:
        return jsonify({"error": "服务不存在"}), 404

    log_paths = service_info.get("log_paths", [])

    return jsonify({
        "service_name": service_name,
        "display_name": service_info.get("display_name", service_name),
        "log_files": [{"path": path, "name": os.path.basename(path)} for path in log_paths if path]
    })


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