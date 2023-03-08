from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Protocol

from playhouse.shortcuts import model_to_dict

from qtpy.QtCore import *

from . import db_core
from .db_core import DBRebuildProgressInfo
from .workers import Worker


class RebuildProgressCallback(Protocol):
    def __call__(self, status_info: DBRebuildProgressInfo): ...


class DBManager(QObject):

    def __init__(self):
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(1)
        self.threadpool.setExpiryTimeout(-1)

        self.tpe = ThreadPoolExecutor(max_workers=1)

    def wait_async(self, fn, *args, **kwargs):
        return self.tpe.submit(fn, *args, **kwargs).result()

    def connect(self, db_path):
        worker = Worker(self.wait_async, db_core.connect, db_path)
        self.threadpool.start(worker)

    def rebuild_files_table(
            self,
            samples_directory,
            progress_callback: Optional[RebuildProgressCallback] = None,
            finished_callback=None,
            result_callback=None):
        worker = Worker(
            self.wait_async,
            db_core.rebuild_files_table,
            samples_directory,
            progress_callback=progress_callback
        )
        worker.signals.progress.connect(progress_callback)
        worker.signals.finished.connect(finished_callback)
        worker.signals.result.connect(result_callback)
        self.threadpool.start(worker)

    def search_file(
            self,
            phrase,
            finished_callback=None,
            result_callback=None):
        worker = Worker(
            self.wait_async,
            lambda: [model_to_dict(m) for m in db_core.search_file(phrase)]
        )
        worker.signals.finished.connect(finished_callback)
        worker.signals.result.connect(result_callback)
        self.threadpool.start(worker)
