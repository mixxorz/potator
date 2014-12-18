import os
import sqlite3 as lite

from twisted.python import log


_CREATE_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS potator
    (
        id INTEGER PRIMARY KEY,
        onion_url TEXT,
        ip_address TEXT,
        group_id INTEGER,
        UNIQUE(
            ip_address,
            group_id
        ) ON CONFLICT REPLACE
    );
'''

_SELECT_SQL = '''
SELECT onion_url FROM potator
WHERE ip_address = ?
AND group_id = ?;
'''

_INSERT_SQL = '''
INSERT INTO potator
(ip_address, onion_url, group_id)
VALUES (?, ?, ?);
'''

_SELECT_ALL_SQL = '''
SELECT onion_url
FROM potator
WHERE group_id = ?;
'''

_DROP_TABLE_SQL = '''
DROP TABLE potator;
'''


class Database(object):

    def __init__(self, lock):
        self.lock = lock
        self.database_name = os.path.join(
            os.environ['AppData'], 'potator', 'db.sqlite3')
        self.table_name = 'onion_ip_mappings'

    def connect(self):
        return lite.connect(self.database_name)

    def cleandb(self):
        try:
            self.dropdb()
        except:
            pass
        finally:
            self.syncdb()

    def syncdb(self):
        self.lock.acquire()
        try:
            con = self.connect()
            cur = con.cursor()
            cur.execute(_CREATE_TABLE_SQL)
            con.commit()
            con.close()
        finally:
            self.lock.release()

    def dropdb(self):
        self.lock.acquire()
        try:
            con = self.connect()
            cur = con.cursor()
            cur.execute(_DROP_TABLE_SQL)
            con.commit()
            con.close()
        finally:
            self.lock.release()

    def getOnionUrl(self, ip_address, group_id):
        ''' Get Onion URL of an ip_address and group_id
        '''
        self.lock.acquire()
        try:
            con = self.connect()
            cur = con.cursor()
            cur.execute(_SELECT_SQL, (ip_address, group_id))
            rows = cur.fetchall()
            con.close()
        finally:
            self.lock.release()
        try:
            return rows[0][0]
        except IndexError:
            log.msg('Unknown IP address: %s [%d]' % (ip_address, group_id))
            return None

    def setOnionUrl(self, ip_address, onion_url, group_id):
        ''' Add a new row to the onion IP database
        '''
        self.lock.acquire()
        try:
            con = self.connect()
            cur = con.cursor()
            cur.execute(_INSERT_SQL, (ip_address, onion_url, group_id))
            log.msg('Saving: %s = %s = [%d]' % (ip_address, onion_url, group_id))
            con.commit()
            con.close()
        finally:
            self.lock.release()

    def getAllOnionUrls(self, group_id):
        self.lock.acquire()
        try:
            con = self.connect()
            cur = con.cursor()
            cur.execute(_SELECT_ALL_SQL, (group_id,))
            rows = cur.fetchall()
            con.close()
        finally:
            self.lock.release()

        return [x[0] for x in rows]


class OnionIPMapper(object):

    def __init__(self):
        self.mappings = {}

    def getOnionUrl(self, ip_address):
        return self.mappings.get('ip_address')

    def setOnionUrl(self, ip_address, onion_url):
        self.mappings[ip_address] = onion_url

    def getAllOnionUrls(self):
        return [value for key, value in self.mappings.iteritems()]
