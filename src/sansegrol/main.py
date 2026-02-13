from logger import init_logging, get_logger, get_multiprocess_queue, setup_child_process_logger, cleanup_logging
from qt import Window, install_qt_handler
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QUrl

import sys
import os
import multiprocessing
import importlib.util
import time
from pathlib import Path
import json


log_file = init_logging()
logger = get_logger("main")
# install Qt handler (writes to same shared log file via get_logger("qt"))
install_qt_handler()


def run_flask_server(flask_server_path: str, debug: bool = False):
    """
    Run Flask server in a separate process.
    Configures logging to use the parent process"s queue.
    """
    # Configure child process logger to use queue
    queue_obj = get_multiprocess_queue()
    if queue_obj:
        setup_child_process_logger(queue_obj)
    
    # Get project root from environment variable
    sansegrol_path = os.environ.get("Sansegrol")
    if not sansegrol_path:
        flask_logger = get_logger("flask")
        flask_logger.error("Sansegrol environment variable not set")
        return
    
    # Import Flask server dynamically
    flask_server_path = str(Path(sansegrol_path) / flask_server_path).replace("\\", "/")
    
    if not Path(flask_server_path).exists():
        flask_logger = get_logger("flask")
        flask_logger.error(f"Flask server file not found: {flask_server_path}")
        return
    
    # Load the module dynamically
    spec = importlib.util.spec_from_file_location("flask_app", str(flask_server_path))
    if spec is None or spec.loader is None:
        flask_logger = get_logger("flask")
        flask_logger.error(f"Failed to load Flask server from {flask_server_path}")
        return
    
    try:
        flask_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(flask_module)
        
        # Run the server
        if hasattr(flask_module, "run_server"):
            flask_module.run_server(debug=debug)
        else:
            flask_logger = get_logger("flask")
            flask_logger.error("run_server function not found in Flask module")
    except Exception as e:
        flask_logger = get_logger("flask")
        flask_logger.error(f"Error running Flask server: {e}")

def get_configure(sansegrol_path: str) -> dict:
    """Get configuration dictionary"""
    config_path = Path(sansegrol_path) / "config" / "sansegrol.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError as e:
                logger.fatal(f"Error decoding config.json: {e}")
                sys.exit(-1)
    else:
        logger.fatal("config.json not found, using default configuration")
        sys.exit(-1)

if __name__ == "__main__":
    sansegrol_path = os.environ.get("Sansegrol")

    try:
        assert sansegrol_path is not None
        assert os.path.exists(sansegrol_path)
    except AssertionError:
        logger.error("Environment variable `Sansegrol` is not set or path does not exist.")
        sys.exit(1)

    browser_data_path = os.path.join(sansegrol_path, ".browser_data").replace("\\", "/")  # Normalize path for Windows
    configure         = get_configure(sansegrol_path)

    porject_name      = configure.get("project_name", "Sansegrol")
    version           = configure.get("version", "1.0.0")
    qt_title          = configure.get("qt_settings", {}).get("title", "Sansegrol")
    qt_author         = configure.get("qt_settings", {}).get("author", "Sansegron")
    qt_show_maximium  = configure.get("qt_settings", {}).get("show_maximum", True)
    defualt_width     = configure.get("qt_settings", {}).get("default_width", 1280)
    defualt_height    = configure.get("qt_settings", {}).get("default_height", 720)
    qt_icon_path      = Path(sansegrol_path) / configure.get("qt_settings", {}).get("icon_path", "assets/icons/icon128.png")
    flask_host        = configure.get("flask_settings", {}).get("host", "http://localhost")
    flask_port        = configure.get("flask_settings", {}).get("port", 8720)
    flask_debug       = configure.get("flask_settings", {}).get("debug", False)
    flask_server_path = configure.get("flask_settings", {}).get("server_path", "web/server/index.py")

    logger.info(f"Working directory: {sansegrol_path}")
    logger.info(f"Browser data path: {browser_data_path}")
    logger.info(f"Sansegrol Path: {sansegrol_path}")
    logger.info(f"Configuration: {configure}")

    if qt_icon_path is not None and os.path.exists(qt_icon_path):
        qt_icon_path = str(qt_icon_path)
        logger.info(f"Using icon path: {qt_icon_path}")
    else:
        qt_icon_path = ""
        logger.warning(f"Icon path does not exist or is not set")

    # Start Flask server in a separate process
    flask_process = multiprocessing.Process(target=run_flask_server, args=(flask_server_path, flask_debug), daemon=True)
    flask_process.start()
    logger.info(f"Flask server started on {flask_host}:{flask_port}")

    # Wait a bit for Flask to start
    time.sleep(2)

    app = QApplication(sys.argv)
    app.setApplicationName(qt_title)
    app.setOrganizationName(qt_author)
    app.setApplicationVersion(version)

    window = Window(
        qt_title, 
        (50, 50, defualt_width, defualt_height), 
        browser_data_path,
        icon_path=qt_icon_path
    )
    # Load the Flask server URL
    window.load_url(QUrl(f"{flask_host}:{flask_port}/"))
    if qt_show_maximium:
        window.showMaximized()
    else:
        window.show()

    sys.exit(app.exec_())