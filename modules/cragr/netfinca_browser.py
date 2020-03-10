# -*- coding: utf-8 -*-

# Copyright(C) 2012-2019  Budget Insight

# yapf-compatible

from weboob.browser import AbstractBrowser


class NetfincaBrowser(AbstractBrowser):
    PARENT = 'netfinca'
    BASEURL = 'https://www.cabourse.credit-agricole.fr'
