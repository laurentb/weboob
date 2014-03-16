# -*- coding: utf-8 -*-
from weboob.tools.test import BackendTest

__all__ = ['LaCentraleTest']

class LaCentraleTest(BackendTest):
    BACKEND = 'lacentrale'

    def test_lacentrale(self):
        products = list(self.backend.search_products('1000€,pro'))
        self.assertTrue(len(products) > 0)

        product = products[0]
        prices = list(self.backend.iter_prices(product))
        self.assertTrue(len(prices) > 0)
