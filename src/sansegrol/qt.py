from PyQt5.QtCore import qInstallMessageHandler, QtMsgType
from PyQt5.QtCore import QUrl, QStandardPaths, Qt
from PyQt5.QtWidgets import QMainWindow, QShortcut, QDockWidget, QAction
from PyQt5.QtGui import QKeySequence, QIcon
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage, QWebEngineSettings

from logger import get_logger, init_logging

import os


log_file = init_logging()
logger = get_logger("custom_qt")


class CustomWebEnginePage(QWebEnginePage):
    """
    Custom WebEngine page to handle link navigation and capture JavaScript console messages
    """

    def __init__(self, parent=None):
        super(CustomWebEnginePage, self).__init__(parent)
        # Keep strong references to popup windows to prevent C++ objects
        # from being deleted by Python garbage collection
        self._popup_windows = []
        # Get JavaScript logger
        self._js_logger = get_logger("javascript")
    
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        """
        Capture JavaScript console messages at the Qt level.
        level: 0 = LogMessageLevel, 1 = WarningMessageLevel, 2 = ErrorMessageLevel
        """
        # Map Qt console levels to logging levels
        level_map = {
            0: "info",      # LogMessageLevel
            1: "warning",   # WarningMessageLevel
            2: "error"      # ErrorMessageLevel
        }
        
        log_level = level_map.get(level, "info")
        
        # Format the message with source information
        if sourceID:
            full_message = f"[{sourceID}:{lineNumber}] {message}"
        else:
            full_message = message
        
        # Log using the appropriate level
        if log_level == "error":
            self._js_logger.error(full_message)
        elif log_level == "warning":
            self._js_logger.warning(full_message)
        else:
            self._js_logger.info(full_message)
    
    def createWindow(self, type):
        """
        Handle new window creation (e.g., target="_blank")
        """

        # Create a new QWebEngineView to display the popup content
        new_view = QWebEngineView()
        new_page = CustomWebEnginePage(new_view)
        new_view.setPage(new_page)

        # Open in a new native window
        new_window = QMainWindow()
        new_window.setCentralWidget(new_view)
        new_window.resize(800, 600)
        new_window.show()

        # Keep references to prevent Python GC from deleting underlying
        # C++ objects used by the WebEngine
        try:
            self._popup_windows.append((new_window, new_view, new_page))
        except Exception:
            # Fallback: if self._popup_windows is inaccessible, store
            # the popup references on the parent object instead
            parent = self.parent() if hasattr(self, "parent") else None
            if parent is not None:
                if not hasattr(parent, "_popup_windows"):
                    parent._popup_windows = [] # type: ignore
                parent._popup_windows.append((new_window, new_view, new_page)) # type: ignore

        # Return the page for the new window
        return new_view.page()

class CustomWebEngineView(QWebEngineView):
    """
    Custom QWebEngineView that adds an "Inspect element" action to the context menu
    """
    
    def __init__(self, parent=None):
        super(CustomWebEngineView, self).__init__(parent)

    def contextMenuEvent(self, event): # type: ignore
        # use page"s standard context menu when available
        page = self.page()
        menu = None
        try:
            if page is not None and hasattr(page, "createStandardContextMenu"):
                menu = page.createStandardContextMenu()
        except Exception:
            menu = None
        if menu is None:
            from PyQt5.QtWidgets import QMenu
            menu = QMenu(self)
        inspect_act = QAction("Inspect element", self)

        # Call the parent window"s devtools open function and trigger the
        # InspectElement action on the page
        def on_inspect():
            parent = self.window()
            if hasattr(parent, "_open_devtools"):
                parent._open_devtools() # type: ignore
            try:
                act = self.page().action(QWebEnginePage.WebAction.InspectElement) # type: ignore
                if act is not None:
                    act.trigger()
            except Exception:
                pass

        inspect_act.triggered.connect(on_inspect)
        menu.addAction(inspect_act)
        menu.exec_(event.globalPos())

