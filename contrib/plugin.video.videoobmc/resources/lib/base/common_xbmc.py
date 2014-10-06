# -*- coding: utf-8 -*-
from __future__ import print_function

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

import urllib
import sys

from traceback import print_exc


def get_addon():
    if hasattr(sys.modules["__main__"], "addon_id"):
        _id = sys.modules["__main__"].addon_id
        return xbmcaddon.Addon(id=_id)


def get_translation(key):
    addon = get_addon()
    if addon:
        return addon.getLocalizedString(int(key))


def get_settings(key):
    addon = get_addon()
    if addon:
        return addon.getSetting(key)


def get_addon_dir():
    addon = get_addon()
    if addon:
        addonDir = addon.getAddonInfo("path")
    else:
        addonDir = xbmc.translatePath("special://profile/addon_data/")

    return addonDir


def display_error(msg):
    xbmc.executebuiltin("XBMC.Notification(%s, %s)" % (get_translation('30200').decode('utf-8'), msg))
    print(msg)
    print_exc(msg)


def display_info(msg):
    xbmc.executebuiltin("XBMC.Notification(%s, %s, 3000, DefaultFolder.png)" % (get_translation('30300').encode('utf-8'),
                                                                                msg.encode('utf-8')))
    #print msg
    print_exc()


def parse_params(param_str):
    param_dic = {}
    # Parameters are on the 3rd arg passed to the script
    param_str = sys.argv[2]
    if len(param_str) > 1:
        param_str = param_str.replace('?', '')

        # Ignore last char if it is a '/'
        if param_str[len(param_str) - 1] == '/':
            param_str = param_str[0:len(param_str) - 2]

        # Processing each parameter splited on  '&'
        for param in param_str.split('&'):
            try:
                # Spliting couple key/value
                key, value = param.split('=')
            except:
                key = param
                value = ''

            key = urllib.unquote_plus(key)
            value = urllib.unquote_plus(value)

            # Filling dictionnary
            param_dic[key] = value

    return param_dic


def ask_user(content, title):
    keyboard = xbmc.Keyboard(content, title)
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():
        return keyboard.getText()
    return ""


def create_param_url(param_dic, quote_plus=False):
    """
    Create an plugin URL based on the key/value passed in a dictionary
    """
    url = sys.argv[0]
    sep = '?'

    try:
        for param in param_dic:
            if quote_plus:
                url = url + sep + urllib.quote_plus(param) + '=' + urllib.quote_plus(param_dic[param])
            else:
                url = "%s%s%s=%s" % (url, sep, param, param_dic[param])

            sep = '&'
    except Exception as msg:
        display_error("create_param_url %s" % msg)
        url = None
    return url


def create_list_item(name, itemInfoType="Video", itemInfoLabels=None, iconimage="DefaultFolder.png",
                     c_items=None, isPlayable=False):
    lstItem = xbmcgui.ListItem(label=name, iconImage=iconimage, thumbnailImage=iconimage)

    if c_items:
        lstItem.addContextMenuItems(c_items, replaceItems=True)

    if itemInfoLabels:
        iLabels = itemInfoLabels
    else:
        iLabels = {"Title": name, }

    lstItem.setInfo(type=itemInfoType, infoLabels=iLabels)
    if isPlayable:
        lstItem.setProperty('IsPlayable', "true")

    return lstItem


def add_menu_item(params={}):
    url = create_param_url(params)
    if params.get('name'):
        if params.get('iconimage'):
            lstItem = create_list_item(params.get('name'), iconimage=params.get('iconimage'))
        else:
            lstItem = create_list_item(params.get('name'))
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=lstItem, isFolder=True)
    else:
        display_error('add_menu_item : Fail to add item to menu')


def add_menu_link(params={}):
    if params.get('name') and params.get('iconimage') and params.get('url') and \
       params.get('itemInfoLabels') and params.get('c_items'):
        url = params.get('url')
        lstItem = create_list_item(params.get('name'), iconimage=params.get('iconimage'),
                                   itemInfoLabels=params.get('itemInfoLabels'), c_items=params.get('c_items'),
                                   isPlayable=True)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=lstItem)
    else:
        display_error('add_menu_link : Fail to add item to menu')


def end_of_directory(update=False):
    xbmcplugin.endOfDirectory(handle=int(sys.argv[1]), succeeded=True, updateListing=update)  # , cacheToDisc=True)
