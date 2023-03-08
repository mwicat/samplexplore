from collections import namedtuple
import os
import sqlite3


SQL_SEARCH = '''
SELECT full_path, filename FROM files WHERE filename MATCH ? ORDER BY RANK;
'''

SQL_CREATE_FILES_TABLE = '''
CREATE VIRTUAL TABLE files 
USING FTS5(full_path, filename, tokenize="trigram");
'''

SQL_DROP_FILES_TABLE = '''
DROP TABLE IF EXISTS files;
'''

SQL_INSERT_FILES = '''
INSERT INTO files(full_path, filename)
VALUES (?, ?);
'''

DEFAULT_SUPPORTED_EXTENSIONS = [
    'wav',
    'aif',
    'mp3',
    'flac',
]


DBRebuildStatusInfo = namedtuple(
    'DBRebuildStatusInfo',
    'num_files_total num_dirs_total current_dir',
)


class SampleDB(object):

    def __init__(self, db_path, samples_directory, supported_extensions=None):
        if supported_extensions is None:
            self.supported_extensions = DEFAULT_SUPPORTED_EXTENSIONS

        self.samples_directory = samples_directory

        self._connection = sqlite3.connect(db_path)
        self._cursor = self._connection.cursor()

    def search_file(self, phrase):
        self._cursor.execute(SQL_SEARCH, (phrase,))
        return self._cursor.fetchall()

    def rebuild_files_table(self, status_callback=None):
        self._cursor.execute(SQL_DROP_FILES_TABLE)
        self._cursor.execute(SQL_CREATE_FILES_TABLE)

        status_info_total = DBRebuildStatusInfo()

        def yield_records():
            for root, dirs, files in os.walk(self.samples_directory):
                for fn in files:
                    fn_base, fn_ext = os.path.splitext(fn)
                    if fn_ext:
                        fn_ext = fn_ext[1:].lower()
                        if fn_ext not in self.supported_extensions:
                            continue

                    file_path = os.path.join(root, fn)
                    yield file_path, fn

                if status_callback is not None:
                    status_info_total.num_dirs_total += len(dirs)
                    status_info_total.num_files_total += len(files)

                    status_info = DBRebuildStatusInfo(
                        num_files_total=status_info_total.num_files_total,
                        num_dirs_total=status_info.num_dirs_total,
                        current_dir=root)
                    status_callback()

        self._cursor.executemany(SQL_INSERT_FILES, yield_records())
        self._connection.commit()
