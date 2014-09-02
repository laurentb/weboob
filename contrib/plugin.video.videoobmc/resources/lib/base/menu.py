# -*- coding: utf-8 -*-
import sys

if hasattr(sys.modules["__main__"], "common_xbmc"):
    common_xbmc = sys.modules["__main__"].common_xbmc
else:
    import common_xbmc


class BaseMenuItem():

    def __init__(self, name, action, iconimage="DefaultFolder.png"):
        self.params = {}
        self.params['name'] = name
        self.params['action'] = action
        self.params['iconimage'] = iconimage

    def get(self, element):
        return self.params[element]

    def add_to_menu(self):
        common_xbmc.add_menu_item(self.params)


class BaseMenuLink(BaseMenuItem):

    def __init__(self, name, url, action, iconimage="DefaultFolder.png"):
        BaseMenuItem.__init__(self, name, action, iconimage)
        self.params["url"] = url

    def createVideoContextMenu(self):
        return ""

    def create_info_labels(self):
        return ""

    def add_to_menu(self):
        self.params["itemInfoLabels"] = self.create_info_labels()
        self.params["c_items"] = self.createVideoContextMenu()
        common_xbmc.add_menu_link(self.params)
