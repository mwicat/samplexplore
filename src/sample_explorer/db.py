import sqlite3

SQL_SEARCH = '''
SELECT full_path, filename FROM files WHERE filename MATCH ? ORDER BY RANK;
'''


class SampleDB(object):

    def __init__(self, db_path):
        self._connection = sqlite3.connect(db_path)
        self._cursor = self._connection.cursor()

    def search_file(self, phrase):
        self._cursor.execute(SQL_SEARCH, (phrase,))
        return self._cursor.fetchall()
