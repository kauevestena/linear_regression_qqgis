# -*- coding: utf-8 -*-

def classFactory(iface):
    from .plugin import TopoALignPlugin
    return TopoALignPlugin(iface)

