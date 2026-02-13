from PyQt5.QtCore import qInstallMessageHandler, QtMsgType
from PyQt5.QtCore import QUrl, QStandardPaths, Qt
from PyQt5.QtWidgets import (
    QMainWindow, QShortcut, QDockWidget, QAction,
    QFileDialog, QToolBar, QLabel, QPushButton,
    QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QFrame,
    QApplication
)
from PyQt5.QtGui import QKeySequence, QIcon, QFont
from PyQt5.QtWebEngineWidgets import (
    QWebEngineView, QWebEngineProfile, QWebEnginePage,
    QWebEngineSettings, QWebEngineDownloadItem
)
from PyQt5.QtGui import QDesktopServices

from logger import get_logger, init_logging

import os


log_file = init_logging()
logger = get_logger("custom_qt")


class DownloadItemWidget(QFrame):
    """
    Modern download item widget with flat design, rounded corners and icons.
    """
    def __init__(self, download_item: QWebEngineDownloadItem, parent=None):
        super().__init__(parent)
        self.download = download_item

        # Remove frame border (we'll use stylesheet for card effect)
        self.setFrameStyle(QFrame.NoFrame)
        self.setObjectName("downloadItem")

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Top row: filename and cancel button
        top_layout = QHBoxLayout()
        self.filename_label = QLabel(os.path.basename(download_item.path()))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.filename_label.setFont(font)
        top_layout.addWidget(self.filename_label)

        self.cancel_button = QPushButton()
        # Use standard icon if available
        icon = QApplication.style().standardIcon(QApplication.style().SP_DialogCancelButton)
        self.cancel_button.setIcon(icon)
        self.cancel_button.setToolTip("Cancel download")
        self.cancel_button.setFlat(True)
        self.cancel_button.setCursor(Qt.PointingHandCursor)
        self.cancel_button.clicked.connect(self.cancel_download)
        top_layout.addWidget(self.cancel_button)
        layout.addLayout(top_layout)

        # Progress bar (modern style via stylesheet)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Downloading...")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

        # Bottom row: Open file / Open folder buttons (initially hidden)
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        self.open_file_btn = QPushButton("Open File")
        self.open_file_btn.setIcon(QApplication.style().standardIcon(QApplication.style().SP_FileIcon))
        self.open_file_btn.setCursor(Qt.PointingHandCursor)
        self.open_file_btn.clicked.connect(self.open_file)

        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.setIcon(QApplication.style().standardIcon(QApplication.style().SP_DirIcon))
        self.open_folder_btn.setCursor(Qt.PointingHandCursor)
        self.open_folder_btn.clicked.connect(self.open_folder)

        bottom_layout.addWidget(self.open_file_btn)
        bottom_layout.addWidget(self.open_folder_btn)
        bottom_layout.addStretch()
        layout.addLayout(bottom_layout)

        # Initially hide open buttons
        self.open_file_btn.hide()
        self.open_folder_btn.hide()

        # Connect download signals
        self.download.downloadProgress.connect(self.update_progress)
        self.download.finished.connect(self.on_finished)

        # Apply modern stylesheet
        self.setStyleSheet("""
            #downloadItem {
                background-color: #f9f9f9;
                border-radius: 8px;
                margin: 4px;
                padding: 0px;
            }
            #downloadItem:hover {
                background-color: #f0f0f0;
            }
            QProgressBar {
                border: none;
                background-color: #e0e0e0;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #2a82da;
                border-radius: 3px;
            }
            #statusLabel {
                color: #666;
                font-size: 9pt;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)

    def update_progress(self, bytes_received, bytes_total):
        """Update progress bar and status."""
        if bytes_total > 0:
            progress = int(bytes_received / bytes_total * 100)
            self.progress_bar.setValue(progress)
            self.status_label.setText(f"Downloading… {progress}%")
        else:
            self.status_label.setText(f"Downloaded {bytes_received} bytes…")

    def on_finished(self):
        """Handle download finished."""
        if self.download.state() == QWebEngineDownloadItem.DownloadCompleted:
            self.progress_bar.setValue(100)
            self.status_label.setText("Completed")
            self.cancel_button.hide()
            self.open_file_btn.show()
            self.open_folder_btn.show()
        else:
            self.status_label.setText("Failed / Cancelled")
            self.cancel_button.setText("Retry")
            self.cancel_button.setIcon(QApplication.style().standardIcon(QApplication.style().SP_BrowserReload))
            self.cancel_button.clicked.disconnect()
            self.cancel_button.clicked.connect(self.retry_download)

    def cancel_download(self):
        """Cancel the download."""
        self.download.cancel()

    def retry_download(self):
        """Retry a failed download (placeholder)."""
        self.download.cancel()
        self.status_label.setText("Retry not implemented")

    def open_file(self):
        """Open the downloaded file."""
        if os.path.exists(self.download.path()):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.download.path()))

    def open_folder(self):
        """Open the folder containing the downloaded file."""
        folder = os.path.dirname(self.download.path())
        if os.path.exists(folder):
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))


class DownloadManager(QDockWidget):
    """
    Modern download manager with clean, card-based layout.
    """
    def __init__(self, parent=None):
        super().__init__("Downloads", parent)
        self.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)

        # Central widget with layout
        self.central_widget = QWidget()
        self.setWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(8)

        # Title bar with clear button
        title_layout = QHBoxLayout()
        title_label = QLabel("Downloads")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)

        self.clear_button = QPushButton("Clear Completed")
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.clicked.connect(self.clear_completed)
        title_layout.addStretch()
        title_layout.addWidget(self.clear_button)
        self.layout.addLayout(title_layout)

        # Scroll area for download items
        from PyQt5.QtWidgets import QScrollArea
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(4)
        self.items_layout.addStretch()

        self.scroll.setWidget(self.items_container)
        self.layout.addWidget(self.scroll)

        # List of download item widgets
        self.items = []  # (download_item, widget)

        # Apply modern stylesheet to the dock
        self.setStyleSheet("""
            QDockWidget {
                font-size: 10pt;
            }
            QDockWidget::title {
                background-color: #f0f0f0;
                padding: 4px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QPushButton {
                background-color: transparent;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)

    def add_download(self, download_item: QWebEngineDownloadItem):
        """Add a new download to the manager."""
        # Create widget
        item_widget = DownloadItemWidget(download_item)
        self.items.append((download_item, item_widget))

        # Insert before stretch
        self.items_layout.insertWidget(self.items_layout.count() - 1, item_widget)

        # Ensure the dock is visible
        self.show()
        self.raise_()

        # Optionally scroll to bottom to show new item
        self.scroll.ensureWidgetVisible(item_widget)

    def remove_download(self, download_item):
        """Remove a download widget from the manager."""
        for i, (d, w) in enumerate(self.items):
            if d == download_item:
                w.deleteLater()
                del self.items[i]
                break

    def clear_completed(self):
        """Remove all completed downloads from the list."""
        to_remove = []
        for d, w in self.items:
            if d.state() == QWebEngineDownloadItem.DownloadCompleted:
                to_remove.append((d, w))
        for d, w in to_remove:
            w.deleteLater()
            self.items.remove((d, w))

    def closeEvent(self, event):
        """Override close to just hide instead of destroying."""
        self.hide()
        event.ignore()


# 以下为 CustomWebEnginePage, CustomWebEngineView, Window 等类，与之前版本相同，
# 但已包含上述现代化下载管理器。为完整起见，保留所有代码。

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

        # --- Create top toolbar ---
        self.toolbar = QToolBar("Main Toolbar")
        self.addToolBar(self.toolbar)

        # Download button
        self.download_btn = QAction(QIcon(), "Downloads", self)
        self.download_btn.setToolTip("Show Downloads")
        self.download_btn.triggered.connect(self.toggle_download_manager)
        self.toolbar.addAction(self.download_btn)

        # Download count label (optional)
        self.download_count_label = QLabel("0")
        self.toolbar.addWidget(self.download_count_label)

        # --- Download Manager (initially hidden) ---
        self.download_manager = DownloadManager(self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.download_manager)
        self.download_manager.hide()  # start hidden

        # Keep track of active downloads count
        self.active_downloads = 0

        # --- Browser setup (existing code) ---
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

            # Connect download signal
            profile.downloadRequested.connect(self.handle_download)

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

    def toggle_download_manager(self):
        """Show or hide the download manager dock."""
        if self.download_manager.isVisible():
            self.download_manager.hide()
        else:
            self.download_manager.show()
            self.download_manager.raise_()

    def handle_download(self, download):
        """
        Handle download requests from the web engine.
        """
        # Suggest a default download location (system's download folder)
        default_download_dir = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        suggested_filename = download.suggestedFileName()
        if not suggested_filename:
            suggested_filename = "download"

        # Ask user where to save the file
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File",
            os.path.join(default_download_dir, suggested_filename)
        )
        if not file_path:
            download.cancel()
            logger.info("Download cancelled by user.")
            return

        # Set the full destination path and accept the download
        download.setPath(file_path)
        download.accept()
        logger.info(f"Download started: {file_path}")

        # Add to download manager
        self.download_manager.add_download(download)

        # Update download count
        self.active_downloads += 1
        self.download_count_label.setText(str(self.active_downloads))

        # When download finishes, decrease count
        def on_finished():
            self.active_downloads -= 1
            self.download_count_label.setText(str(self.active_downloads))
        download.finished.connect(on_finished)

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