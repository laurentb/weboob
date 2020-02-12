# -*- coding: utf-8 -*-
import sys
import resources.lib.base.common_xbmc as common_xbmc
import resources.lib.constants as constants
from resources.lib.actions import actions

# Plugin constants
version = '2.0'
plugin = "videoobmc" + version
addon_id = "plugin.video.videoobmc"
author = "Bezleputh"
mail = "carton_ben@yahoo.fr"

#import lxml.html import Element
#print Element.__file__

#TODO gestion du logger, gestion des modules via XBMC (activation/desactivation)

#Bug encodge des categories
#corriger version 1 pour que v2 et v1 donctionnent

if (__name__ == "__main__"):
    if not (sys.argv[2]):
        actions[constants.DISPLAY_MENU]()._do()
    else:
        params = common_xbmc.parse_params(sys.argv[2])
        action = params.get("action")
        if (action):
            actions[action]()._do(params)
        else:
            common_xbmc.display_error(" ARGV Nothing done.. verify params " + repr(params))
