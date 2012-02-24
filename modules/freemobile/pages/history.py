# -*- coding: utf-8 -*-

# Copyright(C) 2012 Florent Fourcot
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


from weboob.tools.browser import BasePage
from weboob.capabilities.bill import Detail

__all__ = ['HistoryPage']

def convert_price(div):
    try:
        price = div.find('div[@class="horsForfait"]/p/span').text
        price = price.encode('utf-8', 'replace').replace('€', '').replace(',', '.')
        return float(price)
    except:
        return 0.


class HistoryPage(BasePage):
    calls = []
    details = []

    def on_loaded(self):

        divnat = self.document.xpath('//div[@class="national"]')[0]
        divs = divnat.xpath('div[@class="detail"]')
        divvoice = divs.pop(0)

        # Two informations in one div... 
        voice = Detail()
        voice.label = divvoice.find('div[@class="titreDetail"]/p').text_content()
        voice.price = convert_price(divvoice)
        voicenat = divvoice.xpath('div[@class="consoDetail"]/p/span')[0].text
        voiceint = divvoice.xpath('div[@class="consoDetail"]/p/span')[1].text
        voice.infos = "Consommation : " + voicenat + " International : " + voiceint               
        self.details.append(voice)

        self.iter_divs(divs)
        divint = self.document.xpath('//div[@class="international hide"]')[0]
        self.iter_divs(divint.xpath('div[@class="detail"]'), True)


    def iter_divs(self, divs, inter=False):
        for div in divs:
            detail = Detail()

            detail.label = div.find('div[@class="titreDetail"]/p').text_content()
            if inter:
                detail.label = detail.label + " (international)"
            detail.infos = div.find('div[@class="consoDetail"]/p').text_content().lstrip()
            detail.price = convert_price(div)

            self.details.append(detail)

        

    def get_calls(self):
        return self.calls

    def get_details(self):
        return self.details
