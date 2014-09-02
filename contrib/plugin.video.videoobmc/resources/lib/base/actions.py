# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod


class BaseAction():
    __metaclass__ = ABCMeta

    @abstractmethod
    def _do(self, param=None):
        """
        Overload this method in application type subclass
        if you want to associate an action to the menu
        """
        pass

actions = {}
