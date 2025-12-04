"""
统一异常处理模块
提供标准化的异常类和错误处理机制
"""

from flask import jsonify
from functools import wraps
import traceback
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==========================
# 自定义异常类
# ==========================

class APIException(Exception):
    """API异常基类"""
    def __init__(self, message: str, status_code: int = 500, error_code: str = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or f"ERROR_{status_code}"


class ValidationError(APIException):
    """参数验证错误"""
    def __init__(self, message: str):
        super().__init__(message, status_code=400, error_code="VALIDATION_ERROR")


class AuthenticationError(APIException):
    """认证错误"""
    def __init__(self, message: str = "认证失败"):
        super().__init__(message, status_code=401, error_code="AUTH_ERROR")


class PermissionError(APIException):
    """权限错误"""
    def __init__(self, message: str = "权限不足"):
        super().__init__(message, status_code=403, error_code="PERMISSION_ERROR")


class ResourceNotFoundError(APIException):
    """资源未找到错误"""
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, status_code=404, error_code="NOT_FOUND")


class ServerConnectionError(APIException):
    """服务器连接错误"""
    def __init__(self, message: str):
        super().__init__(message, status_code=500, error_code="CONNECTION_ERROR")


class FileOperationError(APIException):
    """文件操作错误"""
    def __init__(self, message: str):
        super().__init__(message, status_code=500, error_code="FILE_ERROR")


# ==========================
# 异常处理装饰器
# ==========================

def handle_exceptions(f):
    """
    统一异常处理装饰器
    自动捕获并处理函数中的异常，返回标准化的错误响应
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except APIException as e:
            # 处理自定义API异常
            logger.warning(f"{e.error_code}: {e.message}")
            return jsonify({
                "error": e.message,
                "error_code": e.error_code
            }), e.status_code
        except Exception as e:
            # 处理未预期的异常
            logger.error(f"Unexpected error in {f.__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                "error": "服务器内部错误",
                "error_code": "INTERNAL_ERROR",
                "details": str(e) if logger.level == logging.DEBUG else None
            }), 500
    
    return decorated_function


def handle_ssh_exceptions(f):
    """
    SSH操作专用异常处理装饰器
    自动处理SSH相关的异常并转换为友好的错误信息
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            error_msg = format_ssh_error(e)
            logger.error(f"SSH error in {f.__name__}: {error_msg}")
            raise ServerConnectionError(error_msg)
    
    return decorated_function


# ==========================
# 错误格式化函数
# ==========================

def format_ssh_error(error) -> str:
    """格式化SSH连接错误信息，提供更友好的中文提示"""
    error_msg = str(error)
    
    # SSH 特定错误
    error_mappings = {
        "Administratively prohibited": "操作被拒绝（请重新连接）",
        "Permission denied": "权限被拒绝",
        "No such file": "文件或目录不存在",
        "Network is unreachable": "网络不可达",
        "Connection refused": "连接被拒绝",
        "Authentication failed": "身份验证失败",
        "timed out": "连接超时",
        "No existing session": "会话不存在",
        "Invalid argument": "参数无效",
        "Bad file descriptor": "文件描述符错误（连接已断开）",
    }
    
    # 查找匹配的错误类型
    for key, value in error_mappings.items():
        if key.lower() in error_msg.lower():
            return value
    
    # 未识别的错误类型，返回原始错误信息
    return error_msg


def format_error_response(error: Exception, include_traceback: bool = False) -> dict:
    """
    格式化错误响应
    
    Args:
        error: 异常对象
        include_traceback: 是否包含堆栈跟踪信息（仅用于调试）
    
    Returns:
        格式化的错误字典
    """
    response = {
        "error": str(error),
        "error_type": type(error).__name__
    }
    
    if isinstance(error, APIException):
        response["error_code"] = error.error_code
    
    if include_traceback:
        response["traceback"] = traceback.format_exc()
    
    return response


# ==========================
# 验证辅助函数
# ==========================

def validate_required_fields(data: dict, required_fields: list):
    """
    验证必需字段是否存在
    
    Args:
        data: 要验证的数据字典
        required_fields: 必需字段列表
    
    Raises:
        ValidationError: 如果缺少必需字段
    """
    missing_fields = [field for field in required_fields if field not in data or not data[field]]
    
    if missing_fields:
        raise ValidationError(f"缺少必需字段: {', '.join(missing_fields)}")


def validate_not_empty(value, field_name: str):
    """
    验证值不为空
    
    Args:
        value: 要验证的值
        field_name: 字段名称
    
    Raises:
        ValidationError: 如果值为空
    """
    if not value:
        raise ValidationError(f"{field_name}不能为空")


def validate_server_id(server_id: str):
    """
    验证服务器ID
    
    Args:
        server_id: 服务器ID
    
    Raises:
        ValidationError: 如果服务器ID无效
    """
    if not server_id:
        raise ValidationError("服务器ID不能为空")


# ==========================
# 使用示例
# ==========================

"""
使用示例：

# 1. 在路由中使用异常处理装饰器
@api_bp.route('/servers', methods=['POST'])
@login_required
@handle_exceptions
def add_server():
    data = request.json
    
    # 验证必需字段
    validate_required_fields(data, ['name', 'host', 'port', 'username'])
    
    # 业务逻辑
    servers = load_servers()
    if any(s["id"] == data["id"] for s in servers):
        raise ValidationError("服务器ID已存在")
    
    servers.append(data)
    save_servers(servers)
    
    return jsonify(data), 201


# 2. 在SSH操作中使用
@api_bp.route('/servers/<server_id>/connect', methods=['POST'])
@login_required
@handle_exceptions
@handle_ssh_exceptions
def connect_server(server_id):
    validate_server_id(server_id)
    
    target = find_server(server_id)
    if not target:
        raise ResourceNotFoundError("服务器不存在")
    
    # SSH操作会被 handle_ssh_exceptions 自动处理
    ssh = connect_via_ssh(target)
    active_connections[server_id] = ssh
    
    return jsonify({"message": f"连接成功: {target['name']}"}), 200


# 3. 手动抛出异常
if 'user_id' not in session:
    raise AuthenticationError("用户未登录")

if not has_permission(user, resource):
    raise PermissionError("无权访问此资源")
"""
