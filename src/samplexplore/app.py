import os
import math
import sys
import pathlib

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *
from qtpy.QtMultimedia import QMediaContent, QMediaPlaylist, QMediaPlayer

from pyqtconsole.console import PythonConsole

from .db_manager import DBManager

from . import mediautils
from . import fileutils
from .media_slider import MediaSlider
from . import rc_icons
from .settings import SettingsManager


SUPPORTED_EXTENSIONS = [
    'wav',
    'aif',
    'mp3',
    'flac',
]
8
PREVIEW_PLAY_LOCK_TIME = 200

WEBSITE_URL = 'https://github.com/mwicat/sample_explorer'

DB_PATH = '/tmp/samplesbdb.sqlite'


INITIAL_SIZE = 1000, 600


class SearchResultItemModel(QStandardItemModel):

    def mimeTypes(self):
        return ["text/uri-list"]

    def mimeData( self, indexes):
        mimedata = QMimeData()
        urls = []
        for index in indexes:
            row = index.row()
            full_path = index.sibling(row, 1).data()
            urls.append(QUrl.fromLocalFile(full_path))
        mimedata.setUrls(urls)
        return mimedata


class RenderTypeProxyModel(QSortFilterProxyModel):
    def __init__(self):
        super(RenderTypeProxyModel, self).__init__()

    def filterAcceptsRow(self, row, parent):
        fsmodel = self.sourceModel()

        index = fsmodel.index(row, 3, parent)
        finfo = fsmodel.fileInfo(index)

        if not finfo.isDir():
            fn_base, fn_ext = os.path.splitext(finfo.fileName())
            if fn_ext:
                fn_ext = fn_ext[1:].lower()
                return fn_ext in SUPPORTED_EXTENSIONS
            return False

        return True

    def lessThan(self, left, right):
        fsmodel = self.sourceModel()

        info_left = fsmodel.fileInfo(left)
        info_right = fsmodel.fileInfo(right)

        if fsmodel.data(left) == "..":
            return True

        if fsmodel.data(right) == "..":
            return False

        if not info_left.isDir() and info_right.isDir():
            return False

        if info_left.isDir() and not info_right.isDir():
            return True

        return super(RenderTypeProxyModel, self).lessThan(left, right)


