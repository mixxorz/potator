import os
import sqlite3 as lite

from twisted.python import log


class Database(object):

    def __init__(self, lock):
        self.lock = lock
        self.database_name = os.path.join(
            os.environ['AppData'], 'potator', 'db.sqlite3')
        self.table_name = 'onion_ip_mappings'

    def connect(self):
        return lite.connect(self.database_name)

    def syncdb(self):
        self.lock.acquire()
        try:
            con = self.connect()
            cur = con.cursor()
            cmd = 'CREATE TABLE IF NOT EXISTS %s ' % self.table_name +\
                '(id INTEGER PRIMARY KEY, onion_url TEXT, ' +\
                'ip_address TEXT, group_id INTEGER)'
            cur.execute(cmd)
            con.commit()
            con.close()
        finally:
            self.lock.release()

    def getOnionURL(self, ip_address, group_id):
        ''' Get Onion URL of an ip_address and group_id
        '''
        self.lock.acquire()
        try:
            con = self.connect()
            cmd = 'SELECT onion_url FROM %s ' % self.table_name +\
                'WHERE ip_address = "%s" ' % ip_address +\
                'AND group_id = "%s"' % group_id
            cur = con.cursor()
            cur.execute(cmd)
            rows = cur.fetchall()
            con.close()
        finally:
            self.lock.release()
        try:
            return rows[0][0]
        except IndexError:
            log.msg('Unknown IP address: %s' % ip_address)
            return None

    def setOnionURL(self, ip_address, onion_url, group_id):
        ''' Add a new row to the onion IP database
        '''
        # TODO: Make sure the Onion URL + group_id is unique
        self.lock.acquire()
        try:
            con = self.connect()
            cur = con.cursor()
            cmd = 'INSERT INTO %s ' % self.table_name +\
                '(ip_address, onion_url, group_id)' +\
                'VALUES ("%s","%s","%s")' % (
                    ip_address,
                    onion_url,
                    group_id
                )
            cur.execute(cmd)
            con.commit()
            con.close()
        finally:
            self.lock.release()

    def getAllOnionURL(self, group_id):
        self.lock.acquire()
        try:
            con = self.connect()
            cur = con.cursor()
            cmd = 'SELECT onion_url FROM %s ' % self.table_name +\
                'WHERE group_id = "%s"' % group_id
            cur.execute(cmd)
            rows = cur.fetchall()
            con.close()
        finally:
            self.lock.release()

        return rows

    def dropTable(self):
        self.lock.acquire()
        try:
            con = self.connect()
            cur = con.cursor()
            cur.execute('DROP TABLE IF EXISTS %s' % self.table_name)
            con.commit()
            con.close()
        finally:
            self.lock.release()
