import os
import sqlite3
import logging
import errno
from os.path import isfile
from functools import cache
from core.filemanager import FM


def gW(vals: tuple | set | list):
    if vals is None:
        raise ValueError("vals is empty")
    vals = tuple(sorted(vals))
    if len(vals) == 0:
        raise ValueError("vals is empty")
    if len(vals) == 1:
        return "="+str(vals[0])
    return f"in {vals}"


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def ResultIter(cursor, size=1000):
    while True:
        results = cursor.fetchmany(size)
        if not results:
            break
        for result in results:
            yield result


class EmptyInsertException(sqlite3.OperationalError):
    pass


class DBLite:
    @staticmethod
    def get_connection(file, *extensions, readonly=False):
        logging.info("sqlite: " + file)
        if readonly:
            file = "file:" + file + "?mode=ro"
            con = sqlite3.connect(file, uri=True)
        else:
            con = sqlite3.connect(file)
        if extensions:
            con.enable_load_extension(True)
            for e in extensions:
                con.load_extension(e)
        return con

    def __init__(self, file, extensions=None, reload=False, readonly=False):
        self.readonly = readonly
        self.file = file
        if reload and isfile(self.file):
            os.remove(self.file)
        if self.readonly and not isfile(self.file):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file)
        self.extensions = extensions or []
        self.inTransaction = False
        self.con = DBLite.get_connection(self.file, *self.extensions, readonly=self.readonly)

    def __enter__(self, *args, **kwargs):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

    def openTransaction(self):
        if self.inTransaction:
            self.con.execute("END TRANSACTION")
        self.con.execute("BEGIN TRANSACTION")
        self.inTransaction = True

    def closeTransaction(self):
        if self.inTransaction:
            self.con.execute("END TRANSACTION")
            self.inTransaction = False

    def execute(self, sql: str):
        if FM.exist(sql):
            sql: str = FM.load(sql)
        try:
            self.con.executescript(sql)
        except sqlite3.OperationalError:
            print(sql)
            raise
        self.con.commit()
        self.clear_cache()

    def clear_cache(self):
        self.get_cols.cache_clear()
        self.get_sql_table.cache_clear()

    @property
    def tables(self) -> tuple[str]:
        return self.to_tuple("SELECT name FROM sqlite_master WHERE type='table' order by name")

    @property
    def indices(self):
        return self.to_tuple("SELECT name FROM sqlite_master WHERE type='index' order by name")

    @cache
    def get_sql_table(self, table: str):
        return self.one("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", table)

    @cache
    def get_cols(self, sql: str) -> tuple[str]:
        _sql = sql.lower().split()
        if len(_sql) == 1:
            sql = f"select * from {sql} limit 0"
        elif _sql[-1] != "limit":
            sql = sql + " limit 0"
        cursor = self.con.cursor()
        cursor.execute(sql)
        cols = tuple(col[0] for col in cursor.description)
        cursor.close()
        return cols

    def insert(self, table: str, **kwargs):
        ok_keys = tuple(k.lower() for k in self.get_cols(table))
        keys = []
        vals = []
        for k, v in kwargs.items():
            if v is None or (isinstance(v, str) and len(v) == 0):
                continue
            if k.lower() not in ok_keys:
                continue
            keys.append('"' + k + '"')
            vals.append(v)
        if len(keys) == 0:
            raise EmptyInsertException(f"insert into {table} malformed: give {kwargs}, needed {ok_keys}")
        prm = ['?'] * len(vals)
        sql = "insert into %s (%s) values (%s)" % (
            table, ', '.join(keys), ', '.join(prm))
        self.con.execute(sql, vals)

    def commit(self):
        self.con.commit()

    def close(self, vacuum=True):
        if self.readonly:
            self.con.close()
            return
        self.closeTransaction()
        self.con.commit()
        if vacuum:
            c = self.con.execute("pragma integrity_check")
            c = c.fetchone()
            print("integrity_check =", *c)
            self.con.execute("VACUUM")
        self.con.commit()
        self.con.close()

    def select(self, sql: str, *args, row_factory=None, **kwargs):
        self.con.row_factory = row_factory
        cursor = self.con.cursor()
        try:
            if len(args):
                cursor.execute(sql, args)
            else:
                cursor.execute(sql)
        except sqlite3.OperationalError:
            print(sql)
            raise
        for r in ResultIter(cursor):
            yield r
        cursor.close()
        self.con.row_factory = None

    def to_tuple(self, *args, **kwargs):
        arr = []
        for i in self.select(*args, **kwargs):
            if isinstance(i, (tuple, list)) and len(i)==1:
                i = i[0]
            arr.append(i)
        return tuple(arr)

    def one(self, sql: str, *args):
        cursor = self.con.cursor()
        if len(args):
            cursor.execute(sql, args)
        else:
            cursor.execute(sql)
        r = cursor.fetchone()
        cursor.close()
        if not r:
            return None
        if len(r) == 1:
            return r[0]
        return r