class Browser(QMainWindow):
    def __init__(self, settings_manager, parent=None, console=None, app=None):
        super(Browser, self).__init__(parent=parent)

        self.settings_manager = settings_manager
        self.settings_manager.samplesDirChanged.connect(self.on_samples_directory_changed)

        #self.set_samples_directory(self.settings_manager.samples_directory)

        self.play_locked = False
        self.search_phrase = None

        self.console = console
        self.app = app

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        self.setWindowIcon(QIcon(':headphones.svg'))

        self._createActions()
        self._createMenuBar()
        self._createToolBars()

        self.db_manager = DBManager()
        self.db_manager.connect(DB_PATH)

        self.resize(*INITIAL_SIZE)
        self.setWindowTitle('Sample browser')

        self.fsmodel = QFileSystemModel()

        self.mediaPlayer = QMediaPlayer()
        self.mediaPlayer.positionChanged.connect(self.media_position_changed)
        self.mediaPlayer.durationChanged.connect(self.media_duration_changed)
        self.mediaPlayer.stateChanged.connect(self.media_state_changed)
        self.mediaPlayer.durationChanged.connect(self.media_duration_changed)
        self.mediaPlayer.mediaChanged.connect(self.media_changed)

        self.mediaPlaylist = QMediaPlaylist()
        self.mediaPlayer.setPlaylist(self.mediaPlaylist)

        self.proxyModel = RenderTypeProxyModel()
        self.proxyModel.setSourceModel(self.fsmodel)

        self.proxyModel.sort(0)

        self.file_view = QColumnView()
        self.file_view.setModel(self.proxyModel)

        self.file_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.file_view.setDragDropMode(QAbstractItemView.DragOnly)
        self.file_view.setDragEnabled(True)
        self.file_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_view.customContextMenuRequested.connect(self.open_file_menu)

        self.file_view.clicked.connect(self.on_file_view_clicked)

        selection_model = self.file_view.selectionModel()

        selection_model.selectionChanged.connect(self.on_files_selected)

        self.media_slider = MediaSlider(Qt.Horizontal)
        self.media_slider.setRange(0, 0)
        self.media_slider.sliderMoved.connect(self.set_media_position)

        self.media_pane = QHBoxLayout()
        self.media_pane.setContentsMargins(0, 0, 0, 0)

        self.playBtn = QPushButton()
        self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playBtn.clicked.connect(self.on_play_clicked)

        self.media_pane.addWidget(self.playBtn)

        self.stopBtn = QPushButton()
        self.stopBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stopBtn.clicked.connect(self.on_stop_clicked)

        self.media_pane.addWidget(self.stopBtn)

        self.loopBtn = QPushButton()
        self.loopBtn.setCheckable(True)
        self.loopBtn.setIcon(QIcon(":repeat.svg"))
        self.loopBtn.toggled.connect(self.on_loop_toggled)

        self.media_pane.addWidget(self.loopBtn)

        self.positionLabel = QLabel('--:--')
        self.media_pane.addWidget(self.positionLabel)

        self.media_pane.addWidget(self.media_slider)

        self.durationLabel = QLabel('--:--')
        self.media_pane.addWidget(self.durationLabel)

        grid = QGridLayout()

        self.searchTypeTimer = QTimer(self)
        self.searchTypeTimer.timeout.connect(self.perform_search)
        self.searchTypeTimer.setSingleShot(True)

        self.search_view = QVBoxLayout()

        self.searchEdit = QLineEdit()
        self.searchEdit.setPlaceholderText("Search...")
        self.searchEdit.textChanged.connect(self.on_search_input)
        self.searchEdit.setMaximumWidth(250);

        self.shortcut_search = QShortcut(QKeySequence('Ctrl+F'), self)
        self.shortcut_search.activated.connect(self.search_shortcut_activated)

        self.shortcut_exit = QShortcut(QKeySequence('Ctrl+Q'), self)
        self.shortcut_exit.activated.connect(self.app.quit)

        self.shortcut_loop = QShortcut(QKeySequence('Ctrl+L'), self)
        self.shortcut_loop.activated.connect(self.on_loop_shortcut)

        self.search_view.addWidget(self.searchEdit)

        self.searchResultList = QListView()
        self.searchResultList.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.searchResultModel = SearchResultItemModel()

        self.searchResultList.setModelColumn(1)
        self.searchResultList.setModel(self.searchResultModel)
        self.searchResultList.clicked.connect(self.search_result_clicked)
        self.searchResultList.selectionModel().selectionChanged.connect(self.search_result_selected)
        self.searchResultList.setSelectionMode(QAbstractItemView.SingleSelection)

        self.searchResultList.setDragDropMode(QAbstractItemView.DragOnly)
        self.searchResultList.setDragEnabled(True)

        self.searchResultList.setMaximumWidth(250);
        self.searchEdit.setMaximumWidth(250);

        self.search_view.addWidget(self.searchResultList)

        grid.addLayout(self.search_view, 0, 0, 1, 1)

        grid.addWidget(self.file_view, 0, 1, 1, 3)
        grid.addLayout(self.media_pane, 1, 0, 1, 4)

        self.main_panel = QWidget()
        self.main_panel.setLayout(grid)
        self.setCentralWidget(self.main_panel)

        if settings_manager.samples_directory is None:
            settings_manager.show_settings_dialog()
        else:
            self.set_samples_directory(settings_manager.samples_directory)

    def show_status(self, text):
        self.statusBar.showMessage(text)

    def on_samples_directory_changed(self, path):
        self.refresh_db()
        self.set_samples_directory(path)

    def refresh_db(self):
        self.show_status('Refreshing search database...')
        self.db_manager.rebuild_files_table(
            self.settings_manager.samples_directory,
            result_callback=self.on_search_db_refreshed)

    def on_search_db_refreshed(self):
        self.show_status('Completed refresh of search database!')
        self.perform_search()

    def set_samples_directory(self, path):
        print('set samples directory', path)
        self.fsmodel.setRootPath('/')
        og_index = self.fsmodel.index(path)
        root_index = self.proxyModel.mapFromSource(og_index)
        self.file_view.setRootIndex(root_index)

    def _createActions(self):
        self.settingsAction = QAction(QIcon(":settings.svg"), "Se&ttings", self)
        self.settingsAction.triggered.connect(self.open_settings)

        self.exitAction = QAction(QIcon(":times.svg"), "E&xit", self)
        self.exitAction.triggered.connect(self.app.quit)

        self.openConsoleAction = QAction(QIcon(":python.svg"), "&Python console", self)
        self.openConsoleAction.triggered.connect(self.open_console)

        self.openWebsiteAction = QAction(QIcon(":globe.svg"), "Open &website", self)
        self.openWebsiteAction.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(WEBSITE_URL)))

        self.refreshDbAction = QAction(QIcon(":arrows-round.svg"), "&Refresh search database", self)
        self.refreshDbAction.triggered.connect(self.refresh_db)

        self.toggleOnTop = QAction(QIcon(":note-sticky.svg"), "&Toggle always on top", self)
        self.toggleOnTop.triggered.connect(self.toggle_window_on_top)

    def open_settings(self):
        self.settings_manager.show_settings_dialog()

    def toggle_window_on_top(self):
        # self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        pass

    def open_console(self):
        self.console.show()

    def _createMenuBar(self):
        menuBar = self.menuBar()
        self.setMenuBar(menuBar)

        fileMenu = QMenu("&File", self)
        fileMenu.addAction(self.settingsAction)
        fileMenu.addAction(self.exitAction)
        menuBar.addMenu(fileMenu)

        toolsMenu = QMenu("&Tools", self)
        toolsMenu.addAction(self.openConsoleAction)
        menuBar.addMenu(toolsMenu)

        helpMenu = QMenu("&Help", self)
        helpMenu.addAction(self.openWebsiteAction)
        menuBar.addMenu(helpMenu)

    def _createToolBars(self):
        fileToolBar = self.addToolBar("File")
        fileToolBar.setMovable(False)

        fileToolBar.addAction(self.refreshDbAction)
        fileToolBar.addAction(self.settingsAction)
        # fileToolBar.addAction(self.toggleOnTop)

    def search_shortcut_activated(self):
        self.searchEdit.setFocus()
        self.searchEdit.selectAll()

    def search_result_clicked(self, index):
        row = index.row()

        fn = index.sibling(row, 0).data()
        full_path = index.sibling(row, 1).data()

        self.select_path(full_path)
        self.play_file(full_path)

    def search_result_selected(self, selection):
        indexes = selection.indexes()
        if not indexes:
            return
        index = indexes[0]
        row = index.row()

        fn = index.sibling(row, 0).data()
        full_path = index.sibling(row, 1).data()

        self.select_path(full_path)
        self.play_file(full_path)

    def on_search_results(self, results):
        for result in results:
            self.searchResultModel.appendRow([
                QStandardItem(result['filename']),
                QStandardItem(result['full_path']),
            ])

    def perform_search(self):
        self.searchResultModel.clear()

        if not self.search_phrase:
            return

        self.db_manager.search_file(
            self.search_phrase, result_callback=self.on_search_results)

    def on_search_input(self, search_phrase):
        self.search_phrase = search_phrase
        self.searchTypeTimer.start(500)

    def select_path(self, path):
        idx = self.fsmodel.index(path)
        file_view_idx = self.proxyModel.mapFromSource(idx)
        QTimer.singleShot(0, lambda: self.file_view.setCurrentIndex(file_view_idx))

    def on_play_clicked(self):
        if self.mediaPlayer.state() == QMediaPlayer.State.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()

    def on_stop_clicked(self):
        if self.mediaPlayer.state() != QMediaPlayer.State.StoppedState:
            self.mediaPlayer.stop()

    def on_loop_shortcut(self):
        self.loopBtn.toggle()

    def on_loop_toggled(self, checked):
        if checked:
            self.mediaPlaylist.setPlaybackMode(QMediaPlaylist.Loop)
            self.loopBtn.setIcon(QIcon(":repeat-on.svg"))
        else:
            self.mediaPlaylist.setPlaybackMode(QMediaPlaylist.CurrentItemOnce)
            self.loopBtn.setIcon(QIcon(":repeat.svg"))

    def media_state_changed(self, state: QMediaPlayer.State):
        if state == QMediaPlayer.State.PlayingState:
            self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def get_selected_fileinfo(self) -> QFileInfo:
        indexes = self.file_view.selectedIndexes()

        if not indexes:
            return
        index = self.file_view.selectedIndexes()[0]
        finfo = self.fsmodel.fileInfo(self.proxyModel.mapToSource(index))
        return finfo

    def on_file_view_clicked(self):
        finfo = self.get_selected_fileinfo()

        if finfo is None or finfo.isDir():
            return

        self.play_file(finfo.filePath())

    def on_files_selected(self, selected: QItemSelection, deselected: QItemSelection):
        indexes = selected.indexes()
        if not indexes:
            return
        index = indexes[0]
        full_path = self.fsmodel.filePath(self.proxyModel.mapToSource(index))
        finfo = self.fsmodel.fileInfo(self.proxyModel.mapToSource(index))

        if finfo.isDir():
            self.mediaPlayer.stop()
        else:
            self.play_file(full_path)

    def unlock_play(self):
        self.play_locked = False

    def play_file(self, path):
        if self.play_locked:
            return

        self.play_locked = True
        QTimer.singleShot(PREVIEW_PLAY_LOCK_TIME, self.unlock_play)

        self.mediaPlayer.stop()

        self.mediaPlaylist.clear()
        self.mediaPlaylist.addMedia(QMediaContent(QUrl.fromLocalFile(path)))

        self.mediaPlayer.play()

    def media_changed(self, media: QMediaContent):
        filepath = media.request().url().toLocalFile()
        self.statusBar.showMessage("{}".format(filepath))

    def media_position_changed(self, position):
        self.positionLabel.setText(mediautils.media_time_to_str(position))
        self.media_slider.setValue(position)

    def media_duration_changed(self, duration):
        self.durationLabel.setText(mediautils.media_time_to_str(duration))
        self.media_slider.setRange(0, duration)

    def set_media_position(self, position):
        self.mediaPlayer.setPosition(position)

    def open_file_menu(self, position):
        menu = QMenu()

        open_parent_action = menu.addAction("Show in file browser")
        open_action = menu.addAction("Open with default application")

        action = menu.exec_(self.file_view.mapToGlobal(position))
        finfo = self.get_selected_fileinfo()
        path = pathlib.Path(finfo.absoluteFilePath())

        if action == open_action:
            self.mediaPlayer.pause()
            fileutils.open_file(path)
        elif action == open_parent_action:
            fileutils.open_file_parent(path)


