# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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

from weboob.browser.pages import HTMLPage
from weboob.browser.filters.standard import CleanText, Env, Field, CleanDecimal, Date, Format
from weboob.browser.elements import ItemElement, ListElement, method

from weboob.capabilities.pricecomparison import Product, Shop, Price


class IndexPage(HTMLPage):

    def get_token(self):
        return CleanText('//input[@id="recherche_recherchertype__token"]/@value')(self.doc)

    @method
    class iter_products(ListElement):
        item_xpath = '//div[@id="choix_carbu"]/ul/li'

        class item(ItemElement):
            klass = Product

            obj_id = CleanText('./input/@value')
            obj_name = CleanText('./label')


class ComparisonResultsPage(HTMLPage):

    @method
    class iter_results(ListElement):

        item_xpath = '//table[@id="tab_resultat"]/tr'

        class item(ItemElement):
            klass = Price

            def condition(self):
                return CleanText('./@id', default=False)(self)

            obj_product = Env('product')

            def obj_id(self):
                product = Field('product')(self)
                _id = CleanText('./@id')(self)
                return u"%s.%s" % (product.id, _id)

            def obj_shop(self):
                _id = Field('id')(self)
                shop = Shop(_id)
                shop.name = CleanText('(./td)[4]')(self)
                shop.location = CleanText('(./td)[3]')(self)
                return shop

            obj_date = Date(CleanText('(./td)[7]'), dayfirst=True)
            obj_currency = u'€'
            obj_cost = CleanDecimal('(./td)[6]')

    def get_product_name(self):
        return CleanText('(//table[@id="tab_resultat"]/tr/th)[6]',
                         default='')(self.doc)


class ShopInfoPage(HTMLPage):
    def get_info(self):
        return Format('%s\n\r%s',
                      CleanText('(//div[@class="infos"]/p)[1]/text()'),
                      CleanText('(//div[@class="infos"]/p)[2]'))(self.doc)
