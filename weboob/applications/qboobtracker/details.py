# -*- coding: utf-8 -*-

# Copyright(C) 2013 Sébastien Monel
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

from __future__ import unicode_literals

from xml.sax.saxutils import escape as escape_html

from PyQt5.QtWidgets import QDialog
from weboob.tools.compat import unicode
from weboob.capabilities.base import empty

from .ui.details_ui import Ui_Dialog


def esc(o):
    return escape_html(unicode(o))


class DetailDialog(QDialog):
    def __init__(self, issue, parent=None):
        super(DetailDialog, self).__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.issue = issue

        self.ui.titleEdit.setText(unicode(issue.title))
        self.ui.authorEdit.setText(unicode(issue.author and issue.author.name))
        self.ui.assigneeEdit.setText(unicode(issue.assignee and issue.assignee.name))
        self.ui.creationEdit.setText(unicode(issue.creation))
        self.ui.lastEdit.setText(unicode(issue.updated))

        url = ''
        if issue.url:
            url = '<a href="%s">%s</a>' % (issue.url, issue.url)
        self.ui.linkLabel.setText(url)

        self.ui.bodyEdit.setPlainText(unicode(issue.body))
        self.ui.updatesEdit.setHtml(self.updatesToHtml(issue.history))

    def updatesToHtml(self, updates):
        if empty(updates):
            return ''

        parts = []
        for update in updates:
            parts.append('<b>%s</b> %s' % (update.date, esc(update.author and update.author.name)))
            if update.message or not update.changes:
                parts.append('<pre>%s</pre>' % esc(update.message))
            parts.extend(self.changesToHtml(update.changes))
            parts.append('<hr/>')
        return '\n'.join(parts)

    def changesToHtml(self, changes):
        if not changes:
            return

        yield '<ul>'
        for change in changes:
            yield '<li><i>%s</i> changed to <i><ins>%s</ins></i> (from <i><del>%s</del></i>)</li>' % (esc(change.field), esc(change.new), esc(change.last))
        yield '</ul>'

