# -*- coding: utf-8 -*-

# Copyright(C) 2018      Quentin Defenouillere
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


from weboob.browser.elements import ItemElement, method, DictElement
from weboob.browser.filters.standard import CleanDecimal, Date, Field, Env
from weboob.browser.filters.json import Dict
from weboob.browser.pages import AbstractPage
from weboob.capabilities.bank import Investment
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.bank.investments import is_isin_valid


class AccountsPage(AbstractPage):
    PARENT = 'amundi'
    PARENT_URL = 'accounts'

    @method
    class iter_investments(DictElement):
        def find_elements(self):
            for psds in Dict('listPositionsSalarieFondsDto')(self):
                for psd in psds.get('positionsSalarieDispositifDto'):
                    if psd.get('codeDispositif') == Env('account_id')(self):
                        return psd.get('positionsSalarieFondsDto')
            return {}

        class item(ItemElement):
            klass = Investment

            obj_label = Dict('libelleFonds')
            obj_unitvalue = Dict('vl') & CleanDecimal
            obj_quantity = Dict('nbParts') & CleanDecimal
            obj_valuation = Dict('mtBrut') & CleanDecimal
            obj_code = Dict('codeIsin', default=NotAvailable)
            obj_vdate = Date(Dict('dtVl'))
            # The "diff" is only present on the CAELS website but not its parent (amundi):
            obj_diff = Dict('mtPMV') & CleanDecimal

            def obj_code_type(self):
                if is_isin_valid(Field('code')(self)):
                    return Investment.CODE_TYPE_ISIN
                return NotAvailable
