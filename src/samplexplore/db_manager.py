from concurrent.futures import ThreadPoolExecutor
import logging
from typing import Optional, Protocol

from playhouse.shortcuts import model_to_dict

from qtpy.QtCore import *

from . import db_core
from .db_core import DBRebuildProgressInfo


class RebuildProgressCallback(Protocol):
    def __call__(self, status_info: DBRebuildProgressInfo): ...


class ThreadProxy(QObject):

    progress = Signal()
    finished = Signal()
    result = Signal(object)

    def __init__(self, log_proxy, fn, *args, **kwargs):
        super(ThreadProxy, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.log_proxy = log_proxy

    def run(self):
        return self.fn(*self.args, **self.kwargs)

    def on_done(self, future):
        res = future.result()
        try:
            self.result.emit(res)
        except Exception as e:
            self.log_proxy.error.emit(e)
            logging.error("Logging an uncaught exception", exc_info=True)


class DBManager(QObject):

    def __init__(self, log_proxy):
        super().__init__()
        self.log_proxy = log_proxy
        self.tpe = ThreadPoolExecutor(max_workers=1)

    def shutdown(self):
        self.tpe.shutdown()

    def _run_async(self, result_callback, fn, *args, **kwargs):
        proxy = ThreadProxy(self.log_proxy, fn, *args, **kwargs)
        if result_callback is not None:
            proxy.result.connect(result_callback)
        self.tpe.submit(proxy.run).add_done_callback(proxy.on_done)

    def connect(self, db_path, result_callback=None):
        def db_connect():
            db_core.connect(db_path)
            db_core.create_tables()

        self._run_async(result_callback, db_connect)

    def rebuild_files_table(
            self,
            samples_directory,
            progress_callback: Optional[RebuildProgressCallback] = None,
            result_callback=None):

        self._run_async(
            result_callback,
            db_core.rebuild_files_table,
            samples_directory,
            progress_callback=progress_callback)

    def search_file(
            self,
            phrase,
            result_callback=None):
        def db_search_file():
            res = db_core.search_file(phrase)
            if res is not None:
                return [model_to_dict(m) for m in res]
            else:
                return []

        self._run_async(
            result_callback,
            db_search_file)
