# -*- coding: utf-8 -*-

# Copyright(C) 2012-2019  Budget Insight

from __future__ import unicode_literals

from weboob.browser.pages import LoggedPage, JsonPage
from weboob.browser.elements import DictElement, ItemElement, method
from weboob.browser.filters.standard import Date, CleanDecimal, Format, Env, Currency, Field
from weboob.browser.filters.json import Dict
from weboob.capabilities import NotAvailable
from weboob.capabilities.bill import Subscription, Bill


class SigninPage(JsonPage):
    @property
    def logged(self):
        return bool(self.get_token())

    def get_token(self):
        return self.doc.get('meta', {}).get('token', {})


class UserPage(LoggedPage, JsonPage):
    def get_subscription(self):
        user = self.doc['user']
        sub = Subscription()
        sub.subscriber = '%s %s' % (user['first_name'], user['last_name'])
        sub.id = user['id']
        sub.label = user['email']

        return sub


class DocumentsPage(LoggedPage, JsonPage):
    def build_doc(self, text):
        """
        this json contains several lists
        - pnrs
        - proofs
        - folders
        - trips
        - after_sales_logs_dict
        and others

        the most important is proofs, because it contains url with a pdf
        => so one proof gives one bill (for purchase only)
        """
        doc = super(DocumentsPage, self).build_doc(text)

        pnrs_dict = {pnr['id']: pnr for pnr in doc['pnrs']}
        after_sales_logs_dict = {asl['id']: asl for asl in doc['after_sales_logs']}

        bills = []
        for proof in doc['proofs']:
            pnr = pnrs_dict[proof['pnr_id']]
            bill = {
                'id': proof['id'],  # hash of 32 char length
                'url': proof['url'],
                'date': proof['created_at'],
                'type': proof['type'],  # can be 'purchase' or 'refund'
                'currency': pnr['currency'] or '',  # because pnr['currency'] can be None
            }

            assert proof['type'] in ('purchase', 'refund'), proof['type']
            if proof['type'] == 'purchase':
                # pnr['cents'] is 0 if this purchase has a refund, but there is nowhere to take it
                # except make an addition, but we don't do that
                bill['price'] = pnr['cents']
                bills.append(bill)
            else:  # proof['type'] == 'refund'
                after_sales_logs = [after_sales_logs_dict[asl_id] for asl_id in pnr['after_sales_log_ids']]
                for asl in after_sales_logs:
                    new_bill = dict(bill)
                    new_bill['price'] = asl['refunded_cents']
                    bills.append(new_bill)

        return {'bills': bills}

    @method
    class iter_documents(DictElement):
        item_xpath = 'bills'

        class item(ItemElement):
            klass = Bill

            obj_id = Format('%s_%s', Env('subid'), Dict('id'))
            obj_url = Dict('url')
            obj_date = Date(Dict('date'))
            obj_format = 'pdf'
            obj_currency = Currency(Dict('currency'), default=NotAvailable)

            def obj_price(self):
                price = CleanDecimal(Dict('price'), default=NotAvailable)(self)
                if price:
                    return price / 100
                return NotAvailable

            def obj_income(self):
                if Dict('type')(self) == 'purchase':
                    return False
                else:  # type is 'refund'
                    return True

            def obj_label(self):
                if Field('income')(self):
                    return Format('Remboursement du %s', Field('date'))(self)
                else:
                    return Format('Trajet du %s', Field('date'))(self)
