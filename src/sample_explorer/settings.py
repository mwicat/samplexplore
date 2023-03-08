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
        name = QFileDialog.getExistingDirectory(None, 'Select directory')
        if name:
            self.lineedit.setText(name)

    def text(self):
        return self.lineedit.text()


class SettingsDialog(QDialog):

    samplesDirChanged = Signal(str)

    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent=parent)

        self.samples_directory = None
        self.read_settings()

        self.setWindowTitle("Settings")
        self.setWindowIcon(QIcon(":settings.svg"))

        self.formlayout = layout = QFormLayout(self)

        self.select_directory_widget = SelectDirectoryWidget(self.samples_directory)
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

        if samples_directory != self.samples_directory:
            self.samples_directory = samples_directory
            self.samplesDirChanged.emit(self.samples_directory)

        self.write_settings()

        return super(SettingsDialog, self).accept()

    def write_settings(self):
        settings = QSettings("mwicat", "samplexplore")
        settings.beginGroup("Settings")

        settings.setValue("samples_directory", self.samples_directory)

        settings.endGroup()

    def read_settings(self):
        settings = QSettings("mwicat", "samplexplore")
        settings.beginGroup("Settings")

        self.samples_directory = settings.value("samples_directory")

        settings.endGroup()
