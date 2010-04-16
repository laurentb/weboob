# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

try:
    import sqlite3 as sqlite
except ImportError, e:
    from pysqlite2 import dbapi2 as sqlite

from mechanize import CookieJar, Cookie


__all__ = ['FirefoxCookieJar']


class FirefoxCookieJar(CookieJar):
    def __init__(self, domain, sqlite_file=None, policy=None):
        CookieJar.__init__(self, policy)

        self.domain = domain
        self.sqlite_file = sqlite_file

    def __connect(self):
        try:
            db = sqlite.connect(database=self.sqlite_file, timeout=10.0)
        except sqlite.OperationalError, err:
            print 'Unable to open %s database: %s' % (self.sqlite_file, err)
            return None

        return db

    def load(self):
        db = self.__connect()
        if not db: return

        cookies = db.execute("""SELECT host, path, name, value, expiry, lastAccessed, isSecure
                                FROM moz_cookies
                                WHERE host LIKE '%%%s%%'""" % self.domain)

        for entry in cookies:
            domain = entry[0]
            initial_dot = domain.startswith(".")
            domain_specified = initial_dot
            path = entry[1]
            name = entry[2]
            value = entry[3]
            expires = entry[4]
            secure = entry[6]

            discard = False

            c = Cookie(0, name, value,
                           None, False,
                           domain, domain_specified, initial_dot,
                           path, False,
                           secure,
                           expires,
                           discard,
                           None,
                           None,
                           {})
            #if not ignore_discard and c.discard:
            #    continue
            #if not ignore_expires and c.is_expired(now):
            #    continue
            self.set_cookie(c)

    def save(self):
        db = self.__connect()
        if not db: return

        db.execute("DELETE FROM moz_cookies WHERE host LIKE '%%%s%%'" % self.domain)
        for cookie in self:
            if cookie.secure: secure = 1
            else: secure = 0
            if cookie.expires is not None:
                expires = cookie.expires
            else:
                expires = 0

            if cookie.value is None:
                # cookies.txt regards 'Set-Cookie: foo' as a cookie
                # with no name, whereas cookielib regards it as a
                # cookie with no value.
                name = ""
                value = cookie.name
            else:
                name = cookie.name
                value = cookie.value

            # XXX ugly hack to keep this cookie
            if name == 'PHPSESSID':
                expires = 1854242393

            db.execute("""INSERT INTO moz_cookies (host, path, name, value, expiry, isSecure)
                                 VALUES (?, ?, ?, ?, ?, ?)""",
                       (cookie.domain, cookie.path, name, value, int(expires), int(secure)))
            db.commit()
