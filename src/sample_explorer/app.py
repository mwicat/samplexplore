import os
import sys

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer

SUPPORTED_EXTENSIONS = [
    'wav',
    'aif',
    'mp3',
]

INITIAL_SIZE = 800, 600


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


class Browser(QDialog):
    def __init__(self, parent=None):
        super(Browser, self).__init__(parent)

        self.resize(*INITIAL_SIZE)
        self.setWindowTitle('Sample browser')

        path = 'd:/produkcja/sample'
        self.fsmodel = QFileSystemModel()
        self.fsmodel.setRootPath('/')

        og_index = self.fsmodel.index(path)

        self.mediaPlayer = QMediaPlayer()
        self.mediaPlayer.positionChanged.connect(self.media_position_changed)
        self.mediaPlayer.durationChanged.connect(self.media_duration_changed)

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

        root_index = self.proxyModel.mapFromSource(og_index)
        self.file_view.setRootIndex(root_index)
        self.file_view.clicked.connect(self.on_files_selected)

        selection_model = self.file_view.selectionModel()

        selection_model.selectionChanged.connect(self.on_files_selected)

        self.media_slider = QSlider(Qt.Horizontal)
        self.media_slider.setRange(0, 0)
        self.media_slider.sliderMoved.connect(self.set_media_position)

        self.media_pane = QHBoxLayout()
        self.media_pane.setContentsMargins(0, 0, 0, 0)

        self.playBtn = QPushButton()
        self.playBtn.setEnabled(False)
        self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

        self.media_pane.addWidget(self.playBtn)
        self.media_pane.addWidget(self.media_slider)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)

        grid.addWidget(self.file_view, 0, 0)
        grid.addLayout(self.media_pane, 1, 0)

        self.setLayout(grid)

    def get_selected_fileinfo(self):
        index = self.file_view.selectedIndexes()[0]
        finfo = self.fsmodel.fileInfo(self.proxyModel.mapToSource(index))
        return finfo

    def on_files_selected(self, *args, **kwargs):
        finfo = self.get_selected_fileinfo()
        self.mediaPlayer.stop()

        if finfo.isDir():
            return

        media_path = finfo.filePath()
        self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(media_path)))
        self.mediaPlayer.play()

        self.playBtn.setEnabled(True)

    def media_position_changed(self, position):
        self.media_slider.setValue(position)

    def media_duration_changed(self, duration):
        self.media_slider.setRange(0, duration)

    def set_media_position(self, position):
        self.mediaPlayer.setPosition(position)

    def open_file_menu(self, position):
        menu = QMenu()
        open_action = menu.addAction("Open with system handler")
        action = menu.exec_(self.file_view.mapToGlobal(position))
        if action == open_action:
            finfo = self.get_selected_fileinfo()
            os.startfile(finfo.filePath(), 'open')


def main():
    app = QApplication(sys.argv)

    browser = Browser()
    browser.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
