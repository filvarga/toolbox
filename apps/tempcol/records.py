#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# autor: Filip Varga

DEBUG = False

from sys import stderr
from sqlite3 import connect
from datetime import datetime
from bs4 import BeautifulSoup
from collections import namedtuple
from contextlib import contextmanager
from urlparse import urlparse, parse_qs
from requests import session, RequestException

Record = namedtuple('Record', 'datetime measurement')

class ConnectionException(Exception): pass

class PageException(Exception): pass

class Page(object):

    def __init__(self, url):
        self._soup = None
        self._url = url
    
    def get(self):
        # debug:
        if DEBUG:
            stderr.write(u"[debug] url: %s\n" % self._url)
        try:
            with session() as so:
                content = so.get(self._url).content
        except RequestException:
            raise ConnectionException()

        self._soup = BeautifulSoup(
            content,
            'html.parser')

    def findLastPageNum(self):
        lis = self._soup.find_all(
            'li',
            attrs={'class', 'PagedList-skipToLast'},
            limit=1)

        if not lis:
            raise PageException()

        try:
            url = lis[0].a['href']
        except KeyError, TypeError:
            raise PageException()

        if not url:
            raise PageException()

        try:
            num = int(parse_qs(urlparse(url).query)['page'][0])
        except KeyError, IndexError:
            raise PageException()

        return num

    def findRecords(self):
        try:
            tr = self._soup.table.tbody.tr
        except AttributeError:
            raise PageException()

        if not tr:
            raise PageException()

        while tr:

            try:
                timestamp, measurement = tr.find_all('td')
            except ValueError:
                raise PageException()
            
            try:
                timestamp = datetime.strptime(
                    timestamp.string,
                    "%m/%d/%Y %I:%M:%S %p")
            except ValueError:
                raise PageException()
            
            yield Record(timestamp, measurement.string)

            tr = tr.find_next_sibling('tr')

class App(object):

    def __init__(self, server, vendor_id, device_id, appbundle):
        self.appbundle = appbundle
        self.device_id = device_id
        self.vendor_id = vendor_id

        if not server.startswith("http://"):
            self.server = "http://{}".format(server)

    def url(self, page_n):
        fstr = "{}/Home/MeasurementDetails?page={}&pagesize=250" \
               "&deviceid={}&vendorid={}&appbundle={}"

        return fstr.format(
            self.server,
            1 if page_n < 1 else page_n,
            self.device_id,
            self.vendor_id,
            self.appbundle
        )

    # musis zavolat page.get(), aj, ked nechces spracovat stranku
    def getPages(self):
        i = 1
        while True:
            page = Page(self.url(i))
            yield page

            try:
                l = page.findLastPageNum()
            except PageException:
                break
            else:
                if i > l:
                    break
            i = i + 1

class Records(object):

    def __init__(self, conn):
        self._conn = conn

    def update(self, since, server, vendor_id, device_id, appbundle):
        cur = self._conn.cursor()
        app = App(server, vendor_id, device_id, appbundle)

        cur.execute(
            "CREATE TABLE IF NOT EXISTS records (" \
            "datetime timestamp NOT NULL PRIMARY KEY," \
            "measurement text NOT NULL" \
            ");")

        for i, page in enumerate(app.getPages()):
            try:
                page.get()
            except ConnectionException:
                stderr.write("[error] Chyba sieťovej komunikácie.\n")
                break

            # exception sa nezachyti v tomto bode ale
            # az pri iteracii koli yield
            try:
                for record in page.findRecords():
                    # debug
                    if DEBUG:
                        stderr.write(u"[debug] record: %s\n" % record.datetime)

                    if record.datetime < since:
                        return

                    cur.execute("INSERT OR IGNORE INTO RECORDS VALUES (?,?);",
                    (record.datetime, record.measurement))

                    # commit po kazdom zazname
                    self._conn.commit()

            except PageException:
                stderr.write("[error] Chyba formátu stránky.\n")
                break
                        
    def getAll(self, since):
        cur = self._conn.cursor()

        results = cur.execute("SELECT * FROM records WHERE datetime >= ?;",
        (since,))

        for dtime, measurement in results:
            yield Record(dtime, measurement)

    def get(self, since):
        cur = self._conn.cursor()
        till = datetime(since.year, since.month, since.day, 23, 59, 59)

        results = cur.execute("SELECT * FROM records WHERE datetime >= ? AND datetime <= ?;",
        (since,till))

        for dtime, measurement in results:
            yield Record(dtime, measurement)


@contextmanager
def records(db):
    conn = connect(db)
    try:
         yield Records(conn)
    finally:
        conn.close()
