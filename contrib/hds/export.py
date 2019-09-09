#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright(C) 2011 Romain Bignon
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

try:
    import sqlite3 as sqlite
except ImportError as e:
    from pysqlite2 import dbapi2 as sqlite

from weboob.core import Weboob
from weboob.exceptions import ModuleLoadError
import sys
import logging
level = logging.DEBUG
logging.basicConfig(stream=sys.stdout, level=level)


def main(filename):
    weboob = Weboob()
    try:
        hds = weboob.build_backend('hds')
    except ModuleLoadError as e:
        print('Unable to load "hds" module: %s' % e, file=sys.stderr)
        return 1

    try:
        db = sqlite.connect(database=filename, timeout=10.0)
    except sqlite.OperationalError as err:
        print('Unable to open %s database: %s' % (filename, err), file=sys.stderr)
        return 1

    sys.stdout.write('Reading database... ')
    sys.stdout.flush()
    try:
        results = db.execute('SELECT id, author FROM stories')
    except sqlite.OperationalError as err:
        print('fail!\nUnable to read database: %s' % err, file=sys.stderr)
        return 1

    stored = set()
    authors = set()
    for r in results:
        stored.add(r[0])
        authors.add(r[1])
    stored_authors = set([s[0] for s in db.execute('SELECT name FROM authors')])
    sys.stdout.write('ok\n')

    br = hds.browser
    to_fetch = set()
    sys.stdout.write('Getting stories list from website... ')
    sys.stdout.flush()
    for story in br.iter_stories():
        if int(story.id) in stored:
            break
        to_fetch.add(story.id)
        authors.add(story.author.name)
    sys.stdout.write(' ok\n')

    sys.stdout.write('Getting %d new storiese... ' % len(to_fetch))
    sys.stdout.flush()
    for id in to_fetch:
        story = br.get_story(id)
        if not story:
            logging.warning('Story #%d unavailable' % id)
            continue

        db.execute("""INSERT INTO stories (id, title, date, category, author, body)
                             VALUES (?, ?, ?, ?, ?, ?)""",
                   (story.id, story.title, story.date, story.category,
                    story.author.name, story.body))
        db.commit()
    sys.stdout.write('ok\n')

    authors = authors.difference(stored_authors)
    sys.stdout.write('Getting %d new authors... ' % len(authors))
    sys.stdout.flush()
    for a in authors:
        author = br.get_author(a)
        if not author:
            logging.warning('Author %s unavailable\n' % id)
            continue

        db.execute("INSERT INTO authors (name, sex, description) VALUES (?, ?, ?)",
                   (a, author.sex, author.description))
        db.commit()
    sys.stdout.write(' ok\n')
    return 0

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Syntax: %s [--help] SQLITE_FILENAME' % sys.argv[0], file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] in ('-h', '--help'):
        print('Syntax: %s SQLITE_FILENAME' % sys.argv[0])
        print('')
        print('Before running this software, please create the database with')
        print('this command:')
        print('  $ cat scheme.sql | sqlite3 hds.sql')
        print('')
        print('You can then run export.py with:')
        print('  $ %s hds.sql ' % sys.argv[0])
        print('')
        print('It fill the database with stories and authors information')
        print('fetched from histoires-de-sexe.net')
        print('')
        print('You can next use SQL queries to find interesting stories, for')
        print('example:')
        print('')
        print('- To get all stories written by women')
        print('  sqlite> SELECT s.id, s.title, s.category, a.name')
        print('                 FROM stories AS s LEFT JOIN authors AS a')
        print('                 WHERE a.name = s.author AND a.sex = 2;')
        print('- To get all stories where it talks about bukkake')
        print('  sqlite> SELECT s.id, s.title, s.category, a.name')
        print('                 FROM stories AS s LEFT JOIN authors AS a')
        print('                 WHERE a.name = s.author AND s.body LIKE \'%bukkake%\';')
        sys.exit(0)

    sys.exit(main(sys.argv[1]))
