from qtpy.QtCore import *
from qtpy.QtConcurrent import QtConcurrent

from .db import SampleDB


class DBManager(QObject):

    rebuild_status_updated = Signal(DBRebuildStatusInfo)
    rebuild_files_table_requested = Signal()

    def __init__(self):
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(1)
        self.threadpool.setExpiryTimeout(-1)

    def start_service(self):
        print('started service')
        self.db = SampleDB

    def rebuild_files_table(self):
        rebuild_files_table_requested.emit()