class Window(QMainWindow):
    def __init__(self, title: str, geometrys: tuple, browser_data_path: str, html_content: str = None, icon_path: str = ""): # type: ignore
        super(Window, self).__init__()

        self.title     = title
        self.geometrys = geometrys
        self.browser_data_path = browser_data_path
        self.icon_path = icon_path

        self.setWindowTitle(title)
        self.setGeometry(self.geometrys[0], self.geometrys[1], self.geometrys[2], self.geometrys[3])
        
        if self.icon_path:
            self.setWindowIcon(QIcon(self.icon_path))

        # Obtain and log the default storage path
        default_path = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        logger.info(f"Default cookie storage path: {default_path}")

        # Create custom storage directory (must be set before creating any WebEngineView)
        os.makedirs(self.browser_data_path, exist_ok=True)

        # Obtain the default profile and set the persistent storage path
        profile = QWebEngineProfile.defaultProfile()
        if profile is not None:
            profile.setPersistentStoragePath(self.browser_data_path)  # set custom path
            # Persistent cookie policy
            if hasattr(QWebEngineProfile, "PersistSessionCookies"):
                profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistSessionCookies) # type: ignore
            else:
                logger.warning("Warning: persistent cookie policy enum not found, skipping setting")

        logger.info(f"Custom cookie storage path: {self.browser_data_path}")
        
        self.browser = CustomWebEngineView()
        
        # Create a custom page and assign it to the browser
        self.custom_page = CustomWebEnginePage(self.browser)
        self.browser.setPage(self.custom_page)
        
        # Enable required settings
        self.enable_web_settings()
        
        # Wire up signals for URL change and load finished
        self.browser.urlChanged.connect(self.on_url_changed)
        self.browser.loadFinished.connect(self.on_load_finished)

        # Only set HTML content if provided (for backwards compatibility)
        if html_content is not None:
            self.browser.setHtml(html_content, QUrl("https://localhost/"))
        
        self.setCentralWidget(self.browser)

        # DevTools window reference to prevent it from being garbage-collected
        self._devtools = None
        # F12 shortcut to toggle developer tools (best-effort)
        try:
            shortcut = QShortcut(QKeySequence("F12"), self)
            shortcut.activated.connect(self._toggle_devtools)
            self._devtools_shortcut = shortcut
        except Exception:
            logger.warning("Note: unable to create F12 shortcut (QShortcut unsupported in this environment)")
    
    def load_url(self, url: QUrl):
        """Load a URL in the browser"""
        logger.info(f"Loading URL: {url.toString()}")
        self.browser.load(url)

    def enable_web_settings(self):
        """
        Enable required web settings
        """

        settings = self.browser.settings()
        # Enable JavaScript
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True) # type: ignore
        # Allow JavaScript to open new windows
        settings.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, True) # type: ignore
        # Allow JavaScript to access the clipboard
        settings.setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, True) # type: ignore
        # Enable local storage
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True) # type: ignore
        # Enable plugins
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True) # type: ignore
        # Try to enable developer tools (attribute name varies between PyQt5 versions)
        if hasattr(QWebEngineSettings, "DeveloperExtrasEnabled"):
            settings.setAttribute(QWebEngineSettings.DeveloperExtrasEnabled, True) # type: ignore
        elif hasattr(QWebEngineSettings, "WebAttribute") and hasattr(QWebEngineSettings.WebAttribute, "DeveloperExtrasEnabled"):
            settings.setAttribute(QWebEngineSettings.WebAttribute.DeveloperExtrasEnabled, True) # type: ignore
        else:
            logger.warning("Current PyQt5 version does not support DeveloperExtrasEnabled setting, skipping")
    
    def on_url_changed(self, url):
        """
        Handle URL changes
        """

        logger.info(f"URL changed: {url.toString()}")
        self.setWindowTitle(f"{self.title} - {url.toString()}")
    
    def on_load_finished(self, success):
        """
        Handle page load finished
        """

        if success:
            logger.info("Page loaded successfully")
        else:
            logger.warning("Page load failed")

    def _open_devtools(self):
        """
        Open a standalone DevTools window if supported by the platform
        """

        page = self.browser.page()
        if page is None:
            logger.warning("Notice: current page is not available, cannot open DevTools")
            return

        # If QWebEnginePage supports setDevToolsPage, use built-in DevTools support
        # Prefer opening DevTools in a dock widget when supported
        if hasattr(page, "setDevToolsPage"):
            try:
                dev = QWebEngineView()
                dev.setWindowTitle("DevTools")
                dev.resize(900, 700)
                    # Register the devtools page
                page.setDevToolsPage(dev.page())
                # Embed devtools as a dock widget
                if self._devtools is not None and isinstance(self._devtools, QDockWidget):
                    try:
                        self.removeDockWidget(self._devtools)
                    except Exception:
                        pass
                dock = QDockWidget("DevTools", self)
                dock.setWidget(dev)
                dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea) # type: ignore
                self.addDockWidget(Qt.BottomDockWidgetArea, dock) # type: ignore
                dock.show()
                self._devtools = dock
                return
            except Exception:
                # Continue trying alternative methods
                pass

        # Fallback: trigger InspectElement action (some Qt versions open DevTools)
        try:
            act = page.action(QWebEnginePage.WebAction.InspectElement)
            if act is not None:
                act.trigger()
                return
        except Exception:
            pass

        logger.error("Unable to open DevTools: current Qt/PyQt version does not support DevTools API")

    def _toggle_devtools(self):
        """Toggle DevTools window visibility"""
        if self._devtools is not None and hasattr(self._devtools, "isVisible") and self._devtools.isVisible():
            try:
                self._devtools.close()
            except Exception:
                pass
            self._devtools = None
            return
        # Otherwise open DevTools
        self._open_devtools()

def qt_message_handler(mode, context, message):
    qlogger = get_logger("qt")
    try:
        if mode == QtMsgType.QtDebugMsg or mode == QtMsgType.QtInfoMsg:
            qlogger.info(str(message))
        elif mode == QtMsgType.QtWarningMsg or mode == QtMsgType.QtCriticalMsg:
            qlogger.error(str(message))
        elif mode == QtMsgType.QtFatalMsg:
            # use fault if available
            if hasattr(qlogger, "fault"):
                qlogger.fault(str(message)) # type: ignore
            else:
                qlogger.error(str(message))
        else:
            qlogger.info(str(message))
    except Exception:
        try:
            qlogger.error(str(message))
        except Exception:
            pass

def install_qt_handler():
    try:
        qInstallMessageHandler(qt_message_handler)
        return True
    except Exception:
        # qInstallMessageHandler might not be available in some builds
        return False
