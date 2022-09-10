# -*- coding: utf-8 -*-
"""This module manages the plugin's assets (JS, CSS files, and templates).

The module is plugin agnostic: it contains generic mechanisms for updating
relevant assets.
"""
# Media refers to static JS and CSS files.
import os.path
import pathlib
import re
from typing import Callable, List, Optional, Protocol, Union

from anki.media import MediaManager  # type: ignore
from aqt import mw  # type: ignore

# This list contains the intended public API of this module.
__all__ = [
    'AssetManager',
    'AnkiAssetManager',
    'sync_assets',
]


class AssetManager(Protocol):

    def has_newer_version(self) -> bool:
        return False

    def install_assets(self) -> None:
        return None

    def delete_assets(self) -> None:
        return None


class AnkiAssetManager:

    def __init__(self, modify_templates: Callable[[Callable[[str], str]],
                                                  None], media: MediaManager,
                 asset_prefix: str, css_assets: List[str],
                 js_assets: List[str], version_asset: str, class_name: str):
        """
        :param modify_templates Callable[[Callable[[str], str]],
                                                          None]:
            A function that can modify card templates.
        :param media anki.media.MediaManager: The active Anki media manager.
        :param asset_prefix str: The prefix used for this plugin's assets.
        :param css_assets List[str]: All CSS files used by this plugin.
        :param js_assets List[str]: All JS files to be imported by this plugin.
        :param version_asset str: The version asset filename.
        :param class_name str: The unique HTML class name that this manager can
            use to identify its HTML elements.
        """
        self.modify_templates = modify_templates
        self.media = media
        self.asset_prefix = asset_prefix
        self.css_assets = css_assets
        self.js_assets = js_assets
        self.version_asset = version_asset
        self.class_name = class_name

    def has_newer_version(self) -> bool:
        new_version = read_asset_version(assets_directory() /
                                         self.version_asset)
        old_version = read_asset_version(
            anki_media_directory(self.media) / self.version_asset)
        if new_version is None:
            return False
        elif old_version is None or new_version > old_version:
            return True
        else:
            return False

    def install_assets(self) -> None:
        install_media_assets(self.asset_prefix, self.media)
        configure_cards(self.modify_templates,
                        css_assets=self.css_assets,
                        js_assets=self.js_assets,
                        class_name=self.class_name)

    def delete_assets(self) -> None:
        clear_cards(self.modify_templates, class_name=self.class_name)
        delete_media_assets(self.asset_prefix, self.media)


addon_path = os.path.dirname(__file__)


def read_asset_version(asset_version_path: pathlib.Path) -> Optional[int]:
    """Reads the integer representing the asset version from the file."""
    try:
        with open(asset_version_path, 'r') as f:
            return int(f.read())
    except:
        return None


def assets_directory() -> pathlib.Path:
    return pathlib.Path(addon_path) / 'assets'


def anki_media_directory(media: MediaManager) -> pathlib.Path:
    return pathlib.Path(media.dir())


def list_files_with_prefix(dir: pathlib.Path, asset_prefix: str) -> List[str]:
    return [f for f in os.listdir(dir) if f.startswith(asset_prefix)]


def install_media_assets(asset_prefix: str, media: MediaManager) -> None:
    assets_dir = assets_directory()
    my_assets = list_files_with_prefix(assets_dir, asset_prefix)
    for asset in my_assets:
        media.add_file(str(assets_dir / asset))


def delete_media_assets(asset_prefix: str, media: MediaManager) -> None:
    """Deletes all media assets whose filenames starts with `asset_prefix`"""
    my_assets = list_files_with_prefix(anki_media_directory(media),
                                       asset_prefix)
    media.trash_files(my_assets)


def configure_cards(modify_templates: Callable[[Callable[[str], str]],
                                               None], css_assets: List[str],
                    js_assets: List[str], class_name: str) -> None:

    IMPORT_STATEMENTS = (''.join([
        f'<link rel="stylesheet" href="{css_asset}" class="{class_name}">\n'
        for css_asset in css_assets
    ] + [
        f'<script src="{js_asset}" class="{class_name}"></script>\n'
        for js_asset in js_assets
    ]))

    def append_import_statements(tmpl):
        return tmpl + '\n' + IMPORT_STATEMENTS

    modify_templates(append_import_statements)


def clear_cards(modify_templates: Callable[[Callable[[str], str]], None],
                class_name: str) -> None:

    def delete_import_statements(tmpl):
        return re.sub(f'^<[^>]*class="{class_name}"[^>]*>[^\n]*\n',
                      "",
                      tmpl,
                      flags=re.MULTILINE)

    modify_templates(lambda tmpl: delete_import_statements(tmpl).strip())


def sync_assets(asset_manager: AssetManager) -> None:
    """Checks if assets need updating and updates them."""
    if not asset_manager.has_newer_version():
        return None
    asset_manager.delete_assets()
    asset_manager.install_assets()
