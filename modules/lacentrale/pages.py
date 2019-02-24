# -*- coding: utf-8 -*-

# Copyright(C) 2014 Vicnet
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


from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.filters.standard import CleanText, Regexp, CleanDecimal, Format, Env, BrowserURL
from weboob.browser.filters.javascript import JSVar
from weboob.browser.filters.html import Link
from weboob.capabilities.pricecomparison import Price, Shop
from .product import LaCentraleProduct


class ListingAutoPage(HTMLPage):
    @pagination
    @method
    class iter_prices(ListElement):
        item_xpath = '//div[@class="adContainer "]'
        next_page = Link('//section[@class="pagination"]/ul/li[@class="last"]/a')

        class item(ItemElement):
            klass = Price

            obj_id = CleanText('./p/a/@data-annid')
            obj_cost = CleanDecimal('./a/div/div/div/div[@class="fieldPrice"]')
            obj_currency = Regexp(CleanText('./a/div/div/div/div[@class="fieldPrice"]'),
                                  '.*([%s%s%s])' % (u'€', u'$', u'£'), default=u'€')
            obj_message = Format('%s / %s / %s',
                                 CleanText('./a/div/div/h3'),
                                 CleanText('./a/div/div/div/div[@class="fieldYear"]'),
                                 CleanText('./a/div/div/div/div[@class="fieldMileage"]'))
            obj_url = Format('http://www.lacentrale.fr%s',
                             CleanText('./a/@href'))

            obj_product = LaCentraleProduct()

            def obj_shop(self):
                shop = Shop(CleanText('./p/a/@data-annid')(self))
                return shop


class AdvertPage(HTMLPage):

    @method
    class get_price(ItemElement):
        klass = Price

        obj_id = Env('_id')

        obj_cost = CleanDecimal('//div[@class="mainInfos"]/div/p[@class="gpfzj"]')
        obj_currency = Regexp(CleanText('//div[@class="mainInfos"]/div/p[@class="gpfzj"]'),
                              '.*([%s%s%s])' % (u'€', u'$', u'£'), default=u'€')
        obj_message = Format('%s %s',
                             CleanText('//div[@class="mainInfos"]/div/div/h1'),
                             CleanText('//div[@class="mainInfos"]/div/div/p'))
        obj_url = BrowserURL('advert_page', _id=Env('_id'))

        def obj_shop(self):
            shop = Shop(Env('_id')(self))
            shop.name = Regexp(CleanText('(//div[@xtcz="contacter_le_vendeur"]/div/ul/li)[1]'),
                               'Nom : (.*)')(self)
            shop.location = JSVar(CleanText('//script'), var='tooltip')(self)
            shop.info = CleanText('//div[@xtcz="contacter_le_vendeur"]/div/ul/li[has-class("printPhone")]')(self)
            return shop

        obj_product = LaCentraleProduct()
