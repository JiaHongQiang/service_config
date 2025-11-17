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
active_connections = {}
log_watchers = {}
detected_errors = {}
startup_trackers = {}

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
            "keyword": "start up",
            "required_count": 3,
            "timeout": 30
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
            "enabled": True,
            "keyword": "start up",  # VSS 的启动关键字
            "required_count": 1,  # 只需要 1 个日志文件检测到
            "timeout": 30
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

user_manager = UserManager('data')


# ==========================
# 工具函数
# ==========================
def login_required(f):
    """装饰器：确保用户已登录"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.headers.get('Content-Type', '').startswith('application/json') or \
                request.headers.get('Accept', '').find('application/json') != -1:
            if 'user_id' not in session:
                return jsonify({"error": "用户未登录"}), 401
        else:
            if 'user_id' not in session:
                return redirect('/login')
        return f(*args, **kwargs)

    return decorated_function


def get_user_servers_file(user_id: str) -> str:
    return f'data/servers_{user_id}.json'


def get_error_patterns_file() -> str:
    return 'data/error_log_patterns.json'


def get_ssh_client(server_id: str):
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
    if 'user_id' not in session:
        return False
    servers_file = get_user_servers_file(session['user_id'])
    os.makedirs('data', exist_ok=True)
    with open(servers_file, 'w', encoding='utf-8') as f:
        json.dump(servers, f, ensure_ascii=False, indent=4)
    return True


def find_server(server_id):
    servers = load_servers()
    return next((s for s in servers if str(s["id"]) == str(server_id)), None)


def decode_line(line):
    if isinstance(line, str):
        return line
    encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin1', 'ascii']
    for encoding in encodings:
        try:
            return line.decode(encoding)
        except (UnicodeDecodeError, AttributeError):
            continue
    try:
        return line.decode('utf-8', errors='ignore')
    except:
        return str(line)


def format_ssh_error(error):
    error_msg = str(error)
    if "Administratively prohibited" in error_msg:
        return "操作被服务器拒绝（权限不足）"
    elif "Permission denied" in error_msg:
        return "权限被拒绝"
    elif "No such file" in error_msg:
        return "文件或目录不存在"
    elif "Network is unreachable" in error_msg:
        return "网络不可达"
    elif "Connection refused" in error_msg:
        return "连接被拒绝"
    else:
        return error_msg


def check_startup_status(tracker_key, log_path, line_str):
    """检查服务启动状态"""
    tracker = startup_trackers.get(tracker_key)
    if not tracker:
        return

    if tracker['reported']:
        return

    # 检查是否包含启动关键字
    if tracker['keyword'] in line_str:
        tracker['detected_files'].add(log_path)
        print(
            f"[STARTUP] Detected '{tracker['keyword']}' in {log_path} ({len(tracker['detected_files'])}/{tracker['required_count']})")

        # 检查是否达到要求数量
        if len(tracker['detected_files']) >= tracker['required_count']:
            print(f"[STARTUP] Reached required count, reporting success...")
            report_startup_result(tracker_key, True)


def monitor_startup_timeout(tracker_key):
    """独立线程监控启动超时"""
    tracker = startup_trackers.get(tracker_key)
    if not tracker:
        return

    timeout = tracker['timeout']
    start_time = tracker['start_time']

    # 每0.5秒检查一次
    while True:
        time.sleep(0.5)

        # 如果tracker已被删除或已报告，则退出
        tracker = startup_trackers.get(tracker_key)
        if not tracker or tracker['reported']:
            break

        # 检查是否超时
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            # 超时了，检查是否达到要求
            if len(tracker['detected_files']) < tracker['required_count']:
                print(f"[STARTUP] Timeout reached, reporting failure...")
                report_startup_result(tracker_key, False)
            break


def report_startup_result(tracker_key, success):
    """报告启动结果"""
    tracker = startup_trackers.get(tracker_key)
    if not tracker or tracker['reported']:
        return

    tracker['reported'] = True

    # 解析 tracker_key 获取服务信息
    parts = tracker_key.rsplit('-', 1)
    service_name = parts[-1]

    # 创建一个虚拟的 watcher_id 用于存储统一的启动结果
    result_watcher_id = f"{tracker_key}-startup-result"

    if result_watcher_id not in detected_errors:
        detected_errors[result_watcher_id] = []

    startup_id = tracker.get('startup_id', 0)

    if success:
        error_record = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'service': service_name,
            'log_file': 'all',
            'error_name': '启动成功',
            'log_line': f'服务已在 {len(tracker["detected_files"])} 个日志文件中检测到启动成功',
            'detected_at': time.time(),
            'startup_id': startup_id  # 添加启动ID用于区分不同次启动
        }
        print(f"✓ [STARTUP SUCCESS] {service_name} fully started (startup_id: {startup_id})")
    else:
        error_record = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'service': service_name,
            'log_file': 'all',
            'error_name': '启动超时',
            'log_line': f'超时 {tracker["timeout"]}s，只在 {len(tracker["detected_files"])}/{tracker["required_count"]} 个日志文件中检测到启动成功',
            'detected_at': time.time(),
            'startup_id': startup_id  # 添加启动ID
        }
        print(f"✗ [STARTUP TIMEOUT] {service_name} startup incomplete (startup_id: {startup_id})")

    detected_errors[result_watcher_id].append(error_record)


# ==========================
# 用户认证接口
# ==========================
@api_bp.route('/auth/register', methods=['POST'])
def register():
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
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return jsonify({"error": "用户名和密码不能为空"}), 400
        user = user_manager.authenticate_user(username, password)
        if not user:
            return jsonify({"error": "用户名或密码错误"}), 401
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
    try:
        if 'session_id' in session:
            user_manager.destroy_session(session['session_id'])
        session.clear()
        return jsonify({"message": "已登出"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/auth/status', methods=['GET'])
def auth_status():
    if 'user_id' in session:
        user = user_manager.get_user_by_id(session['user_id'])
        if user:
            return jsonify({
                "logged_in": True,
                "user_id": user.user_id,
                "username": user.username
            }), 200
    return jsonify({"logged_in": False}), 401


@api_bp.route('/')
@login_required
def index():
    return render_template('index.html')


@api_bp.route('/login')
def login_page():
    if 'user_id' in session:
        return render_template('index.html')
    return render_template('login.html')


@api_bp.route('/servers', methods=['GET'])
@login_required
def get_servers():
    try:
        return jsonify(load_servers())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/servers', methods=['POST'])
@login_required
def add_server():
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
    try:
        servers = load_servers()
        updated = [s for s in servers if str(s["id"]) != str(server_id)]
        if len(updated) == len(servers):
            return jsonify({"error": "未找到该服务器"}), 404
        save_servers(updated)
        user_server_id = f"{session['user_id']}-{server_id}"
        if user_server_id in active_connections:
            active_connections[user_server_id].close()
            del active_connections[user_server_id]
        watchers_to_remove = [k for k in log_watchers if k.startswith(user_server_id)]
        for watcher_key in watchers_to_remove:
            log_watchers[watcher_key]['stop'] = True
            del log_watchers[watcher_key]
        return jsonify({"message": "删除成功"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/servers/<server_id>/connect', methods=['POST'])
@login_required
def connect_server(server_id):
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


@api_bp.route('/services/status', methods=['GET'])
@login_required
def get_services_status():
    server_id = request.args.get('server_id')
    if not server_id:
        return jsonify({"error": "缺少 server_id 参数"}), 400
    ssh, err, code = get_ssh_client(server_id)
    if err:
        return err, code
    try:
        result = []
        for s in services:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl list-unit-files | grep -w {s['name']}.service")
            service_exists = stdout.read().decode().strip()
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


@api_bp.route('/services/<service_name>/<action>', methods=['POST'])
@login_required
def service_action(service_name, action):
    server_id = request.args.get('server_id')
    ssh, err, code = get_ssh_client(server_id)
    if err:
        return err, code
    if action not in ["start", "stop", "restart"]:
        return jsonify({"error": "Invalid action"}), 400
    try:
        service_info = next((s for s in services if s["name"] == service_name), None)
        log_paths = service_info.get("log_paths", []) if service_info else []
        if action == "stop" and server_id:
            stop_log_watchers(server_id, service_name)
        cmd = f"sudo systemctl {action} {service_name}"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        err_out = stderr.read().decode()
        if exit_code == 0:
            if action == "start" and log_paths and server_id:
                start_log_watchers(server_id, service_name, log_paths)
            return jsonify({"message": f"{service_name} {action} 成功", "output": out})
        else:
            return jsonify({"error": err_out or "命令执行失败"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def start_log_watchers(server_id, service_name, log_paths):
    user_server_id = f"{session['user_id']}-{server_id}"
    stop_log_watchers(server_id, service_name)

    # 不再清空历史记录，而是为每次启动创建唯一的启动ID
    startup_id = int(time.time() * 1000)  # 使用毫秒级时间戳作为启动ID

    service_info = next((s for s in services if s["name"] == service_name), None)
    startup_check = service_info.get("startup_check", {}) if service_info else {}
    tracker_key = f"{user_server_id}-{service_name}"

    if startup_check.get("enabled"):
        startup_trackers[tracker_key] = {
            'keyword': startup_check.get('keyword', '启动成功'),
            'required_count': startup_check.get('required_count', 3),
            'timeout': startup_check.get('timeout', 30),
            'start_time': time.time(),
            'detected_files': set(),
            'reported': False,
            'startup_id': startup_id  # 添加启动ID
        }
        # 启动独立的超时监控线程
        timeout_thread = threading.Thread(target=monitor_startup_timeout, args=(tracker_key,))
        timeout_thread.daemon = True
        timeout_thread.start()
        print(
            f"[STARTUP] Started timeout monitor for {service_name} (timeout: {startup_check.get('timeout')}s, startup_id: {startup_id})")

    for log_path in log_paths:
        if not log_path:
            continue
        watcher_id = f"{user_server_id}-{service_name}-{hash(log_path)}"
        watcher = {
            'stop': False,
            'service_name': service_name,
            'log_path': log_path,
            'tracker_key': tracker_key if startup_check.get("enabled") else None
        }
        log_watchers[watcher_id] = watcher
        thread = threading.Thread(target=watch_log, args=(user_server_id, watcher, log_path))
        thread.daemon = True
        thread.start()
        print(f"Started log watcher for {service_name}: {log_path}")


def stop_log_watchers(server_id, service_name):
    user_server_id = f"{session['user_id']}-{server_id}"
    prefix = f"{user_server_id}-{service_name}-"
    watchers_to_stop = [k for k in log_watchers if k.startswith(prefix)]
    for watcher_key in watchers_to_stop:
        log_watchers[watcher_key]['stop'] = True
        print(f"Stopped log watcher: {watcher_key}")


def watch_log(user_server_id, watcher, log_path):
    ssh = active_connections.get(user_server_id)
    if not ssh:
        return
    watcher_id = f"{user_server_id}-{watcher['service_name']}-{hash(log_path)}"
    try:
        sftp = ssh.open_sftp()
        error_patterns = []
        patterns_file = get_error_patterns_file()
        if os.path.exists(patterns_file):
            with open(patterns_file, 'r', encoding='utf-8') as f:
                error_patterns = json.load(f)
        detected_errors[watcher_id] = []
        print(f"Started watching log file at {time.strftime('%Y-%m-%d %H:%M:%S')}: {log_path}")
        last_pos = 0
        file_opened = False
        while not watcher['stop']:
            try:
                with sftp.open(log_path, 'rb') as f:
                    if not file_opened:
                        f.seek(0, 2)
                        last_pos = f.tell()
                        file_opened = True
                        print(f"Initialized log watcher at position {last_pos}: {log_path}")
                    else:
                        f.seek(last_pos)
                        lines = f.readlines()
                        if lines:
                            last_pos = f.tell()
                            for line in lines:
                                line_str = decode_line(line)
                                # 先检查启动跟踪器
                                tracker_key = watcher.get('tracker_key')
                                if tracker_key and tracker_key in startup_trackers:
                                    check_startup_status(tracker_key, log_path, line_str)
                                    # 如果包含启动关键字，跳过错误检查
                                    tracker = startup_trackers[tracker_key]
                                    if tracker['keyword'] in line_str:
                                        continue
                                # 检查错误模式
                                for pattern in error_patterns:
                                    if pattern['keyword'] in line_str:
                                        error_record = {
                                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                                            'service': watcher['service_name'],
                                            'log_file': log_path,
                                            'error_name': pattern['name'],
                                            'log_line': line_str.strip(),
                                            'detected_at': time.time()
                                        }
                                        detected_errors[watcher_id].append(error_record)
                                        if len(detected_errors[watcher_id]) > 100:
                                            detected_errors[watcher_id].pop(0)
                                        print(f"[NEW ERROR] Detected in {log_path}: {error_record['error_name']}")
            except FileNotFoundError:
                if file_opened:
                    print(f"Log file disappeared: {log_path}")
                file_opened = False
                time.sleep(5)
                continue
            except UnicodeDecodeError as e:
                print(f"Encoding error in log file {log_path}: {e}, repositioning to end")
                try:
                    f.seek(0, 2)
                    last_pos = f.tell()
                except:
                    pass
                time.sleep(1)
                continue
            except Exception as e:
                print(f"Error reading log file {log_path}: {e}")
                time.sleep(5)
                continue
            time.sleep(1)
        sftp.close()
        print(f"Log watcher stopped for: {log_path}")
    except Exception as e:
        print(f"Log watching error for {log_path}: {e}")


@api_bp.route('/config/files', methods=['GET'])
@login_required
def get_config_files():
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
                items = sftp.listdir_attr(path)
                result[s["name"]] = []
                for item in items:
                    item_path = os.path.join(path, item.filename).replace("\\", "/")
                    if stat.S_ISDIR(item.st_mode):
                        result[s["name"]].append({
                            "name": item.filename,
                            "path": item_path,
                            "type": "directory",
                            "size": item.st_size,
                            "mtime": item.st_mtime
                        })
                    else:
                        result[s["name"]].append({
                            "name": item.filename,
                            "path": item_path,
                            "type": "file",
                            "size": item.st_size,
                            "mtime": item.st_mtime
                        })
            except Exception:
                result[s["name"]] = []
        sftp.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": format_ssh_error(e)}), 500


@api_bp.route('/config/files/list', methods=['GET'])
@login_required
def list_directory():
    server_id = request.args.get('server_id')
    ssh, err, code = get_ssh_client(server_id)
    if err:
        return err, code
    path = request.args.get('path')
    if not path and path != "":
        return jsonify({"error": "缺少 path 参数"}), 400
    try:
        sftp = ssh.open_sftp()
        items = sftp.listdir_attr(path) if path else sftp.listdir_attr(".")
        result = []
        for item in items:
            item_path = os.path.join(path, item.filename).replace("\\", "/") if path else item.filename
            if stat.S_ISDIR(item.st_mode):
                result.append({
                    "name": item.filename,
                    "path": item_path,
                    "type": "directory",
                    "size": item.st_size,
                    "mtime": item.st_mtime
                })
            else:
                result.append({
                    "name": item.filename,
                    "path": item_path,
                    "type": "file",
                    "size": item.st_size,
                    "mtime": item.st_mtime
                })
        sftp.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": format_ssh_error(e)}), 500


@api_bp.route('/config/path/info', methods=['GET'])
@login_required
def get_path_info():
    server_id = request.args.get('server_id')
    ssh, err, code = get_ssh_client(server_id)
    if err:
        return err, code
    path = request.args.get('path')
    if not path:
        return jsonify({"error": "缺少 path 参数"}), 400
    try:
        sftp = ssh.open_sftp()
        stat_info = sftp.stat(path)
        sftp.close()
        if stat.S_ISDIR(stat_info.st_mode):
            return jsonify({"path": path, "type": "directory"})
        else:
            return jsonify({"path": path, "type": "file"})
    except Exception as e:
        return jsonify({"error": format_ssh_error(e)}), 500


@api_bp.route('/config/files/<path:file_path>', methods=['GET'])
@login_required
def read_config_file(file_path):
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
        return jsonify({"error": format_ssh_error(e)}), 500


@api_bp.route('/config/files/<path:file_path>', methods=['POST'])
@login_required
def write_config_file(file_path):
    server_id = request.args.get('server_id')
    ssh, err, code = get_ssh_client(server_id)
    if err:
        return err, code
    try:
        data = request.get_json()
        content = data.get('content', '')
        backup_path = f"/{file_path}.backup_{int(time.time())}"
        sftp = ssh.open_sftp()
        try:
            sftp.rename(f"/{file_path}", backup_path)
        except FileNotFoundError:
            pass
        with sftp.open(f"/{file_path}", 'w') as f:
            f.write(content)
        sftp.close()
        return jsonify({
            "message": "文件保存成功",
            "backup_path": backup_path if 'backup_path' in locals() else None
        })
    except Exception as e:
        return jsonify({"error": format_ssh_error(e)}), 500


@api_bp.route('/config/files/<path:file_path>', methods=['DELETE'])
@login_required
def delete_config_file(file_path):
    server_id = request.args.get('server_id')
    ssh, err, code = get_ssh_client(server_id)
    if err:
        return err, code
    try:
        sftp = ssh.open_sftp()
        sftp.remove(f"/{file_path}")
        sftp.close()
        return jsonify({"message": f"文件 {file_path} 删除成功"})
    except FileNotFoundError:
        return jsonify({"error": "文件不存在"}), 404
    except Exception as e:
        return jsonify({"error": format_ssh_error(e)}), 500


@api_bp.route('/services/<service_name>/errors', methods=['GET'])
@login_required
def get_service_errors(service_name):
    """获取服务的所有错误日志（来自所有日志文件）"""
    server_id = request.args.get('server_id')
    if not server_id:
        return jsonify({"error": "缺少 server_id 参数"}), 400

    user_server_id = f"{session['user_id']}-{server_id}"
    prefix = f"{user_server_id}-{service_name}-"
    all_errors = []

    # 首先检查是否有启动结果
    result_key = f"{user_server_id}-{service_name}-startup-result"
    if result_key in detected_errors:
        all_errors.extend(detected_errors[result_key])

    # 然后收集其他错误（排除单个日志文件的启动成功记录）
    for watcher_key, errors in detected_errors.items():
        if watcher_key.startswith(prefix) and watcher_key != result_key:
            tracker_key = f"{user_server_id}-{service_name}"
            if tracker_key in startup_trackers:
                keyword = startup_trackers[tracker_key]['keyword']
                filtered_errors = [e for e in errors if keyword not in e.get('log_line', '')]
                all_errors.extend(filtered_errors)
            else:
                all_errors.extend(errors)

    # 按时间戳排序
    all_errors.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return jsonify(all_errors)


@api_bp.route('/services/<service_name>/log_files', methods=['GET'])
@login_required
def get_service_log_files(service_name):
    service_info = next((s for s in services if s["name"] == service_name), None)
    if not service_info:
        return jsonify({"error": "服务不存在"}), 404
    log_paths = service_info.get("log_paths", [])
    return jsonify({
        "service_name": service_name,
        "display_name": service_info.get("display_name", service_name),
        "log_files": [{"path": path, "name": os.path.basename(path)} for path in log_paths if path]
    })


@api_bp.route('/config/compare', methods=['POST'])
@login_required
def compare_files():
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
        sftp = ssh.open_sftp()
        try:
            with sftp.open('/' + file_path, 'r') as f:
                server_content = f.read().decode('utf-8', errors='ignore')
        except FileNotFoundError:
            server_content = ""
        finally:
            sftp.close()
        server_lines = server_content.splitlines(keepends=True)
        local_lines = local_content.splitlines(keepends=True)
        diff_result = list(unified_diff(
            server_lines,
            local_lines,
            fromfile=f'服务器: {file_path}',
            tofile=f'本地: {file_path}',
            lineterm=''
        ))
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


@api_bp.route('/config/error_patterns', methods=['GET'])
def get_error_patterns():
    try:
        patterns_file = get_error_patterns_file()
        if os.path.exists(patterns_file):
            with open(patterns_file, 'r', encoding='utf-8') as f:
                patterns = json.load(f)
        else:
            patterns = []
        return jsonify(patterns)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/config/error_patterns', methods=['POST'])
@login_required
def save_error_patterns():
    try:
        patterns = request.json
        patterns_file = get_error_patterns_file()
        os.makedirs(os.path.dirname(patterns_file), exist_ok=True)
        with open(patterns_file, 'w', encoding='utf-8') as f:
            json.dump(patterns, f, ensure_ascii=False, indent=4)
        return jsonify({"message": "保存成功"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500