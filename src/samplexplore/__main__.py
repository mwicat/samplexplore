import logging
import threading

from qtpy.QtCore import *
from qtpy.QtGui import *

from .app import *


log_proxy = None


def custom_excepthook(excType, excValue, traceback):
    logging.error("Logging an uncaught exception", exc_info=(excType, excValue, traceback))
    if log_proxy is not None:
        log_proxy.error.emit(excValue)

    sys.__excepthook__(excType, excValue, traceback)


def custom_threading_excepthook(args):
    custom_excepthook(args.exc_type, args.exc_value, args.exc_traceback)


sys.excepthook = custom_excepthook
threading.excepthook = custom_threading_excepthook


class LogProxy(QObject):

    log = Signal(str)
    error = Signal(str)


class QLogHandler(logging.Handler):

    def __init__(self, emitter):
        super().__init__()
        self._emitter = emitter

    @property
    def emitter(self):
        return self._emitter

    def emit(self, record):
        msg = self.format(record)
        self.emitter.log.emit(msg)


class LogViewDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setWindowTitle("Log viewer")

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.textedit = QPlainTextEdit()
        fm = self.textedit.fontMetrics()
        width = fm.width(" " * 150)
        height = fm.height() * 30
        self.textedit.setMinimumSize(width, height)

        self.layout.addWidget(self.textedit)
        self.setLayout(self.layout)

    def append_log(self, log):
        self.textedit.insertPlainText(log + '\n')


def main():
    app = QApplication(sys.argv)

    app.setOrganizationDomain("mwicat");
    app.setApplicationName("samplexplore");

    data_path = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
    data_path_dir = QDir(data_path)

    log_view_dlg = LogViewDialog()

    global log_proxy
    log_proxy = LogProxy()
    log_proxy.log.connect(log_view_dlg.append_log)
    log_proxy.error.connect(lambda: QMessageBox.critical(
        None, "Error occured", "An unexpected error occured. Check menu Help -> Log viewer for details"))

    if not data_path_dir.exists():
        data_path_dir.mkpath('.')

    log_path = data_path_dir.filePath("Log.txt")

    log_handlers = [
        logging.FileHandler(log_path, mode='w'),
        logging.StreamHandler(),
        QLogHandler(log_proxy),
    ]

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(message)s',
                        handlers=log_handlers)

    logging.info("Application started")

    console_locals = {}
    console_locals.update(locals())
    console_locals.update(globals())

    console = PythonConsole(locals=console_locals)
    console.eval_queued()

    settings_manager = SettingsManager()
    settings_manager.read_settings()

    browser = Browser(settings_manager, app=app, console=console, log_view_dlg=log_view_dlg)
    browser.show()

    console.interpreter.locals['browser'] = browser

    retcode = app.exec_()
    logging.info("Application finished")
    sys.exit(retcode)


if __name__ == '__main__':
    main()
