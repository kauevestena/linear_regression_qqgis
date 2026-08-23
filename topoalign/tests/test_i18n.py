# -*- coding: utf-8 -*-

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.i18n_utils import tr, set_override_locale, TRANSLATIONS_PT


def test_i18n_fallback_english():
    set_override_locale("en")
    assert tr("Best Fit") == "Best Fit"
    assert tr("Transform") == "Transform"
    assert tr("2D Helmert Transformation") == "2D Helmert Transformation"


def test_i18n_fallback_portuguese():
    set_override_locale("pt_BR")
    assert tr("Best Fit") == "Melhor Ajuste"
    assert tr("Transform") == "Transformar"
    assert tr("2D Helmert Transformation") == "Transformação 2D de Helmert"
    assert tr("Station and Offset (Alignment Transformation)") == "Estaqueamento e Afastamento (Transformação de Alinhamento)"
    assert tr("Best Fit Line (All/Selection)") == "Linha de Melhor Ajuste (Tudo/Seleção)"
    assert tr("Best Fit Lines (By Attribute)") == "Linhas de Melhor Ajuste (Por Atributo)"

    # Reset
    set_override_locale(None)


def test_all_translations_dictionary_complete():
    # Verify all Portuguese entries are non-empty strings
    for k, v in TRANSLATIONS_PT.items():
        assert isinstance(k, str) and len(k) > 0
        assert isinstance(v, str) and len(v) > 0


def test_provider_and_algorithm_groups():
    from topoalign_provider import TopoALignProvider
    from algorithms.bestfit_selection import BestFitSelectionAlgorithm
    from algorithms.bestfit_attribute import BestFitAttributeAlgorithm
    from algorithms.transform_helmert import Helmert2DTransformAlgorithm
    from algorithms.transform_station_offset import StationOffsetAlgorithm

    # Test English
    set_override_locale("en")
    provider = TopoALignProvider()
    assert provider.id() == "topoalign"
    assert provider.name() == "TopoALign"

    bf_sel = BestFitSelectionAlgorithm()
    assert bf_sel.groupId() == "best_fit"
    assert bf_sel.group() == "Best Fit"
    assert bf_sel.name() == "bestfitselection"

    bf_att = BestFitAttributeAlgorithm()
    assert bf_att.groupId() == "best_fit"
    assert bf_att.group() == "Best Fit"
    assert bf_att.name() == "bestfitattribute"

    tr_helm = Helmert2DTransformAlgorithm()
    assert tr_helm.groupId() == "transform"
    assert tr_helm.group() == "Transform"
    assert tr_helm.name() == "helmert2d"

    tr_stat = StationOffsetAlgorithm()
    assert tr_stat.groupId() == "transform"
    assert tr_stat.group() == "Transform"
    assert tr_stat.name() == "stationoffset"

    # Test Portuguese
    set_override_locale("pt_BR")
    assert provider.name() == "TopoALign"
    assert bf_sel.group() == "Melhor Ajuste"
    assert bf_att.group() == "Melhor Ajuste"
    assert tr_helm.group() == "Transformar"
    assert tr_stat.group() == "Transformar"

    set_override_locale(None)


def test_qt_translator_qm_loading():
    from qgis.PyQt.QtCore import QCoreApplication, QTranslator

    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])

    qm_path = os.path.join(os.path.dirname(__file__), '..', 'i18n', 'topoalign_pt_BR.qm')
    assert os.path.exists(qm_path), f"QM file not found at {qm_path}"

    translator = QTranslator()
    loaded = translator.load(os.path.abspath(qm_path))
    assert loaded is True, "Failed to load QTranslator from QM file"

    app.installTranslator(translator)
    translated_group = QCoreApplication.translate('TopoALign', 'Transform')
    assert translated_group == "Transformar"

    translated_best_fit = QCoreApplication.translate('TopoALign', 'Best Fit')
    assert translated_best_fit == "Melhor Ajuste"

    app.removeTranslator(translator)


