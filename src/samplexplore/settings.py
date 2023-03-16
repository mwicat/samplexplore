import os

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


class SelectDirectoryWidget(QWidget):

    def __init__(self, value, parent=None):
        super(SelectDirectoryWidget, self).__init__()

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.valid = False

        self.value = value
        self.lineedit = QLineEdit(value if value is not None else '', parent)
        self.lineedit.textChanged.connect(self.validate)
        layout.addWidget(self.lineedit)

        self.filebtn = QPushButton('Browse')
        self.filebtn.clicked.connect(self.getfile)
        layout.addWidget(self.filebtn)

        self.setLayout(layout)
        self.validate(value)

    def validate(self, text):
        w = self.lineedit

        if not os.path.isdir(text):
            color = 'IndianRed'
            self.valid = False
        else:
            color = 'LightGreen'
            self.valid = True

        w.setAttribute(Qt.WA_StyledBackground, True)
        w.setStyleSheet('background-color: {};'.format(color))

    def getfile(self):
        name = QFileDialog.getExistingDirectory(self, 'Select directory', self.value)
        if name:
            self.lineedit.setText(name)

    def text(self):
        return self.lineedit.text()


class SettingsDialog(QDialog):

    def __init__(self, settings_manager, parent=None):
        super(SettingsDialog, self).__init__(parent=parent)

        self.settings_manager = settings_manager

        self.setWindowTitle("Settings")
        self.setWindowIcon(QIcon(":settings.svg"))

        self.formlayout = layout = QFormLayout(self)

        samples_dir = self.settings_manager.samples_directory

        self.select_directory_widget = SelectDirectoryWidget(
            samples_dir if samples_dir is not None else '')
        self.formlayout.addRow('Samples directory:',  self.select_directory_widget)

        self.bbox = bbox = QDialogButtonBox()
        self.bbox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)

        layout.addWidget(bbox)

        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)

        self.setLayout(layout)

    def accept(self):
        if not self.select_directory_widget.valid:
            QMessageBox.critical(self, "Invalid settings", "Samples directory location is invalid.")
            return

        samples_directory = self.select_directory_widget.text()

        self.settings_manager.samples_directory = samples_directory
        self.settings_manager.write_settings()

        return super(SettingsDialog, self).accept()


class SettingsManager(QObject):

    samplesDirChanged = Signal(str)

    def __init__(self, parent=None):
        super(SettingsManager, self).__init__(parent=parent)
        self._samples_directory = None

    @property
    def samples_directory(self):
        return self._samples_directory

    @samples_directory.setter
    def samples_directory(self, new_samples_directory):
        if new_samples_directory != self._samples_directory:
            self._samples_directory = new_samples_directory
            self.samplesDirChanged.emit(self._samples_directory)

    def write_settings(self):
        settings = QSettings()
        settings.beginGroup("Settings")

        settings.setValue("samples_directory", self._samples_directory)

        settings.endGroup()

    def read_settings(self):
        settings = QSettings("mwicat", "samplexplore")
        print('settings location', settings.fileName())

        settings.beginGroup("Settings")

        self._samples_directory = settings.value("samples_directory")

        settings.endGroup()

    def show_settings_dialog(self):
        settings_dialog = SettingsDialog(self)
        settings_dialog.exec_()
