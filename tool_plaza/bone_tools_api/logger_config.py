"""日志配置模块

统一的日志配置，支持控制台和文件输出，自动限制输出长度
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


# 日志输出最大长度配置
MAX_LOG_LENGTH = 500  # 控制台输出最大字符数
MAX_FILE_LOG_LENGTH = 2000  # 文件输出最大字符数


class TruncatingFormatter(logging.Formatter):
    """截断日志格式化器，自动限制日志长度"""

    def __init__(self, fmt=None, datefmt=None, max_length=500):
        super().__init__(fmt, datefmt)
        self.max_length = max_length

    def format(self, record):
        """格式化日志记录，并截断过长内容"""
        # 先进行正常格式化
        formatted = super().format(record)

        # 如果超长则截断
        if len(formatted) > self.max_length:
            truncated = formatted[:self.max_length]
            # 找到最后一个完整的字符位置
            if truncated.rfind('\n') > self.max_length - 100:
                truncated = truncated[:truncated.rfind('\n')]
            formatted = truncated + f"... [截断，总长度: {len(formatted)}]"

        return formatted


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    console_output: bool = True,
    file_output: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """配置并返回logger实例

    Args:
        name: logger名称
        log_file: 日志文件路径，None则使用默认路径
        level: 日志级别
        console_output: 是否输出到控制台
        file_output: 是否输出到文件
        max_bytes: 单个日志文件最大大小
        backup_count: 保留的日志文件备份数量

    Returns:
        配置好的logger实例
    """
    # 创建logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 清除已有的handlers（避免重复添加）
    logger.handlers.clear()

    # 控制台handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_format = TruncatingFormatter(
            fmt='%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            max_length=MAX_LOG_LENGTH
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

    # 文件handler
    if file_output:
        # 创建logs目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # 确定日志文件路径
        if log_file is None:
            log_file = log_dir / f"{name}.log"
        else:
            log_file = Path(log_file)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_format = TruncatingFormatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            max_length=MAX_FILE_LOG_LENGTH
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    # 防止日志传播到root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """获取已配置的logger或创建新的logger

    Args:
        name: logger名称

    Returns:
        logger实例
    """
    logger = logging.getLogger(name)

    # 如果logger还没有handlers，则配置它
    if not logger.handlers:
        return setup_logger(name)

    return logger


def truncate_text(text: str, max_length: int = MAX_LOG_LENGTH) -> str:
    """截断文本到指定长度

    Args:
        text: 要截断的文本
        max_length: 最大长度

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text

    truncated = text[:max_length]
    # 尝试在合适的位置截断（如换行符）
    if '\n' in truncated[-100:]:
        last_newline = truncated.rfind('\n')
        if last_newline > max_length - 200:
            truncated = truncated[:last_newline]

    return truncated + f"... [截断，总长度: {len(text)}]"


def log_data(logger: logging.Logger, level: int, message: str, data: any, max_length: int = MAX_LOG_LENGTH):
    """记录日志并自动截断数据

    Args:
        logger: logger实例
        level: 日志级别
        message: 日志消息
        data: 要记录的数据（自动转为字符串）
        max_length: 最大长度
    """
    data_str = str(data)
    truncated_data = truncate_text(data_str, max_length)

    full_message = f"{message}: {truncated_data}"
    logger.log(level, full_message)


# 预配置的logger实例
server_logger = None
tool_logger = None


def init_loggers():
    """初始化所有预配置的logger"""
    global server_logger, tool_logger

    # 服务器logger
    server_logger = setup_logger(
        name="tool_server",
        log_file=Path("logs") / "server.log",
        level=logging.INFO
    )

    # 工具执行logger
    tool_logger = setup_logger(
        name="tool_execution",
        log_file=Path("logs") / "tool_execution.log",
        level=logging.INFO
    )

    server_logger.info("日志系统初始化完成")


# 在模块导入时自动初始化
init_loggers()
