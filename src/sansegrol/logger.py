import logging
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
import os
import time
import queue

# add custom FAULT level (between ERROR=40 and CRITICAL=50)
FAULT_LEVEL = 45
logging.addLevelName(FAULT_LEVEL, "FAULT")

def fault(self, message, *args, **kws):
    if self.isEnabledFor(FAULT_LEVEL):
        self._log(FAULT_LEVEL, message, args, **kws)
logging.Logger.fault = fault # type: ignore

# Global logging queue for multiprocess support
_logging_queue = None
_queue_listener = None


class CustomFormatter(logging.Formatter):
    def __init__(self):
        super().__init__("%(message)s")

    def format(self, record):
        t = time.localtime(record.created)
        date_custom = f"{t.tm_year}.{t.tm_mon}.{t.tm_mday} {t.tm_hour}:{t.tm_min}:{t.tm_sec}"
        prefix = f"[{date_custom}] [{record.name}/{record.levelname}] "
        msg = super().format(record)
        return prefix + msg


def init_logging(log_dir: str = None): # type: ignore
    """
    Initialize a single shared logging handler writing to a per-run file.
    Handlers are attached to the root logger so all named loggers propagate to same file.
    Sets up multiprocess support with a queue-based listener.
    """

    global _logging_queue, _queue_listener

    sansegrol_path = os.environ.get("Sansegrol")

    if log_dir is None:
        log_dir = os.path.join(sansegrol_path, "logs").replace("\\", "/")  # Normalize path for Windows
    os.makedirs(log_dir, exist_ok=True)

    now = time.localtime()

    base_name = f"{now.tm_year}-{now.tm_mon}-{now.tm_mday}-{int(time.time())}-log.log"
    log_file = os.path.join(log_dir, base_name).replace("\\", "/")  # Normalize path for Windows

    if os.path.exists(log_file):
        timestr = time.strftime("%H%M%S", now)
        log_file = os.path.join(log_dir, f"{now.tm_year}-{now.tm_mon}-{now.tm_mday}-{timestr}-log.log").replace("\\", "/")  # Normalize path for Windows

    root = logging.getLogger()
    if not root.handlers:
        root.setLevel(logging.INFO)
        
        # Create file handler
        fh = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
        fh.setFormatter(CustomFormatter())
        
        # Create console handler
        ch = logging.StreamHandler()
        ch.setFormatter(CustomFormatter())
        
        # Set up multiprocess queue and listener
        _logging_queue = queue.Queue()
        _queue_listener = QueueListener(_logging_queue, fh, ch, respect_handler_level=True)
        _queue_listener.start()
        
        # Add queue handler to root logger for multiprocess support
        qh = QueueHandler(_logging_queue)
        root.addHandler(qh)

    return log_file


def get_logger(name: str):
    """
    Return a named logger that propagates to the shared handlers.
    """
    
    logger = logging.getLogger(name)
    return logger


def get_multiprocess_queue():
    """
    Get the queue for multiprocess logging.
    Used by child processes to send logs to the parent process.
    """

    global _logging_queue
    return _logging_queue


def setup_child_process_logger(queue_obj: "queue.Queue") -> logging.Logger: # type: ignore
    """
    Configure a child process logger to send logs to the parent process via queue.
    Call this in the child process after initialization.
    
    Args:
        queue_obj: The queue object from get_multiprocess_queue()
    
    Returns:
        A logger configured with QueueHandler
    """

    child_logger = logging.getLogger()
    child_logger.setLevel(logging.INFO)
    
    # Remove all existing handlers
    for handler in child_logger.handlers[:]:
        child_logger.removeHandler(handler)
    
    # Add queue handler to send logs to parent
    qh = QueueHandler(queue_obj)
    child_logger.addHandler(qh)
    
    return logging.getLogger("flask")


def cleanup_logging():
    """
    Clean up logging resources. Call this when shutting down.
    """
    
    global _queue_listener
    if _queue_listener:
        _queue_listener.stop()
