from dataclasses import dataclass
import re
import os

from peewee import *
from playhouse.kv import KeyValue
from playhouse.sqlite_ext import FTS5Model, RowIDField, SearchField
from playhouse.shortcuts import model_to_dict


db = SqliteDatabase(None)
config = None


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


def get_config():
    global config
    if config is None:
        config = KeyValue(database=db, table_name='Configuration')
    return config


class Files(Model):
    full_path = TextField(null=False, unique=True)
    filename = TextField(null=False)

    class Meta:
        database = db


class FilesIndex(FTS5Model):
    rowid = RowIDField()
    filename = SearchField()

    class Meta:
        database = db
        options = {
            'tokenize': 'trigram',
            'content': Files,
        }


@dataclass
class DBRebuildProgressInfo(object):
    num_files_total: int = 0
    num_dirs_total: int = 0
    current_dir: str = ''


def connect(db_path):
    db.init(db_path)


def create_tables():
    db.create_tables([Files, FilesIndex])


def search_file(phrase):
    phrase = re.sub(r"[\"\'.\*]%&", ' ', phrase).strip()
    if not phrase:
        return

    q = (Files
            .select()
            .join(
                FilesIndex,
                on=(Files.id == FilesIndex.rowid))
            .where(FilesIndex.match(phrase))
            .order_by(FilesIndex.rank()))
    return q.execute()


def rebuild_files_table(
        samples_directory,
        supported_extensions=DEFAULT_SUPPORTED_EXTENSIONS,
        progress_callback=None):
    progress_info_total = DBRebuildProgressInfo()

    def yield_records():
        for root, dirs, files in os.walk(samples_directory):
            for fn in files:
                fn_base, fn_ext = os.path.splitext(fn)
                if fn_ext:
                    fn_ext = fn_ext[1:].lower()
                    if fn_ext not in supported_extensions:
                        continue

                file_path = os.path.join(root, fn)
                yield file_path, fn

            if progress_callback is not None:
                progress_info_total.num_dirs_total += len(dirs)
                progress_info_total.num_files_total += len(files)

                progress_info = DBRebuildProgressInfo(
                    num_files_total=progress_info_total.num_files_total,
                    num_dirs_total=progress_info_total.num_dirs_total,
                    current_dir=root)
                #progress_callback(5)

    with db.atomic():
        Files.delete().execute()

        for batch in chunked(yield_records(), 100):
            Files.insert_many(batch).execute()

        FilesIndex.rebuild()
        FilesIndex.optimize()

        get_config()['samples_directory'] = samples_directory
