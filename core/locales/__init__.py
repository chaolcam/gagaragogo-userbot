# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Internationalization (i18n) & JSON-Based Localization Engine
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------

import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger("ggr.i18n")

_LOCALES_DIR = os.path.dirname(os.path.abspath(__file__))
_CURRENT_LANG = os.environ.get("DEFAULT_LANG", "tr").lower()
_STRINGS_CACHE: Dict[str, Dict[str, str]] = {}


def _load_locale(lang_code: str) -> Dict[str, str]:
    """Loads a language dictionary from its corresponding JSON file."""
    if lang_code in _STRINGS_CACHE:
        return _STRINGS_CACHE[lang_code]

    file_path = os.path.join(_LOCALES_DIR, f"{lang_code}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                _STRINGS_CACHE[lang_code] = data
                return data
        except Exception as e:
            logger.error("Error loading locale file %s: %s", file_path, e)

    return {}


def get_available_languages() -> list:
    """Discovers all available language codes based on existing .json files."""
    langs = []
    if os.path.exists(_LOCALES_DIR):
        for fname in os.listdir(_LOCALES_DIR):
            if fname.endswith(".json"):
                langs.append(fname[:-5].lower())
    return langs or ["tr", "en"]


def get_current_lang() -> str:
    """Returns the current active language code ('tr', 'en', etc.)."""
    try:
        from core.database import ayar_getir
        lang = ayar_getir("BOT_LANG", _CURRENT_LANG)
        return lang if lang in get_available_languages() else "tr"
    except Exception:
        return _CURRENT_LANG if _CURRENT_LANG in get_available_languages() else "tr"


def set_current_lang(lang_code: str) -> bool:
    """Sets and persists the active language code."""
    global _CURRENT_LANG
    lang_code = lang_code.lower().strip()
    if lang_code not in get_available_languages():
        return False
    _CURRENT_LANG = lang_code
    try:
        from core.database import ayar_kaydet
        ayar_kaydet("BOT_LANG", lang_code)
    except Exception as e:
        logger.warning("Could not persist language: %s", e)
    return True


def t(key: str, lang: str = None, **kwargs: Any) -> str:
    """
    Translates a key into the given or current language.
    Falls back to Turkish (default) and then English if key not found.
    """
    selected_lang = lang or get_current_lang()
    table = _load_locale(selected_lang)
    text = table.get(key)

    if text is None:
        # Fallback to default (Turkish)
        tr_table = _load_locale("tr")
        text = tr_table.get(key)
        if text is None:
            # Fallback to English
            en_table = _load_locale("en")
            text = en_table.get(key, key)

    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
