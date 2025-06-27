import logging
from functools import wraps
import inspect

LOG_COLORS = {
    'DEBUG': '\033[94m',     # Bright Blue
    'WARNING': '\033[93m',   # Bright Yellow
    'ERROR': '\033[91m',     # Bright Red
}
RESET = '\033[0m'

class ColorFormatter(logging.Formatter):
    def format(self, record):
        levelname = record.levelname
        color = LOG_COLORS.get(levelname, '')
        record.levelname = f"{color}{levelname}{RESET}"
        record.msg = f"{record.msg}"
        return super().format(record)

handler = logging.StreamHandler()
formatter = ColorFormatter('%(levelname)s : %(message)s')
handler.setFormatter(formatter)
logging.basicConfig(level=logging.DEBUG, handlers=[handler])

def log(arg = None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if isinstance(arg, str) and arg:
                logging.debug(f"{LOG_COLORS['DEBUG']}{arg}{RESET}")

            sig = inspect.signature(func)
            params = list(sig.parameters)
            log_args = args[1:] if params and params[0] in ('self', 'cls') else args

            msg = f"Calling {func.__name__} with args: {log_args}"
            if kwargs:
                msg += f", kwargs: {kwargs}"
            logging.debug(msg)

            return func(*args, **kwargs)
        return wrapper

    if callable(arg):
        return decorator(arg)
    else:
        return decorator