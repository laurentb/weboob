# -*- coding: utf-8 -*-

# Copyright(C) 2017      Phyks (Lucas Verney)
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

import datetime

from weboob.browser.elements import method, ItemElement, ListElement
from weboob.browser.filters.html import Attr
from weboob.browser.filters.standard import CleanText, Eval
from weboob.browser.pages import HTMLPage
from weboob.capabilities.gauge import Gauge, GaugeMeasure

NORMAL = 0.0
NORMAL_AND_WORK = -1.0
ALERT = -2.0
ALERT_AND_WORK = -3.0
CRITICAL = -4.0
CRITICAL_AND_WORK = -5.0


class MeteoPage(HTMLPage):
    @method
    class fetch_lines(ListElement):
        item_xpath = u'//*[@class="lignes"]/div'

        class Line(ItemElement):
            klass = Gauge

            obj_city = u"Paris"
            obj_object = u"Current status"
            obj_id = Attr(u'.', attr=u'id')
            obj_name = Eval(
                lambda x: (
                    x
                    .replace(u'ligne_', u'')
                    .replace(u'_', u' ')
                    .title()
                    .replace(u'Rer', u'RER')
                ),
                obj_id
            )

    @method
    class fetch_status(ListElement):
        item_xpath = u'//div[@id="box"]'

        class Line(ItemElement):
            klass = GaugeMeasure

            def obj_level(self):
                classes = Attr(
                    u'//*[@class="lignes"]//div[@id="%s"]' % self.env[u'line'],
                    attr='class'
                )(self)
                classes = classes.split()
                if u"perturb_critique_trav" in classes:
                    return CRITICAL_AND_WORK
                elif u"perturb_critique" in classes:
                    return CRITICAL
                elif u"perturb_alerte_trav" in classes:
                    return ALERT_AND_WORK
                elif u"perturb_alerte" in classes:
                    return ALERT
                elif u"perturb_normal_trav" in classes:
                    return NORMAL_AND_WORK
                elif u"perturb_normal" in classes:
                    return NORMAL

            def obj_alarm(self):
                title = CleanText(
                    u'//*[@class="lignes"]//div[@id="%s"]//div[@class="popin_hover_title"]' % self.env[u'line']
                )(self)
                details = CleanText(
                    u'//*[@class="lignes"]//div[@id="%s"]//div[@class="popin_hover_text"]//span[1]' % self.env[u'line']
                )(self)
                return u"%s: %s" % (title, details)

            def obj_date(self):
                time = CleanText(u'//span[@id="refresh_time"]')(self)
                time = [int(t) for t in time.split(":")]
                now = datetime.datetime.now()
                now.replace(hour=time[0], minute=time[1])
                return now
