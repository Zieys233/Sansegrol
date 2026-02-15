from PySide6.QtCore import qInstallMessageHandler, QtMsgType
from PySide6.QtCore import QUrl, QStandardPaths, Qt
from PySide6.QtWidgets import (
    QMainWindow, QDockWidget,
    QFileDialog, QToolBar, QLabel, QPushButton,
    QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QFrame,
    QApplication, QStyle, QLineEdit, QTabWidget
)
from PySide6.QtGui import QAction, QShortcut, QKeySequence, QIcon, QFont, QDesktopServices
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import (
    QWebEngineProfile,
    QWebEnginePage,
    QWebEngineSettings,
    QWebEngineDownloadRequest
)

from logger import get_logger, init_logging

import os

log_file = init_logging()
logger = get_logger("custom_qt")


class DownloadItemWidget(QFrame):
    """
    Modern download item widget with flat design, rounded corners and icons.
    """
    def __init__(self, download_item: QWebEngineDownloadRequest, parent=None):
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
        if self.download.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
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
        from PySide6.QtWidgets import QScrollArea
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

    def add_download(self, download_item: QWebEngineDownloadRequest):
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
            if d.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
                to_remove.append((d, w))
        for d, w in to_remove:
            w.deleteLater()
            self.items.remove((d, w))

    def closeEvent(self, event):
        """Override close to just hide instead of destroying."""
        self.hide()
        event.ignore()


