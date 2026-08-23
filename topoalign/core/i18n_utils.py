# -*- coding: utf-8 -*-
"""
Internationalization (i18n) utilities for TopoALign.
Supports English (en) and Portuguese (pt-BR / pt).
Integrates seamlessly with Qt's QTranslator while providing standalone fallback support.
"""

import os
from typing import Optional

try:
    from qgis.PyQt.QtCore import QCoreApplication, QSettings, QLocale
    HAS_QT = True
except ImportError:
    HAS_QT = False

# Portuguese (pt / pt-BR) translation dictionary
TRANSLATIONS_PT = {
    # Plugin & Provider
    "TopoALign": "TopoALign",
    "Topographic alignment and coordinate transformation tools": "Ferramentas de alinhamento topográfico e transformação de coordenadas",

    # Section / Group Names
    "Best Fit": "Melhor Ajuste",
    "Transform": "Transformar",

    # Best Fit Selection Algorithm
    "Best Fit Line (All/Selection)": "Linha de Melhor Ajuste (Tudo/Seleção)",
    "Estimates a best fitting line using Total Least Squares for a set of points.": "Estima uma linha de melhor ajuste usando Mínimos Quadrados Totais (TLS) para um conjunto de pontos.",
    "Input Point Layer": "Camada de Pontos de Entrada",
    "Global Standard Error (Sigma)": "Erro Padrão Global (Sigma)",
    "Sigma X Field (Overrides Global)": "Campo Sigma X (Sobrescreve Global)",
    "Sigma Y Field (Overrides Global)": "Campo Sigma Y (Sobrescreve Global)",
    "Best Fit Line": "Linha de Melhor Ajuste",
    "Points with Residuals": "Pontos com Resíduos",
    "Less than 2 points provided. Skipping line generation.": "Menos de 2 pontos fornecidos. Ignorando a geração de linha.",
    "Warning: The provided points are less than 1mm apart. The calculated line may be unstable.": "Aviso: Os pontos fornecidos estão a menos de 1mm de distância. A linha calculada pode ficar instável.",
    "Could not calculate TLS (not enough valid points).": "Não foi possível calcular o ajuste TLS (pontos válidos insuficientes).",

    # Best Fit Attribute Algorithm
    "Best Fit Lines (By Attribute)": "Linhas de Melhor Ajuste (Por Atributo)",
    "Estimates best fitting lines grouped by an attribute using Total Least Squares.": "Estima linhas de melhor ajuste agrupadas por um atributo usando Mínimos Quadrados Totais (TLS).",
    "Grouping Field": "Campo de Agrupamento",
    "Best Fit Lines": "Linhas de Melhor Ajuste",
    "Invalid or missing Grouping Field.": "Campo de agrupamento inválido ou ausente.",
    "Auto-detected grouping field: {field}": "Campo de agrupamento detectado automaticamente: {field}",
    "Group '{group}' has less than 2 points. Skipping.": "O grupo '{group}' possui menos de 2 pontos. Ignorando.",
    "Warning: Group '{group}' points are less than 1mm apart. Line may be unstable.": "Aviso: Os pontos do grupo '{group}' estão a menos de 1mm de distância. A linha pode ficar instável.",

    # 2D Helmert Transformation Algorithm
    "2D Helmert Transformation": "Transformação 2D de Helmert",
    "Estimates 4-parameter conformal transformation (Tx, Ty, Scale, Rotation) and transforms layer coordinates.": "Estima a transformação conforme de 4 parâmetros (Tx, Ty, Escala, Rotação) e transforma as coordenadas da camada.",
    "Source Layer (To Transform)": "Camada de Origem (Para Transformar)",
    "Source Control Points": "Pontos de Controle de Origem",
    "Source Point ID Field": "Campo ID dos Pontos de Origem",
    "Target Control Points": "Pontos de Controle de Destino",
    "Target Point ID Field": "Campo ID dos Pontos de Destino",
    "Manual Tx (Translation X)": "Tx Manual (Translação X)",
    "Manual Ty (Translation Y)": "Ty Manual (Translação Y)",
    "Manual Scale Factor (s)": "Fator de Escala Manual (s)",
    "Manual Rotation (degrees)": "Rotação Manual (graus)",
    "Use Manual Parameters": "Usar Parâmetros Manuais",
    "Transformed Layer": "Camada Transformada",
    "Residuals / Control Point Errors": "Resíduos / Erros dos Pontos de Controle",
    "At least 2 common control points are required for 2D Helmert transformation.": "Pelo menos 2 pontos de controle correspondentes são necessários para a transformação 2D de Helmert.",
    "Helmert 2D Transformation calculated successfully: Tx={tx:.4f}, Ty={ty:.4f}, Scale={scale:.6f}, Rotation={rot_deg:.4f}°, RMSE={rmse:.4f}": "Transformação 2D de Helmert calculada com sucesso: Tx={tx:.4f}, Ty={ty:.4f}, Escala={scale:.6f}, Rotação={rot_deg:.4f}°, RMSE={rmse:.4f}",

    # Station and Offset Algorithm
    "Station and Offset (Alignment Transformation)": "Estaqueamento e Afastamento (Transformação de Alinhamento)",
    "Projects points onto a reference alignment line to compute chainage (station) and transverse offset.": "Projeta pontos sobre um alinhamento de referência para calcular o estaqueamento (estaca/progressiva) e afastamento transversal.",
    "Reference Alignment (Line Layer)": "Alinhamento de Referência (Camada de Linha)",
    "Station Interval (e.g. 20m for 20m stations)": "Intervalo da Estaca (ex: 20m para estacas de 20m)",
    "Start Station Value (m)": "Valor da Estaca Inicial (m)",
    "Points with Station and Offset": "Pontos com Estaca e Afastamento",
    "Projected Points on Alignment": "Pontos Projetados no Alinhamento",
    "Reference alignment layer has no valid line geometries.": "A camada de alinhamento de referência não possui geometrias de linha válidas.",
}

_CURRENT_OVERRIDE_LOCALE: Optional[str] = None


def set_override_locale(locale_code: Optional[str]):
    """Sets a locale override for testing or manual configuration (e.g. 'pt_BR', 'pt', 'en')."""
    global _CURRENT_OVERRIDE_LOCALE
    _CURRENT_OVERRIDE_LOCALE = locale_code


def get_current_locale() -> str:
    """Detects active locale: override -> QGIS settings -> system locale -> default 'en'."""
    global _CURRENT_OVERRIDE_LOCALE
    if _CURRENT_OVERRIDE_LOCALE:
        return _CURRENT_OVERRIDE_LOCALE

    if HAS_QT:
        try:
            settings = QSettings()
            if settings.value("locale/overrideFlag", False, type=bool):
                loc = settings.value("locale/userLocale", "")
                if loc:
                    return str(loc)
            return QLocale.system().name()
        except Exception:
            pass

    return os.environ.get("LANG", "en")


def tr(text: str, context: str = "TopoALign") -> str:
    """
    Translates text to the active language.
    Uses Qt QCoreApplication.translate when available, falling back to built-in dictionaries.
    """
    if HAS_QT:
        try:
            translated = QCoreApplication.translate(context, text)
            if translated and translated != text:
                return translated
        except Exception:
            pass

    loc = get_current_locale().lower()
    if loc.startswith("pt"):
        return TRANSLATIONS_PT.get(text, text)

    return text
