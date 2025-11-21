# 导入标准库
import os                 # 操作系统相关功能
import json               # JSON数据处理
import stat               # 文件状态信息

# 导入第三方库
import paramiko           # SSH连接库，用于远程服务器管理
from flask import Blueprint, jsonify, request, render_template, session, redirect  # Flask Web框架组件
from models import UserManager  # 自定义用户管理模块
from functools import wraps     # 装饰器工具
from difflib import unified_diff  # 文件差异比较工具
import time               # 时间处理
import threading          # 多线程支持

# 导入自定义工具
from utils import (get_user_servers_file, get_error_patterns_file, decode_line, 
                  format_ssh_error, get_ssh_client, load_servers, save_servers, find_server)

# ==========================
# Blueprint 配置
# ==========================
# 创建Flask蓝图，用于组织路由和视图函数
api_bp = Blueprint('api', __name__)

# ==========================
# 全局变量
# ==========================
# 存储活跃的SSH连接对象，键为用户-服务器标识，值为SSH客户端实例
active_connections = {}
# 日志监视器字典，用于跟踪正在监视的日志文件
log_watchers = {}
# 检测到的错误记录，按监视器分组存储
detected_errors = {}
# 服务启动跟踪器，用于监控服务启动状态
startup_trackers = {}

# 模拟服务列表 - 支持多路径日志
# 定义系统中所有可管理的服务及其配置信息
services = [
    {
        "name": "sie",                      # 服务名称（系统内部标识）
        "display_name": "流媒体服务",         # 服务显示名称
        "config_path": "/home/hy_media_server/conf/",  # 配置文件路径
        "log_paths": [                       # 日志文件路径列表
            "/home/hy_media_server/log/222-1/run/log-222-1-run.log",
            "/home/hy_media_server/log/222-1/interface/log-222-1-run.log",
            "/home/hy_media_server/log/666-1/run/log-666-1-run.log",
            "/home/hy_media_server/log/666-1/interface/log-666-1-run.log",
            "/home/hy_media_server/log/888-1/run/log-888-1-run.log",
            "/home/hy_media_server/log/888-1/interface/log-888-1-run.log",
            "/home/hy_media_server/log/999-1/run/log-999-1-run.log",
            "/home/hy_media_server/log/999-1/interface/log-999-1-run.log"
        ],
        "startup_check": {                   # 启动状态检查配置
            "enabled": True,                 # 是否启用启动检查
            "keyword": "start up",          # 启动成功的关键字
            "required_count": 3,             # 需要检测到关键字的日志文件数量
            "timeout": 30                    # 启动超时时间（秒）
        },
        "has_config": True                   # 是否有配置文件
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

# 初始化用户管理器，指定数据存储目录为 'data'
user_manager = UserManager('data')


# ==========================
# 工具函数
# ==========================
# 登录验证装饰器：用于保护需要登录才能访问的路由
# 检查用户会话状态，如果未登录则返回错误信息或重定向到登录页面
def login_required(f):
    """装饰器：确保用户已登录"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 判断请求是否为AJAX请求（通过Content-Type或Accept头部判断）
        if request.headers.get('Content-Type', '').startswith('application/json') or \
                request.headers.get('Accept', '').find('application/json') != -1:
            # AJAX请求返回JSON格式错误信息
            if 'user_id' not in session:
                return jsonify({"error": "用户未登录"}), 401
        else:
            # 普通页面请求重定向到登录页
            if 'user_id' not in session:
                return redirect('/login')
        # 用户已登录，继续执行原函数
        return f(*args, **kwargs)

    return decorated_function


# 已移至 utils.py


# 已移至 utils.py


# 已移至 utils.py


# 已移至 utils.py


# 检查服务启动状态
# 参数: 
#   tracker_key - 启动跟踪器键名
#   log_path - 日志文件路径
#   line_str - 日志行内容
def check_startup_status(tracker_key, log_path, line_str):
    """检查服务启动状态"""
    # 获取对应的启动跟踪器
    tracker = startup_trackers.get(tracker_key)
    if not tracker:
        return

    # 如果已经报告过结果，则不再处理
    if tracker['reported']:
        return

    # 检查日志行是否包含启动关键字
    if tracker['keyword'] in line_str:
        # 记录检测到关键字的日志文件
        tracker['detected_files'].add(log_path)
        print(
            f"[STARTUP] Detected '{tracker['keyword']}' in {log_path} ({len(tracker['detected_files'])}/{tracker['required_count']})")

        # 检查是否达到要求数量
        if len(tracker['detected_files']) >= tracker['required_count']:
            print(f"[STARTUP] Reached required count, reporting success...")
            # 报告启动成功
            report_startup_result(tracker_key, True)


# 独立线程监控服务启动超时
# 参数: tracker_key - 启动跟踪器键名
def monitor_startup_timeout(tracker_key):
    """独立线程监控启动超时"""
    # 获取对应的启动跟踪器
    tracker = startup_trackers.get(tracker_key)
    if not tracker:
        return

    # 获取超时设置和启动时间
    timeout = tracker['timeout']
    start_time = tracker['start_time']

    # 每0.5秒检查一次启动状态
    while True:
        time.sleep(0.5)

        # 如果tracker已被删除或已报告，则退出监控循环
        tracker = startup_trackers.get(tracker_key)
        if not tracker or tracker['reported']:
            break

        # 检查是否超时
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            # 超时了，检查是否达到要求的数量
            if len(tracker['detected_files']) < tracker['required_count']:
                print(f"[STARTUP] Timeout reached, reporting failure...")
                # 报告启动超时失败
                report_startup_result(tracker_key, False)
            break


# 报告服务启动结果
# 参数: 
#   tracker_key - 启动跟踪器键名
#   success - 启动是否成功
def report_startup_result(tracker_key, success):
    """报告启动结果"""
    # 获取对应的启动跟踪器
    tracker = startup_trackers.get(tracker_key)
    if not tracker or tracker['reported']:
        return

    # 标记为已报告，避免重复报告
    tracker['reported'] = True

    # 解析 tracker_key 获取服务信息
    parts = tracker_key.rsplit('-', 1)
    service_name = parts[-1]

    # 创建一个虚拟的 watcher_id 用于存储统一的启动结果
    result_watcher_id = f"{tracker_key}-startup-result"

    # 如果结果列表不存在，创建空列表
    if result_watcher_id not in detected_errors:
        detected_errors[result_watcher_id] = []

    # 获取启动ID，用于区分不同次启动
    startup_id = tracker.get('startup_id', 0)

    # 构造启动结果记录
    if success:
        # 启动成功记录
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
        # 启动超时记录
        error_record = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'service': service_name,
            'log_file': 'all',
            'error_name': '启动超时',
            'log_line': f'超时 {tracker["timeout"]}s，只在 {len(tracker["detected_files"])} 个日志文件中检测到启动成功',
            'detected_at': time.time(),
            'startup_id': startup_id  # 添加启动ID
        }
        print(f"✗ [STARTUP TIMEOUT] {service_name} startup incomplete (startup_id: {startup_id})")

    # 将启动结果添加到检测错误列表中
    detected_errors[result_watcher_id].append(error_record)


# ==========================
# 用户认证接口
# ==========================
# 用户注册接口
# 接收用户名和密码，创建新用户
@api_bp.route('/auth/register', methods=['POST'])
def register():
    try:
        # 获取请求中的JSON数据
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        # 验证用户名和密码是否为空
        if not username or not password:
            return jsonify({"error": "用户名和密码不能为空"}), 400
        
        # 调用用户管理器创建用户
        user = user_manager.create_user(username, password)
        
        # 检查用户是否创建成功
        if not user:
            return jsonify({"error": "用户已存在"}), 400
        
        # 返回注册成功响应
        return jsonify({"message": "注册成功", "user_id": user.user_id}), 201
    except Exception as e:
        # 处理异常情况
        return jsonify({"error": format_ssh_error(e)}), 500


# 用户登录接口
# 验证用户名和密码，创建用户会话
@api_bp.route('/auth/login', methods=['POST'])
def login():
    try:
        # 获取请求中的JSON数据
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        # 验证用户名和密码是否为空
        if not username or not password:
            return jsonify({"error": "用户名和密码不能为空"}), 400
        
        # 调用用户管理器验证用户
        user = user_manager.authenticate_user(username, password)
        
        # 检查用户验证是否成功
        if not user:
            return jsonify({"error": "用户名或密码错误"}), 401
        
        # 创建用户会话
        session_id = user_manager.create_session(user)
        session['user_id'] = user.user_id
        session['session_id'] = session_id
        
        # 返回登录成功响应
        return jsonify({
            "message": "登录成功",
            "user_id": user.user_id,
            "username": user.username
        }), 200
    except Exception as e:
        # 处理异常情况
        return jsonify({"error": format_ssh_error(e)}), 500


# 用户登出接口
# 销毁用户会话，清除登录状态
@api_bp.route('/auth/logout', methods=['POST'])
@login_required
def logout():
    try:
        # 如果会话中存在session_id，则销毁会话
        if 'session_id' in session:
            user_manager.destroy_session(session['session_id'])
        
        # 清除会话数据
        session.clear()
        
        # 返回登出成功响应
        return jsonify({"message": "已登出"}), 200
    except Exception as e:
        # 处理异常情况
        return jsonify({"error": format_ssh_error(e)}), 500


# 检查用户认证状态接口
# 检查当前用户是否已登录
@api_bp.route('/auth/status', methods=['GET'])
def auth_status():
    # 检查会话中是否存在用户ID
    if 'user_id' in session:
        # 根据用户ID获取用户信息
        user = user_manager.get_user_by_id(session['user_id'])
        if user:
            # 用户已登录，返回用户信息
            return jsonify({
                "logged_in": True,
                "user_id": user.user_id,
                "username": user.username
            }), 200
    # 用户未登录
    return jsonify({"logged_in": False}), 401


# 主页路由
# 需要登录才能访问
@api_bp.route('/')
@login_required
def index():
    return render_template('index.html')


# 登录页面路由
# 根据用户登录状态决定显示登录页还是主页
@api_bp.route('/login')
def login_page():
    # 如果用户已登录，直接跳转到主页
    if 'user_id' in session:
        return render_template('index.html')
    # 用户未登录，显示登录页面
    return render_template('login.html')


# 获取服务器列表接口
# 返回当前用户的所有服务器配置
@api_bp.route('/servers', methods=['GET'])
@login_required
def get_servers():
    try:
        # 加载并返回服务器列表
        return jsonify(load_servers())
    except Exception as e:
        # 处理异常情况
        return jsonify({"error": format_ssh_error(e)}), 500


# 添加服务器接口
# 添加新的服务器配置
@api_bp.route('/servers', methods=['POST'])
@login_required
def add_server():
    try:
        # 获取请求中的服务器配置数据
        new_server = request.json
        
        # 加载现有服务器列表
        servers = load_servers()
        
        # 检查服务器ID是否已存在
        if any(s["id"] == new_server["id"] for s in servers):
            return jsonify({"error": "服务器ID已存在"}), 400
        
        # 添加新服务器到列表
        servers.append(new_server)
        
        # 保存更新后的服务器列表
        save_servers(servers)
        
        # 返回添加成功的服务器信息
        return jsonify(new_server), 201
    except Exception as e:
        # 处理异常情况
        return jsonify({"error": format_ssh_error(e)}), 500


# 删除服务器接口
# 根据服务器ID删除服务器配置及相关连接
@api_bp.route('/servers/<server_id>', methods=['DELETE'])
@login_required
def delete_server(server_id):
    try:
        # 加载服务器列表
        servers = load_servers()
        
        # 过滤掉要删除的服务器
        updated = [s for s in servers if str(s["id"]) != str(server_id)]
        
        # 检查是否有服务器被删除
        if len(updated) == len(servers):
            return jsonify({"error": "未找到该服务器"}), 404
        
        # 保存更新后的服务器列表
        save_servers(updated)
        
        # 构造用户-服务器唯一标识
        user_server_id = f"{session['user_id']}-{server_id}"
        
        # 关闭并清理相关SSH连接
        if user_server_id in active_connections:
            active_connections[user_server_id].close()
            del active_connections[user_server_id]
        
        # 停止并清理相关日志监视器
        watchers_to_remove = [k for k in log_watchers if k.startswith(user_server_id)]
        for watcher_key in watchers_to_remove:
            log_watchers[watcher_key]['stop'] = True
            del log_watchers[watcher_key]
        
        # 返回删除成功响应
        return jsonify({"message": "删除成功"})
    except Exception as e:
        # 处理异常情况
        return jsonify({"error": format_ssh_error(e)}), 500


# 连接服务器接口
# 建立到指定服务器的SSH连接
@api_bp.route('/servers/<server_id>/connect', methods=['POST'])
@login_required
def connect_server(server_id):
    # 查找目标服务器配置
    target = find_server(server_id)
    if not target:
        return jsonify({"error": "服务器不存在"}), 404
    
    try:
        # 创建SSH客户端
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 建立SSH连接
        ssh.connect(
            hostname=target["host"],
            port=int(target["port"]),
            username=target["username"],
            password=target["password"],
            timeout=8
        )
        
        # 构造用户-服务器唯一标识并保存连接
        user_server_id = f"{session['user_id']}-{server_id}"
        active_connections[user_server_id] = ssh
        
        # 返回连接成功响应
        return jsonify({"message": f"已成功连接到 {target['name']} ({target['host']})", "server_id": server_id})
    except Exception as e:
        # 处理连接异常
        return jsonify({"error": format_ssh_error(e)}), 500


# 获取服务状态接口
# 查询远程服务器上所有服务的运行状态
@api_bp.route('/services/status', methods=['GET'])
@login_required
def get_services_status():
    # 获取请求参数中的服务器ID
    server_id = request.args.get('server_id')
    if not server_id:
        return jsonify({"error": "缺少 server_id 参数"}), 400
    
    # 获取SSH客户端连接
    ssh, err, code = get_ssh_client(server_id, active_connections)
    if err:
        return err, code
    
    try:
        result = []
        # 遍历所有服务
        for s in services:
            # 检查服务是否存在
            stdin, stdout, stderr = ssh.exec_command(f"systemctl list-unit-files | grep -w {s['name']}.service")
            service_exists = stdout.read().decode().strip()
            
            if service_exists:
                # 获取服务状态
                stdin, stdout, stderr = ssh.exec_command(f"sudo systemctl is-active {s['name']}")
                status = stdout.read().decode().strip()
                
                # 根据状态设置对应的颜色标识
                if status == "active":
                    color = "status-running"  # 运行中
                elif status in ["inactive", "failed"]:
                    color = "status-stopped"  # 已停止
                else:
                    color = "status-unknown"  # 状态未知
                
                # 将服务信息和状态添加到结果中
                result.append({
                    **s,
                    "status": status,
                    "status_indicator": color
                })
        
        # 返回服务状态列表
        return jsonify(result)
    except Exception as e:
        # 处理异常情况
        return jsonify({"error": format_ssh_error(e)}), 500


# 服务控制接口
# 对指定服务执行启动、停止或重启操作
@api_bp.route('/services/<service_name>/<action>', methods=['POST'])
@login_required
def service_action(service_name, action):
    # 获取请求参数中的服务器ID
    server_id = request.args.get('server_id')
    
    # 获取SSH客户端连接
    ssh, err, code = get_ssh_client(server_id, active_connections)
    if err:
        return err, code
    
    # 验证操作类型是否有效
    if action not in ["start", "stop", "restart"]:
        return jsonify({"error": "Invalid action"}), 400
    
    try:
        # 查找服务信息
        service_info = next((s for s in services if s["name"] == service_name), None)
        log_paths = service_info.get("log_paths", []) if service_info else []
        
        # 如果是停止操作，停止相关日志监视器
        if action == "stop" and server_id:
            stop_log_watchers(server_id, service_name)
        
        # 构造并执行系统命令
        cmd = f"sudo systemctl {action} {service_name}"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        # 获取命令执行结果
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        err_out = stderr.read().decode()
        
        if exit_code == 0:
            # 命令执行成功
            # 如果是启动操作且有日志路径，启动日志监视器
            if action == "start" and log_paths and server_id:
                start_log_watchers(server_id, service_name, log_paths)
            
            # 返回操作成功响应
            return jsonify({"message": f"{service_name} {action} 成功", "output": out})
        else:
            # 命令执行失败，返回错误信息
            return jsonify({"error": err_out or "命令执行失败"}), 500
    except Exception as e:
        # 处理异常情况
        return jsonify({"error": format_ssh_error(e)}), 500


# 启动日志监视器
# 为指定服务的所有日志文件启动监视线程
# 参数: 
#   server_id - 服务器ID
#   service_name - 服务名称
#   log_paths - 日志文件路径列表
def start_log_watchers(server_id, service_name, log_paths):
    # 构造用户-服务器唯一标识
    user_server_id = f"{session['user_id']}-{server_id}"
    
    # 停止已存在的同名服务监视器
    stop_log_watchers(server_id, service_name)

    # 不再清空历史记录，而是为每次启动创建唯一的启动ID
    startup_id = int(time.time() * 1000)  # 使用毫秒级时间戳作为启动ID

    # 获取服务信息和启动检查配置
    service_info = next((s for s in services if s["name"] == service_name), None)
    startup_check = service_info.get("startup_check", {}) if service_info else {}
    tracker_key = f"{user_server_id}-{service_name}"

    # 如果启用了启动检查，初始化启动跟踪器
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

    # 为每个日志文件启动监视线程
    for log_path in log_paths:
        if not log_path:
            continue
        
        # 构造监视器唯一标识
        watcher_id = f"{user_server_id}-{service_name}-{hash(log_path)}"
        
        # 创建监视器配置
        watcher = {
            'stop': False,
            'service_name': service_name,
            'log_path': log_path,
            'tracker_key': tracker_key if startup_check.get("enabled") else None
        }
        
        # 保存监视器配置
        log_watchers[watcher_id] = watcher
        
        # 启动日志监视线程
        thread = threading.Thread(target=watch_log, args=(user_server_id, watcher, log_path))
        thread.daemon = True
        thread.start()
        print(f"Started log watcher for {service_name}: {log_path}")


# 停止日志监视器
# 停止指定服务的所有日志监视线程
# 参数: 
#   server_id - 服务器ID
#   service_name - 服务名称
def stop_log_watchers(server_id, service_name):
    # 构造用户-服务器唯一标识
    user_server_id = f"{session['user_id']}-{server_id}"
    
    # 构造监视器键名前缀
    prefix = f"{user_server_id}-{service_name}-"
    
    # 查找需要停止的监视器
    watchers_to_stop = [k for k in log_watchers if k.startswith(prefix)]
    
    # 设置停止标志并打印日志
    for watcher_key in watchers_to_stop:
        log_watchers[watcher_key]['stop'] = True
        print(f"Stopped log watcher: {watcher_key}")


# 监控单个日志文件
# 持续读取日志文件内容，检测错误模式和启动状态
# 参数:
#   user_server_id - 用户-服务器唯一标识
#   watcher - 监视器配置
#   log_path - 日志文件路径
def watch_log(user_server_id, watcher, log_path):
    # 获取SSH连接
    ssh = active_connections.get(user_server_id)
    if not ssh:
        return
    
    # 构造监视器唯一标识
    watcher_id = f"{user_server_id}-{watcher['service_name']}-{hash(log_path)}"
    
    try:
        # 打开SFTP连接
        sftp = ssh.open_sftp()
        
        # 加载错误模式配置
        error_patterns = []
        patterns_file = get_error_patterns_file()
        if os.path.exists(patterns_file):
            with open(patterns_file, 'r', encoding='utf-8') as f:
                error_patterns = json.load(f)
        
        # 初始化错误记录列表
        detected_errors[watcher_id] = []
        print(f"Started watching log file at {time.strftime('%Y-%m-%d %H:%M:%S')}: {log_path}")
        
        # 初始化文件读取位置
        last_pos = 0
        file_opened = False
        
        # 持续监控日志文件
        while not watcher['stop']:
            try:
                with sftp.open(log_path, 'rb') as f:
                    # 如果文件尚未打开，定位到文件末尾
                    if not file_opened:
                        f.seek(0, 2)  # 定位到文件末尾
                        last_pos = f.tell()  # 记录当前位置
                        file_opened = True
                        print(f"Initialized log watcher at position {last_pos}: {log_path}")
                    else:
                        # 定位到上次读取位置并读取新内容
                        f.seek(last_pos)
                        lines = f.readlines()
                        
                        if lines:
                            # 更新读取位置
                            last_pos = f.tell()
                            
                            # 处理每一行日志
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
                                        # 构造错误记录
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


# 获取配置文件列表接口
# 获取服务器上所有服务的配置文件列表
@api_bp.route('/config/files', methods=['GET'])
@login_required
def get_config_files():
    # 获取请求参数
    server_id = request.args.get('server_id')
    ssh, err, code = get_ssh_client(server_id, active_connections)
    if err:
        return err, code
    service_name = request.args.get('service')
    
    try:
        # 打开SFTP连接
        sftp = ssh.open_sftp()
        result = {}
        
        # 遍历所有服务
        for s in services:
            # 如果指定了服务名，只处理该服务
            if service_name and s["name"] != service_name:
                continue
            
            # 获取服务配置路径
            path = s["config_path"]
            if not path:
                result[s["name"]] = []
                continue
            
            try:
                # 列出目录中的所有项目
                items = sftp.listdir_attr(path)
                result[s["name"]] = []
                
                # 处理每个项目
                for item in items:
                    # 构造项目路径
                    item_path = os.path.join(path, item.filename).replace("\\", "/")
                    
                    # 判断是目录还是文件
                    if stat.S_ISDIR(item.st_mode):
                        # 目录
                        result[s["name"]].append({
                            "name": item.filename,
                            "path": item_path,
                            "type": "directory",
                            "size": item.st_size,
                            "mtime": item.st_mtime
                        })
                    else:
                        # 文件
                        result[s["name"]].append({
                            "name": item.filename,
                            "path": item_path,
                            "type": "file",
                            "size": item.st_size,
                            "mtime": item.st_mtime
                        })
            except Exception:
                # 处理异常情况
                result[s["name"]] = []
        
        # 关闭SFTP连接并返回结果
        sftp.close()
        return jsonify(result)
    except Exception as e:
        # 处理连接异常
        return jsonify({"error": format_ssh_error(e)}), 500


# 列出目录内容
@api_bp.route('/api/sftp/list', methods=['GET'])
@login_required
def sftp_list():
    """
    请求参数:
      - server_id (query) 必需
      - path (query) 可选, 默认为 '/'
    返回: JSON 列表: [{name, path, type, size, mtime, mode}, ...]
    """
    server_id = request.args.get('server_id')
    path = request.args.get('path', '/')
    if not server_id:
        return jsonify({"error": "缺少 server_id 参数"}), 400

    ssh, err, code = get_ssh_client(server_id, active_connections)
    if err:
        return err, code

    try:
        sftp = ssh.open_sftp()
        # 如果 path 是空，设为根
        try:
            items = sftp.listdir_attr(path)
        except IOError as e:
            # 目录不存在或无法访问，返回空列表
            sftp.close()
            return jsonify({"error": "无法访问目录: " + str(e)}), 500

        result = []

        # ==================== 新增代码开始 ====================
        # 批量获取用户名和组名映射（一次性执行）
        uid_to_user = {}
        gid_to_group = {}

        # 收集所有唯一的 UID 和 GID
        unique_uids = set(item.st_uid for item in items)
        unique_gids = set(item.st_gid for item in items)

        # 批量查询用户名
        if unique_uids:
            try:
                uid_list = ' '.join(str(uid) for uid in unique_uids)
                cmd = f"getent passwd {uid_list} 2>/dev/null || true"
                stdin, stdout, stderr = ssh.exec_command(cmd)
                for line in stdout.read().decode('utf-8', errors='ignore').splitlines():
                    parts = line.split(':')
                    if len(parts) >= 3:
                        uid_to_user[int(parts[2])] = parts[0]
            except:
                pass

        # 批量查询组名
        if unique_gids:
            try:
                gid_list = ' '.join(str(gid) for gid in unique_gids)
                cmd = f"getent group {gid_list} 2>/dev/null || true"
                stdin, stdout, stderr = ssh.exec_command(cmd)
                for line in stdout.read().decode('utf-8', errors='ignore').splitlines():
                    parts = line.split(':')
                    if len(parts) >= 3:
                        gid_to_group[int(parts[2])] = parts[0]
            except:
                pass
        # ==================== 新增代码结束 ====================

        for item in items:
            item_path = os.path.join(path, item.filename).replace("\\", "/")

            # ==================== 修改这里 ====================
            # 使用映射获取用户名和组名，如果找不到则使用数字ID
            user_name = uid_to_user.get(item.st_uid, str(item.st_uid))
            group_name = gid_to_group.get(item.st_gid, str(item.st_gid))
            # ==================== 修改结束 ====================

            result.append({
                "name": item.filename,
                "path": item_path,
                "type": "directory" if stat.S_ISDIR(item.st_mode) else "file",
                "size": item.st_size,
                "mtime": item.st_mtime,
                "mode": oct(item.st_mode & 0o777),
                "uid": item.st_uid,
                "gid": item.st_gid,
                "user": user_name,
                "group": group_name
            })
        sftp.close()
        return jsonify(result)
    except Exception as e:
        # 添加更详细的错误信息
        error_msg = format_ssh_error(e)
        return jsonify({"error": "读取目录失败: " + error_msg}), 500


# 获取路径信息接口
# 获取服务器上指定路径的信息（判断是文件还是目录）
@api_bp.route('/config/path/info', methods=['GET'])
@login_required
def get_path_info():
    # 获取请求参数
    server_id = request.args.get('server_id')
    ssh, err, code = get_ssh_client(server_id, active_connections)
    if err:
        return err, code
    
    # 获取路径参数
    path = request.args.get('path')
    if not path:
        return jsonify({"error": "缺少 path 参数"}), 400
    
    try:
        # 打开SFTP连接
        sftp = ssh.open_sftp()
        
        # 获取路径状态信息
        stat_info = sftp.stat(path)
        sftp.close()
        
        # 判断是目录还是文件
        if stat.S_ISDIR(stat_info.st_mode):
            return jsonify({"path": path, "type": "directory"})
        else:
            return jsonify({"path": path, "type": "file"})
    except Exception as e:
        # 处理连接异常
        return jsonify({"error": format_ssh_error(e)}), 500


# 读取配置文件接口
# 读取服务器上指定配置文件的内容
@api_bp.route('/config/files/<path:file_path>', methods=['GET'])
@login_required
def read_config_file(file_path):
    # 获取请求参数
    server_id = request.args.get('server_id')
    ssh, err, code = get_ssh_client(server_id, active_connections)
    if err:
        return err, code
    
    try:
        # 打开SFTP连接
        sftp = ssh.open_sftp()
        
        # 读取文件内容
        with sftp.open('/' + file_path, 'r') as f:
            content = f.read().decode('utf-8', errors='ignore')
        
        # 关闭SFTP连接并返回文件内容
        sftp.close()
        return jsonify({"path": file_path, "content": content})
    except Exception as e:
        # 处理连接异常
        return jsonify({"error": format_ssh_error(e)}), 500


# 写入配置文件接口
# 将内容写入服务器上指定的配置文件
@api_bp.route('/config/files/<path:file_path>', methods=['POST'])
@login_required
def write_config_file(file_path):
    # 获取请求参数
    server_id = request.args.get('server_id')
    ssh, err, code = get_ssh_client(server_id, active_connections)
    if err:
        return err, code
    
    try:
        # 获取请求中的文件内容
        data = request.get_json()
        content = data.get('content', '')
        
        # 构造备份文件路径
        backup_path = f"/{file_path}.backup_{int(time.time())}"
        
        # 打开SFTP连接
        sftp = ssh.open_sftp()
        
        # 尝试备份原文件
        try:
            sftp.rename(f"/{file_path}", backup_path)
        except FileNotFoundError:
            # 如果原文件不存在，跳过备份
            pass
        
        # 写入新内容到文件
        with sftp.open(f"/{file_path}", 'w') as f:
            f.write(content)
        
        # 关闭SFTP连接并返回成功信息
        sftp.close()
        return jsonify({
            "message": "文件保存成功",
            "backup_path": backup_path if 'backup_path' in locals() else None
        })
    except Exception as e:
        # 处理连接异常
        return jsonify({"error": format_ssh_error(e)}), 500


# 删除配置文件接口
# 删除服务器上指定的配置文件
@api_bp.route('/config/files/<path:file_path>', methods=['DELETE'])
@login_required
def delete_config_file(file_path):
    # 获取请求参数
    server_id = request.args.get('server_id')
    ssh, err, code = get_ssh_client(server_id, active_connections)
    if err:
        return err, code
    
    try:
        # 打开SFTP连接
        sftp = ssh.open_sftp()
        
        # 删除文件
        sftp.remove(f"/{file_path}")
        
        # 关闭SFTP连接并返回成功信息
        sftp.close()
        return jsonify({"message": f"文件 {file_path} 删除成功"})
    except FileNotFoundError:
        # 文件不存在
        return jsonify({"error": "文件不存在"}), 404
    except Exception as e:
        # 处理连接异常
        return jsonify({"error": format_ssh_error(e)}), 500


# 获取服务错误日志接口
# 获取指定服务的所有错误日志（来自所有日志文件）
@api_bp.route('/services/<service_name>/errors', methods=['GET'])
@login_required
def get_service_errors(service_name):
    """获取服务的所有错误日志（来自所有日志文件）"""
    # 获取请求参数
    server_id = request.args.get('server_id')
    if not server_id:
        return jsonify({"error": "缺少 server_id 参数"}), 400

    # 构造用户-服务器唯一标识
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


# 获取服务日志文件列表接口
# 获取指定服务的所有日志文件路径
@api_bp.route('/services/<service_name>/log_files', methods=['GET'])
@login_required
def get_service_log_files(service_name):
    # 查找服务信息
    service_info = next((s for s in services if s["name"] == service_name), None)
    if not service_info:
        return jsonify({"error": "服务不存在"}), 404
    
    # 获取日志文件路径列表
    log_paths = service_info.get("log_paths", [])
    
    # 返回服务信息和日志文件列表
    return jsonify({
        "service_name": service_name,
        "display_name": service_info.get("display_name", service_name),
        "log_files": [{"path": path, "name": os.path.basename(path)} for path in log_paths if path]
    })


# 比较配置文件接口
# 比较服务器上的文件与本地内容的差异
@api_bp.route('/config/compare', methods=['POST'])
@login_required
def compare_files():
    # 获取请求参数
    server_id = request.args.get('server_id')
    ssh, err, code = get_ssh_client(server_id, active_connections)
    if err:
        return err, code
    
    try:
        # 获取请求中的文件路径和本地内容
        data = request.get_json()
        file_path = data.get('file_path')
        local_content = data.get('local_content')
        
        # 验证必要参数
        if not file_path or local_content is None:
            return jsonify({"error": "缺少必要参数: file_path, local_content"}), 400
        
        # 打开SFTP连接
        sftp = ssh.open_sftp()
        
        # 读取服务器上的文件内容
        try:
            with sftp.open('/' + file_path, 'r') as f:
                server_content = f.read().decode('utf-8', errors='ignore')
        except FileNotFoundError:
            # 如果文件不存在，设为空字符串
            server_content = ""
        finally:
            sftp.close()
        
        # 将内容按行分割
        server_lines = server_content.splitlines(keepends=True)
        local_lines = local_content.splitlines(keepends=True)
        
        # 生成统一差异格式的结果
        diff_result = list(unified_diff(
            server_lines,
            local_lines,
            fromfile=f'服务器: {file_path}',
            tofile=f'本地: {file_path}',
            lineterm=''
        ))
        
        # 统计变更数量
        added_count = len([line for line in diff_result if line.startswith('+')])
        removed_count = len([line for line in diff_result if line.startswith('-')])
        
        # 返回比较结果
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
        # 处理异常情况
        return jsonify({"error": format_ssh_error(e)}), 500


# 获取错误模式配置接口
# 获取所有错误日志匹配模式
@api_bp.route('/config/error_patterns', methods=['GET'])
def get_error_patterns():
    try:
        # 获取错误模式配置文件路径
        patterns_file = get_error_patterns_file()
        
        # 读取错误模式配置
        if os.path.exists(patterns_file):
            with open(patterns_file, 'r', encoding='utf-8') as f:
                patterns = json.load(f)
        else:
            patterns = []
        
        # 返回错误模式列表
        return jsonify(patterns)
    except Exception as e:
        # 处理异常情况
        return jsonify({"error": format_ssh_error(e)}), 500


# 保存错误模式配置接口
# 保存错误日志匹配模式配置
@api_bp.route('/config/error_patterns', methods=['POST'])
@login_required
def save_error_patterns():
    try:
        # 获取请求中的模式配置
        patterns = request.json
        
        # 获取错误模式配置文件路径
        patterns_file = get_error_patterns_file()
        
        # 确保目录存在
        os.makedirs(os.path.dirname(patterns_file), exist_ok=True)
        
        # 保存错误模式配置到文件
        with open(patterns_file, 'w', encoding='utf-8') as f:
            json.dump(patterns, f, ensure_ascii=False, indent=4)
        
        # 返回保存成功信息
        return jsonify({"message": "保存成功"})
    except Exception as e:
        # 处理异常情况
        return jsonify({"error": str(e)}), 500

# ==========================
# SFTP 管理接口（Flask + Paramiko）
# 说明：与已有的 get_ssh_client / active_connections 集成
# 路径前缀：/api/sftp/...
# ==========================
from io import BytesIO
from flask import send_file




# 上传文件（multipart/form-data）
@api_bp.route('/api/sftp/upload', methods=['POST'])
@login_required
def sftp_upload():
    """
    上传文件到远程服务器
    FormData:
      - files: file input (可多个)
      - path (query or form) 上传到的目录（必需）
      - overwrite (form) 可选，若为 'true' 则覆盖已存在文件
      - server_id (query/form) 必需或通过连接使用 active_connections
    返回: { uploaded: [...], errors: [...] , path: '/target/path' }
    """
    server_id = request.args.get('server_id') or request.form.get('server_id')
    if not server_id:
        return jsonify({"error": "缺少 server_id 参数"}), 400

    target_path = request.args.get('path') or request.form.get('path') or '/'
    overwrite = (request.form.get('overwrite', 'false').lower() == 'true')

    # files 支持多个（前端使用 input multiple）
    files = request.files.getlist('files')
    if not files:
        return jsonify({"error": "没有上传的文件"}), 400

    ssh, err, code = get_ssh_client(server_id, active_connections)
    if err:
        return err, code

    sftp = None
    uploaded = []
    errors = []
    try:
        sftp = ssh.open_sftp()

        # 确保目标目录存在：若不存在尝试创建（仅创建一层，不做递归复杂逻辑）
        try:
            sftp.listdir(target_path)
        except IOError:
            try:
                sftp.mkdir(target_path)
            except Exception:
                # 如果创建失败，继续尝试写文件（有些环境允许直接写）
                pass

        for f in files:
            filename = f.filename
            remote_file_path = os.path.join(target_path, filename).replace("\\", "/")
            try:
                # 如果已存在且不允许覆盖，报错
                try:
                    sftp.stat(remote_file_path)
                    exists = True
                except IOError:
                    exists = False

                if exists and not overwrite:
                    errors.append({"file": filename, "error": "目标已存在 (设置 overwrite=true 可覆盖)"})
                    continue

                # 写入远程文件（以二进制）
                # 使用 sftp.open 以便设置模式
                with sftp.open(remote_file_path, 'wb') as remote_f:
                    # Flask 的 FileStorage 已经是流式，可以直接读取
                    chunk = f.stream.read(64 * 1024)
                    while chunk:
                        remote_f.write(chunk)
                        chunk = f.stream.read(64 * 1024)
                uploaded.append({"file": filename, "path": remote_file_path})
            except Exception as ef:
                errors.append({"file": filename, "error": format_ssh_error(ef)})
    except Exception as e:
        return jsonify({"error": format_ssh_error(e)}), 500
    finally:
        if sftp:
            try:
                sftp.close()
            except:
                pass

    return jsonify({"uploaded": uploaded, "errors": errors, "path": target_path})


# 下载文件（将远程文件流式返回）
@api_bp.route('/api/sftp/download', methods=['GET'])
@login_required
def sftp_download():
    """
    请求参数:
      - server_id (query) 必需
      - path (query) 远程文件完整路径，必需
    返回: flask send_file 流
    """
    server_id = request.args.get('server_id')
    remote_path = request.args.get('path')
    if not server_id or not remote_path:
        return jsonify({"error": "缺少 server_id 或 path 参数"}), 400

    ssh, err, code = get_ssh_client(server_id, active_connections)
    if err:
        return err, code

    sftp = None
    try:
        sftp = ssh.open_sftp()

        # 读取远程文件到内存（对大文件需谨慎，可改为分块流）
        remote_file = sftp.open(remote_path, 'rb')
        buf = BytesIO()
        chunk = remote_file.read(64 * 1024)
        while chunk:
            buf.write(chunk)
            chunk = remote_file.read(64 * 1024)
        remote_file.close()
        buf.seek(0)

        filename = os.path.basename(remote_path)
        return send_file(buf, as_attachment=True, download_name=filename)
    except FileNotFoundError:
        return jsonify({"error": "文件不存在"}), 404
    except Exception as e:
        return jsonify({"error": format_ssh_error(e)}), 500
    finally:
        if sftp:
            try:
                sftp.close()
            except:
                pass


# 删除文件或空目录
@api_bp.route('/api/sftp/delete', methods=['DELETE'])
@login_required
def sftp_delete():
    """
    请求参数:
      - server_id (query) 必需
      - path (query) 要删除的文件或目录路径，必需
      - type (query) 可选 'file' or 'dir'，默认根据 stat 判断
    """
    server_id = request.args.get('server_id')
    path = request.args.get('path')
    if not server_id or not path:
        return jsonify({"error": "缺少 server_id 或 path 参数"}), 400

    ssh, err, code = get_ssh_client(server_id, active_connections)
    if err:
        return err, code

    sftp = None
    try:
        sftp = ssh.open_sftp()
        try:
            st = sftp.stat(path)
        except IOError:
            return jsonify({"error": "路径不存在"}), 404

        if stat.S_ISDIR(st.st_mode):
            # 仅删除空目录
            try:
                sftp.rmdir(path)
                return jsonify({"message": "目录已删除"})
            except Exception as e:
                return jsonify({"error": format_ssh_error(e)}), 500
        else:
            try:
                sftp.remove(path)
                return jsonify({"message": "文件已删除"})
            except Exception as e:
                return jsonify({"error": format_ssh_error(e)}), 500
    except Exception as e:
        return jsonify({"error": format_ssh_error(e)}), 500
    finally:
        if sftp:
            try:
                sftp.close()
            except:
                pass


# 新建目录
@api_bp.route('/api/sftp/mkdir', methods=['POST'])
@login_required
def sftp_mkdir():
    """
    请求参数:
      - server_id (query or form) 必需
      - path (form/json) 要创建的目录路径，必需
    """
    server_id = request.args.get('server_id') or request.form.get('server_id')
    path = request.json.get('path') if request.is_json else request.form.get('path')
    if not server_id or not path:
        return jsonify({"error": "缺少 server_id 或 path 参数"}), 400

    ssh, err, code = get_ssh_client(server_id, active_connections)
    if err:
        return err, code

    sftp = None
    try:
        sftp = ssh.open_sftp()
        try:
            sftp.mkdir(path)
            return jsonify({"message": "目录创建成功", "path": path})
        except Exception as e:
            return jsonify({"error": format_ssh_error(e)}), 500
    finally:
        if sftp:
            try:
                sftp.close()
            except:
                pass


# 重命名 / 移动
@api_bp.route('/api/sftp/rename', methods=['POST'])
@login_required
def sftp_rename():
    """
    请求 body (json 或 form):
      - server_id
      - old_path
      - new_path
    """
    data = request.get_json() or request.form
    server_id = data.get('server_id')
    old_path = data.get('old_path')
    new_path = data.get('new_path')
    if not server_id or not old_path or not new_path:
        return jsonify({"error": "缺少参数: server_id, old_path, new_path"}), 400

    ssh, err, code = get_ssh_client(server_id, active_connections)
    if err:
        return err, code

    sftp = None
    try:
        sftp = ssh.open_sftp()
        try:
            sftp.rename(old_path, new_path)
            return jsonify({"message": "重命名/移动成功", "old": old_path, "new": new_path})
        except Exception as e:
            return jsonify({"error": format_ssh_error(e)}), 500
    finally:
        if sftp:
            try:
                sftp.close()
            except:
                pass


@api_bp.route('/sftp_page')
@login_required
def sftp_page():
    # 如果你使用 Jinja2，可将 servers 列表传过去渲染
    servers = load_servers()
    return render_template('sftp.html', servers=servers)