class CustomWebEnginePage(QWebEnginePage):
    """
    Custom WebEngine page to handle link navigation, capture JavaScript console messages,
    and manage HTML5 permissions.
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

    def featurePermissionRequested(self, securityOrigin, feature):
        """
        Handle permission requests for HTML5 features (geolocation, notifications, media, etc.)
        """
        # Define which permissions to grant automatically
        allowed_features = []
        # Use hasattr to ensure compatibility with older Qt versions
        if hasattr(QWebEnginePage, 'Geolocation'):
            allowed_features.append(QWebEnginePage.Geolocation)
        if hasattr(QWebEnginePage, 'Notifications'):
            allowed_features.append(QWebEnginePage.Notifications)
        if hasattr(QWebEnginePage, 'MediaAudioCapture'):
            allowed_features.append(QWebEnginePage.MediaAudioCapture)
        if hasattr(QWebEnginePage, 'MediaVideoCapture'):
            allowed_features.append(QWebEnginePage.MediaVideoCapture)
        if hasattr(QWebEnginePage, 'MediaAudioVideoCapture'):
            allowed_features.append(QWebEnginePage.MediaAudioVideoCapture)
        if hasattr(QWebEnginePage, 'DesktopVideoCapture'):
            allowed_features.append(QWebEnginePage.DesktopVideoCapture)
        if hasattr(QWebEnginePage, 'DesktopAudioVideoCapture'):
            allowed_features.append(QWebEnginePage.DesktopAudioVideoCapture)

        if feature in allowed_features:
            self.setFeaturePermission(securityOrigin, feature, QWebEnginePage.PermissionGrantedByUser)
        else:
            # Deny other permissions (or you could prompt user)
            self.setFeaturePermission(securityOrigin, feature, QWebEnginePage.PermissionDeniedByUser)

        self._js_logger.info(f"Permission requested: {feature} -> {'granted' if feature in allowed_features else 'denied'}")

    def createWindow(self, type):
        """
        Handle new window creation (e.g., target="_blank")
        Overridden to open new tabs instead of new windows.
        """
        # Try to get the main window and create a new tab
        view = self.parent()
        if view is not None and isinstance(view, QWebEngineView):
            main_window = view.window()
            if main_window is not None and hasattr(main_window, 'create_new_tab'):
                new_page = main_window.create_new_tab()
                if new_page is not None:
                    return new_page

        # Fallback to original behavior: open in a new native window
        new_view = QWebEngineView()
        new_page = CustomWebEnginePage(new_view)
        new_view.setPage(new_page)

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
                    parent._popup_windows = []  # type: ignore
                parent._popup_windows.append((new_window, new_view, new_page))  # type: ignore

        return new_page


class CustomWebEngineView(QWebEngineView):
    """
    Custom QWebEngineView that adds an "Inspect element" action to the context menu
    """

    def __init__(self, parent=None):
        super(CustomWebEngineView, self).__init__(parent)

    def contextMenuEvent(self, event):  # type: ignore
        # use page's standard context menu when available
        page = self.page()
        menu = None
        try:
            if page is not None and hasattr(page, "createStandardContextMenu"):
                menu = page.createStandardContextMenu()
        except Exception:
            menu = None
        if menu is None:
            from PySide6.QtWidgets import QMenu
            menu = QMenu(self)
        inspect_act = QAction("Inspect element", self)

        # Call the parent window's devtools open function and trigger the
        # InspectElement action on the page
        def on_inspect():
            parent = self.window()
            if hasattr(parent, "_open_devtools"):
                parent._open_devtools()  # type: ignore
            try:
                act = self.page().action(QWebEnginePage.WebAction.InspectElement)  # type: ignore
                if act is not None:
                    act.trigger()
            except Exception:
                pass

        inspect_act.triggered.connect(on_inspect)
        menu.addAction(inspect_act)
        menu.exec_(event.globalPos())


class Window(QMainWindow):
    def __init__(self, title: str, geometrys: tuple, browser_data_path: str, html_content: str = None, icon_path: str = ""):  # type: ignore
        super(Window, self).__init__()

        self.title = title
        self.geometrys = geometrys
        self.browser_data_path = browser_data_path
        self.icon_path = icon_path

        self.setWindowTitle(title)
        self.setGeometry(self.geometrys[0], self.geometrys[1], self.geometrys[2], self.geometrys[3])

        if self.icon_path:
            self.setWindowIcon(QIcon(self.icon_path))

        self.toolbar = QToolBar("Main Toolbar")
        self.addToolBar(self.toolbar)

        # Donwload manager
        self.download_btn = QAction(QIcon(), "Downloads", self)
        self.download_btn.setToolTip("Show Downloads")
        self.download_btn.triggered.connect(self.toggle_download_manager)
        self.toolbar.addAction(self.download_btn)

        self.download_count_label = QLabel("0")
        self.toolbar.addWidget(self.download_count_label)

        self.download_manager = DownloadManager(self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.download_manager)
        self.download_manager.hide()

        self.active_downloads = 0

        # Browser settings
        default_path = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        logger.info(f"Default cookie storage path: {default_path}")

        os.makedirs(self.browser_data_path, exist_ok=True)

        profile = QWebEngineProfile.defaultProfile()
        if profile is not None:
            profile.setPersistentStoragePath(self.browser_data_path)

            # Set persistent cookie policy.
            if hasattr(profile, 'setPersistentCookiesPolicy'):
                policy = None
                if hasattr(QWebEngineProfile, 'PersistentSessionCookies'):
                    policy = QWebEngineProfile.PersistentSessionCookies
                elif hasattr(QWebEngineProfile, 'PersistentCookiesPolicy'):
                    policy_enum = QWebEngineProfile.PersistentCookiesPolicy
                    if hasattr(policy_enum, 'PersistentSessionCookies'):
                        policy = policy_enum.PersistentSessionCookies
                if policy is not None:
                    profile.setPersistentCookiesPolicy(policy)
                else:
                    logger.warning("Could not find PersistentSessionCookies policy, using default")
                    try:
                        profile.setPersistentCookiesPolicy(1)
                    except TypeError:
                        logger.error("Failed to set persistent cookies policy")
            else:
                logger.warning("setPersistentCookiesPolicy not available, using default policy")

            # Autoplay Policy
            if hasattr(profile, 'setAttribute'):
                autoplay_policy_attr = None
                autoplay_policy_value = None
                if hasattr(QWebEngineProfile, 'AutoplayPolicy'):
                    autoplay_policy_attr = QWebEngineProfile.AutoplayPolicy
                if hasattr(QWebEngineProfile, 'AutoplayAllow'):
                    autoplay_policy_value = QWebEngineProfile.AutoplayAllow
                elif hasattr(QWebEngineProfile, 'AutoplayPolicy'):
                    try:
                        autoplay_policy_value = QWebEngineProfile.AutoplayPolicy.AutoplayAllow
                    except AttributeError:
                        pass

                if autoplay_policy_attr is not None and autoplay_policy_value is not None:
                    try:
                        profile.setAttribute(autoplay_policy_attr, autoplay_policy_value)
                    except Exception as e:
                        logger.warning(f"Failed to set autoplay policy: {e}")

            modern_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
            profile.setHttpUserAgent(modern_ua)
            profile.downloadRequested.connect(self.handle_download)

        logger.info(f"Custom cookie storage path: {self.browser_data_path}")

        # Create tab control.
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.on_current_tab_changed)
        self.setCentralWidget(self.tab_widget)

        self.add_new_tab(None)

        # Toolbar navigation buttons (act on current tab)
        back_btn = QAction(self.style().standardIcon(QStyle.SP_ArrowBack), "", self)
        back_btn.triggered.connect(lambda: self.current_browser().back())
        self.toolbar.insertAction(self.download_btn, back_btn)

        forward_btn = QAction(self.style().standardIcon(QStyle.SP_ArrowForward), "", self)
        forward_btn.triggered.connect(lambda: self.current_browser().forward())
        self.toolbar.insertAction(self.download_btn, forward_btn)

        reload_btn = QAction(self.style().standardIcon(QStyle.SP_BrowserReload), "", self)
        reload_btn.triggered.connect(lambda: self.current_browser().reload())
        self.toolbar.insertAction(self.download_btn, reload_btn)

        # Address bar input field
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL or search...")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.toolbar.insertWidget(self.download_btn, self.url_bar)

        if html_content is not None:
            self.current_browser().setHtml(html_content, QUrl("https://localhost/"))

        # Developer tools shortcut
        self._devtools = None
        try:
            shortcut = QShortcut(QKeySequence("F12"), self)
            shortcut.activated.connect(self._toggle_devtools)
            self._devtools_shortcut = shortcut
        except Exception:
            logger.warning("Note: unable to create F12 shortcut")

    def add_new_tab(self, url: QUrl):
        """Create a new tab, optionally loading a specified URL."""
        browser = CustomWebEngineView()
        custom_page = CustomWebEnginePage(browser)
        browser.setPage(custom_page)
        self.enable_web_settings(browser)

        browser.urlChanged.connect(self.on_browser_url_changed)
        browser.titleChanged.connect(self.on_browser_title_changed)
        browser.loadFinished.connect(self.on_browser_load_finished)

        index = self.tab_widget.addTab(browser, "New Page")
        self.tab_widget.setCurrentIndex(index)

        if url is not None and not url.isEmpty():
            browser.load(url)

        return browser

    def create_new_tab(self) -> CustomWebEnginePage:
        """Method called by `CustomWebEnginePage.createWindow`: creates a new tab and returns its page."""
        browser = self.add_new_tab()
        return browser.page()

    def current_browser(self) -> CustomWebEngineView:
        """Get the current active browser widget (current tab)."""
        return self.tab_widget.currentWidget()

    def close_tab(self, index: int):
        """Close the tab at the specified index, ensuring proper cleanup of the browser widget."""
        widget = self.tab_widget.widget(index)
        self.tab_widget.removeTab(index)
        widget.deleteLater()

        # If no tabs remain, add a new blank tab to prevent the UI from being empty
        if self.tab_widget.count() == 0:
            self.add_new_tab()

    def on_current_tab_changed(self, index: int):
        """When the user switches tabs, update the URL bar and window title to reflect the new active tab's URL."""
        browser = self.tab_widget.widget(index)
        if browser:
            url = browser.url()
            self.url_bar.setText(url.toString())
            self.setWindowTitle(f"{self.title} - {url.toString()}")

    def on_browser_url_changed(self, url: QUrl):
        """Update the address bar and window title when the browser URL changes (only if it is the currently active tab)."""
        browser = self.sender()
        if browser == self.current_browser():
            self.url_bar.setText(url.toString())
            self.setWindowTitle(f"{self.title} - {url.toString()}")
        logger.info(f"URL changed: {url.toString()}")

    def on_browser_title_changed(self, title: str):
        """Update tab title."""
        browser = self.sender()
        index = self.tab_widget.indexOf(browser)
        if index != -1:
            self.tab_widget.setTabText(index, title)

    def on_browser_load_finished(self, success: bool):
        """Log page load success or failure for the current tab."""
        browser = self.sender()
        if browser == self.current_browser():
            if success:
                logger.info("Page loaded successfully")
            else:
                logger.warning("Page load failed")

    def navigate_to_url(self):
        """When the user presses Enter in the address bar, navigate to the URL or search query."""
        text = self.url_bar.text().strip()
        if text:
            url = QUrl.fromUserInput(text)
            self.current_browser().load(url)

    def load_url(self, url: QUrl):
        """Programmatically load a URL in the current tab, with logging."""
        logger.info(f"Loading URL: {url.toString()}")
        self.current_browser().load(url)

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

    def enable_web_settings(self, browser: CustomWebEngineView):
        """
        Enable required web settings for full HTML5 support on a specific browser.
        """
        settings = browser.settings()

        # Basic settings
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, True)
        settings.setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, True)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)

        # Fullscreen support (for video, etc.)
        if hasattr(QWebEngineSettings, 'FullScreenSupportEnabled'):
            settings.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)

        # WebGL and hardware acceleration
        if hasattr(QWebEngineSettings, 'WebGLEnabled'):
            settings.setAttribute(QWebEngineSettings.WebGLEnabled, True)
            
        if hasattr(QWebEngineSettings, 'Accelerated2dCanvasEnabled'):
            settings.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)

        # Auto-load images (usually on by default)
        if hasattr(QWebEngineSettings, 'AutoLoadImages'):
            settings.setAttribute(QWebEngineSettings.AutoLoadImages, True)

        # Allow autoplay without user gesture (if supported)
        if hasattr(QWebEngineSettings, 'PlaybackRequiresUserGesture'):
            settings.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)
        
        # Developer tools (for debugging)
        if hasattr(QWebEngineSettings, 'DeveloperExtrasEnabled'):
            settings.setAttribute(QWebEngineSettings.DeveloperExtrasEnabled, True)
        elif hasattr(QWebEngineSettings, 'WebAttribute') and hasattr(QWebEngineSettings.WebAttribute, 'DeveloperExtrasEnabled'):
            settings.setAttribute(QWebEngineSettings.WebAttribute.DeveloperExtrasEnabled, True)
        else:
            logger.warning("Current PySide6 version does not support DeveloperExtrasEnabled setting, skipping")

        # Enable media features if available (for HTML5 audio/video)
        if hasattr(QWebEngineSettings, 'MediaEnabled'):
            settings.setAttribute(QWebEngineSettings.MediaEnabled, True)

        # Security settings - disable mixed content (if supported)
        if hasattr(QWebEngineSettings, 'AllowRunningInsecureContent'):
            settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, False)

        # Disable features that may cause issues or are not needed
        if hasattr(QWebEngineSettings, 'HyperlinkAuditingEnabled'):
            settings.setAttribute(QWebEngineSettings.HyperlinkAuditingEnabled, False)

        # Disable scroll animator for smoother scrolling (if supported)
        if hasattr(QWebEngineSettings, 'ScrollAnimatorEnabled'):
            settings.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, False)

        # Enable media source extensions for advanced media streaming (if supported)
        if hasattr(QWebEngineSettings, 'MediaSourceEnabled'):
            settings.setAttribute(QWebEngineSettings.MediaSourceEnabled, True)

        # Hide scrollbars for a cleaner look (optional, may cause issues on some sites)
        if hasattr(QWebEngineSettings, 'HideScrollbars'):
            settings.setAttribute(QWebEngineSettings.HideScrollbars, True)

        # Enable encrypted media extensions for DRM-protected content (if supported)
        if hasattr(QWebEngineSettings, 'EncryptedMediaEnabled'):
            settings.setAttribute(QWebEngineSettings.EncryptedMediaEnabled, True)

    def _open_devtools(self):
        """
        Open a standalone DevTools window if supported by the platform
        """
        browser = self.current_browser()
        if not browser:
            return
        page = browser.page()
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
                dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)  # type: ignore
                self.addDockWidget(Qt.BottomDockWidgetArea, dock)  # type: ignore
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

        logger.error("Unable to open DevTools: current Qt/PySide version does not support DevTools API")

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
                qlogger.fault(str(message))  # type: ignore
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