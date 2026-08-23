# -*- coding: utf-8 -*-

def classFactory(iface):
    from .plugin import BestFitLinesPlugin
    return BestFitLinesPlugin(iface)
