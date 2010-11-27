# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


import re
from weboob.capabilities.bank import Account
from .base import CragrBasePage
from weboob.capabilities.bank import Operation

class AccountsList(CragrBasePage):
    def get_list(self):
        """
            Returns the list of available bank accounts
        """
        l = []

        for div in self.document.getiterator('div'):
            if div.attrib.get('class', '') == 'dv' and div.getchildren()[0].tag in ('a', 'br'):
                account = Account()
                if div.getchildren()[0].tag == 'a':
                    # This is at least present on CA Nord-Est
                    account.label = ' '.join(div.find('a').text.split()[:-1])
                    account.link_id = div.find('a').get('href', '')
                    account.id = div.find('a').text.split()[-1]
                    s = div.find('div').find('b').find('span').text
                else:
                    # This is at least present on CA Toulouse
                    account.label = div.find('a').text.strip()
                    account.link_id = div.find('a').get('href', '')
                    account.id = div.findall('br')[1].tail.strip()
                    s = div.find('div').find('span').find('b').text
                balance = u''
                for c in s:
                    if c.isdigit():
                        balance += c
                    if c == ',':
                        balance += '.'
                account.balance = float(balance)
                l.append(account)
        return l

    def is_account_page(self):
        """
            Returns True if the current page appears to be a page dedicated to list
            the history of a specific account.
        """
        # tested on CA Lorraine, Paris, Toulouse
        title_spans = self.document.xpath('/html/body/div[@class="dv"]/span')
        for title_span in title_spans:
            title_text = title_span.text_content().strip().replace("\n", '')
            if (re.match('.*Compte.*n.[0-9]+.*au.*', title_text)):
                return True
        return False

    def next_page_url(self):
        """
            When on a page dedicated to list the history of a specific account (see
            is_account_page), returns the link to the next page, or False if the
            link is not present.
        """
        # tested on CA Lorraine, Paris, Toulouse
        a = self.document.xpath('/html/body//div[@class="navlink"]//a[contains(text(), "Suite")]')
        if not a:
            return False
        else:
            return a[0].get('href', '')

    def is_right_aligned_div(self, div_elmt):
        """
            Returns True if the given div element is right-aligned
        """
        return(re.match('.*text-align: ?right.*', div_elmt.get('style', '')))

    def extract_text(self, xml_elmt):
        """
            Given an XML element, returns its inner text in a reasonably readable way
        """
        data = u''
        for text in xml_elmt.itertext():
            data = data + u'%s ' % text
        data = re.sub(' +', ' ', data.replace("\n", ' ').strip())
        return data

    def get_history(self, start_index = 0):
        """
            Returns the history of a specific account. Note that this function
            expects the current page page to be the one dedicated to this history.
        """
        # tested on CA Lorraine, Paris, Toulouse
        # avoir parsing the page as an account-dedicated page if it is not the case
        if not self.is_account_page():
            return

        index = start_index
        operation = False

        body_elmt_list = self.document.xpath('/html/body/*')

        # type of separator used in the page
        separators = 'hr'
        # How many <hr> elements do we have under the <body>?
        sep_expected = len(self.document.xpath('/html/body/hr'))
        if (not sep_expected):
            # no <hr>? Then how many class-less <div> used as separators instead?
            sep_expected = len(self.document.xpath('/html/body/div[not(@class) and not(@style)]'))
            separators = 'div'

        # the interesting divs are after the <hr> elements
        interesting_divs = []
        right_div_count = 0
        left_div_count = 0
        sep_found = 0
        for body_elmt in body_elmt_list:
            if (separators == 'hr' and body_elmt.tag == 'hr'):
                sep_found += 1
            elif (separators == 'div' and body_elmt.tag == 'div' and body_elmt.get('class', 'nope') == 'nope'):
                sep_found += 1
            elif (sep_found >= sep_expected and body_elmt.tag == 'div'):
                # we just want <div> with dv class and a style attribute
                if (body_elmt.get('class', '') != 'dv'):
                    continue
                if (body_elmt.get('style', 'nope') == 'nope'):
                    continue
                interesting_divs.append(body_elmt)
                if (self.is_right_aligned_div(body_elmt)):
                    right_div_count += 1
                else:
                    left_div_count += 1

        # So, how are data laid out?
        toulouse_way_of_life = (left_div_count == 2 * right_div_count)
        # we'll have: one left-aligned div for the date, one right-aligned
        # div for the amount, and one left-aligned div for the label. Each time.

        if (not toulouse_way_of_life):
            for body_elmt in interesting_divs:
                if (self.is_right_aligned_div(body_elmt)):
                    # this is the second line of an operation entry, displaying the amount
                    data = self.extract_text(body_elmt).replace(',', '.').replace(' ', '')
                    matches = re.findall('^(-?[0-9]+\.[0-9]{2}).*$', data)
                    operation.amount = float(matches[0]) if (matches) else 0.0
                    yield operation
                else:
                    # this is the first line of an operation entry, displaying the date and label
                    data = self.extract_text(body_elmt)
                    matches = re.findall('^([012][0-9]|3[01])/(0[1-9]|1[012]).(.+)$', data)
                    operation = Operation(index)
                    index += 1
                    if (matches):
                        operation.date  = u'%s/%s' % (matches[0][0], matches[0][1])
                        operation.label = u'%s'    % matches[0][2]
                    else:
                        operation.date  = u'01/01'
                        operation.label = u'Unknown'
        else:
            for i in range(0, len(interesting_divs)/3):
                operation = Operation(index)
                index += 1
                # amount
                data = self.extract_text(interesting_divs[(i*3)+1]).replace(',', '.').replace(' ', '')
                matches = re.findall('^(-?[0-9]+\.[0-9]{2}).*$', data)
                operation.amount = float(matches[0]) if (matches) else 0.0
                # date
                data = self.extract_text(interesting_divs[i*3])
                matches = re.findall('^([012][0-9]|3[01])/(0[1-9]|1[012])', data)
                operation.date = u'%s/%s' % (matches[0][0], matches[0][1]) if (matches) else u'01/01'
                #label
                data = self.extract_text(interesting_divs[(i*3)+2])
                data = re.sub(' +', ' ', data)
                operation.label = u'%s' % data
                yield operation
