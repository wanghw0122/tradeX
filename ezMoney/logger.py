import logging
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
import datetime
import os
from functools import wraps
import threading

log_lock = threading.Lock()
class LockedRotatingFileHandler(RotatingFileHandler):
    def emit(self, record):
        with log_lock:
            super().emit(record)


def setup_logging(name):
    # 获取当前日期
    current_date = datetime.datetime.now().strftime('%Y%m%d')
    log_dir = 'D:\\workspace\\TradeX\\logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    if name == 'my_logger':
    # 创建日志记录器
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # 创建文件处理器，每天生成一个新的日志文件
        file_handler = TimedRotatingFileHandler(f'{log_dir}/app_{current_date}.log', when='midnight', interval=1, backupCount=7, encoding='utf-8')
        file_handler.suffix = '%Y%m%d'
        file_handler.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)  

        # 创建日志格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 将处理器添加到日志记录器
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger
    else:
        log_dir = f'D:\workspace\TradeX\logs\{name}'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_file = os.path.join(log_dir, f'{name}.log')
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        file_handler = RotatingFileHandler(log_file, mode='a', maxBytes=10*1024*1024, backupCount=10, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        return logger

# 配置日志记录
logger = setup_logging("my_logger")
strategy_logger = setup_logging("strategy_logger")
order_logger = setup_logging("order_logger")
order_success_logger = setup_logging("order_success_logger")



# 配置日志记录器
order_logger = logging.getLogger('order_logger')
order_logger.setLevel(logging.DEBUG)

# 创建 RotatingFileHandler，设置 delay=True
handler = LockedRotatingFileHandler(
    'D:\\workspace\\TradeX\\logs\\order_logger\\order_logger.log',
    maxBytes=1024 * 1024 * 5,  # 5 MB
    backupCount=5,
    delay=True,
    encoding='utf-8'
)
handler.setLevel(logging.DEBUG)

# 创建格式化器并添加到处理器
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# 将处理器添加到日志记录器
order_logger.addHandler(handler)

def catch(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"An error occurred in {func.__name__}: {e}")
            raise
    return wrapper