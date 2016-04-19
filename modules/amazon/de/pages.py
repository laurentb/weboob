# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


import re
from datetime import datetime

from ..pages import OrderNewPage


class OrderNewPageDE(OrderNewPage):
    def order_date(self):
        return datetime.strptime(
            re.match('.*Ordered on ([0-9]+ [\w]+ [0-9]+) .*',
                     self.date_num()).group(1),
            '%d %B %Y')
