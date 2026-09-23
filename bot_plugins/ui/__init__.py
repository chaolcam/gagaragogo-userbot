# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: UI Component Package Init
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
from bot_plugins.ui.common import check_update_status, make_progress_bar, format_sure, safe_edit
from bot_plugins.ui.help_menu import (
    get_main_menu_text,
    get_main_menu_keyboard,
    get_settings_keyboard,
    get_detailed_status_content,
    get_category_keyboard,
    get_araclar_hub_content,
    handle_yardim_close,
    handle_main_and_settings,
    handle_btn_update,
    handle_sub_callbacks,
    handle_kat_and_cmd,
)
from bot_plugins.ui.broadcast_ui import (
    get_ilet_hub_content,
    get_ilet_anlik_content,
    get_ilet_otomesaj_content,
    build_ilet_menu_keyboard,
    build_otomesaj_list_keyboard,
    build_otomesaj_detail_keyboard,
    handle_ilet_callbacks,
    handle_otomsg_callbacks,
)
from bot_plugins.ui.contacts_ui import (
    build_rehber_menu_main,
    build_rehber_menu_groups,
    build_rehber_menu_counts,
    handle_rehber_callbacks,
)
from bot_plugins.ui.plugin_store_ui import (
    build_eklenti_ana_menu_keyboard,
    build_eklenti_magaza_keyboard,
    handle_eklenti_callbacks,
)
from bot_plugins.ui.instagram_ui import handle_ig_callbacks

__all__ = [
    "check_update_status",
    "make_progress_bar",
    "format_sure",
    "safe_edit",
    "get_main_menu_text",
    "get_main_menu_keyboard",
    "get_settings_keyboard",
    "get_detailed_status_content",
    "get_category_keyboard",
    "get_araclar_hub_content",
    "handle_yardim_close",
    "handle_main_and_settings",
    "handle_btn_update",
    "handle_sub_callbacks",
    "handle_kat_and_cmd",
    "get_ilet_hub_content",
    "get_ilet_anlik_content",
    "get_ilet_otomesaj_content",
    "build_ilet_menu_keyboard",
    "build_otomesaj_list_keyboard",
    "build_otomesaj_detail_keyboard",
    "handle_ilet_callbacks",
    "handle_otomsg_callbacks",
    "build_rehber_menu_main",
    "build_rehber_menu_groups",
    "build_rehber_menu_counts",
    "handle_rehber_callbacks",
    "build_eklenti_ana_menu_keyboard",
    "build_eklenti_magaza_keyboard",
    "handle_eklenti_callbacks",
    "handle_ig_callbacks",
]
