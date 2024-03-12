#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.12 21:00:00                  #
# ================================================== #

import copy
import configparser
import io
import os

from pygpt_net.provider.core.plugin_preset.json_file import JsonFileProvider
from pygpt_net.plugin.base import BasePlugin
from pygpt_net.utils import trans


class Plugins:
    def __init__(self, window):
        """
        Plugins core

        :param window: Window instance
        """
        self.window = window
        self.allowed_types = [
            'audio.input',
            'audio.output',
            'text.input',
            'text.output',
            'vision',
            'schedule'
        ]
        self.plugins = {}
        self.presets = {}  # presets config
        self.provider = JsonFileProvider(window)

    def is_registered(self, id: str) -> bool:
        """
        Check if plugin is registered

        :param id: plugin id
        :return: True if registered
        """
        return id in self.plugins

    def all(self) -> dict:
        """
        Get all plugins

        :return: plugins dict
        """
        return self.plugins

    def get_ids(self) -> list:
        """
        Get all plugins ids

        :return: plugins ids list
        """
        return list(self.plugins.keys())

    def get(self, id: str) -> BasePlugin or None:
        """
        Get plugin by id

        :param id: plugin id
        :return: plugin instance
        """
        if self.is_registered(id):
            return self.plugins[id]
        return None

    def get_option(self, id: str, key: str) -> any:
        """
        Get plugin option

        :param id: plugin id
        :param key: option key
        :return: option value
        """
        if self.is_registered(id):
            if key in self.plugins[id].options:
                return self.plugins[id].options[key]['value']
        return None

    def register(self, plugin: BasePlugin):
        """
        Register plugin

        :param plugin: plugin instance
        """
        plugin.attach(self.window)
        id = plugin.id
        self.plugins[id] = plugin

        # make copy of options
        if hasattr(plugin, 'options'):
            self.plugins[id].initial_options = copy.deepcopy(plugin.options)

        try:
            removed = False
            plugins = self.window.core.config.get('plugins')
            if id in list(plugins.keys()):
                for key in list(plugins[id].keys()):
                    if key in self.plugins[id].options:
                        self.plugins[id].options[key]['value'] = plugins[id][key]
                    else:
                        removed = True
                        del plugins[id][key]

            # remove invalid options
            if removed:
                self.window.core.config.save()

            # register options (configure dict editors, etc.)
            self.register_options(id, self.plugins[id].options)
            # print("Loaded plugin: {}".format(plugin.name))
        except Exception as e:
            self.window.core.debug.log(e)
            print('Error while loading plugin options: {}'.format(id))

    def apply_all_options(self):
        """Apply all options to plugins"""
        removed = False
        user_config = self.window.core.config.get('plugins')
        for id in self.plugins:
            if hasattr(self.plugins[id], 'initial_options'):
                self.plugins[id].options = copy.deepcopy(self.plugins[id].initial_options)  # copy
            if id in user_config:
                for key in user_config[id]:
                    if key in self.plugins[id].options:
                        self.plugins[id].options[key]['value'] = user_config[id][key]
                    else:
                        print("removed")
                        removed = True
                        del user_config[id][key]
        if removed:
            self.window.core.config.save()

    def register_options(self, id: str, options: dict):
        """
        Register plugin options

        :param id: plugin id
        :param options: options dict
        """
        dict_types = ["dict", "cmd"]
        for key in options:
            option = options[key]
            if 'type' in option and option['type'] in dict_types:
                key_name = key
                if option['type'] == "cmd":
                    key_name = key + ".params"
                parent = "plugin." + id
                option['label'] = key_name  # option name
                self.window.ui.dialogs.register_dictionary(key_name, parent, option)

    def unregister(self, id: str):
        """
        Unregister plugin

        :param id: plugin id
        """
        if self.is_registered(id):
            self.plugins.pop(id)

    def enable(self, id: str):
        """
        Enable plugin

        :param id: plugin id
        """
        if self.is_registered(id):
            self.plugins[id].enabled = True
            self.window.core.config.data['plugins_enabled'][id] = True
            self.window.core.config.save()

    def disable(self, id: str):
        """
        Disable plugin

        :param id: plugin id
        """
        if self.is_registered(id):
            self.plugins[id].enabled = False
            self.window.core.config.data['plugins_enabled'][id] = False
            self.window.core.config.save()

    def destroy(self, id: str):
        """
        Destroy plugin workers (send stop signal)

        :param id: plugin id
        """
        if self.is_registered(id):
            self.plugins[id].destroy()

    def has_options(self, id: str) -> bool:
        """
        Check if plugin has options

        :param id: plugin id
        :return: True if has options
        """
        if self.is_registered(id):
            return hasattr(self.plugins[id], 'options') and len(self.plugins[id].options) > 0
        return False

    def restore_options(self, id: str):
        """
        Restore options to initial values

        :param id: plugin id
        """
        options = []
        values = {}
        for key in self.plugins[id].options:
            if 'persist' in self.plugins[id].options[key] and self.plugins[id].options[key]['persist']:
                options.append(key)

        # store persisted values
        for key in options:
            values[key] = self.plugins[id].options[key]['value']

        # restore initial values
        if id in self.plugins:
            if hasattr(self.plugins[id], 'initial_options'):
                self.plugins[id].options = copy.deepcopy(self.plugins[id].initial_options)  # copy

        # restore persisted values
        for key in options:
            self.plugins[id].options[key]['value'] = values[key]

    def get_name(self, id: str) -> str:
        """
        Get plugin name (translated)

        :param id: plugin id
        :return: plugin name
        """
        plugin = self.get(id)
        default = plugin.name
        trans_key = 'plugin.' + id
        name = trans(trans_key)
        if name == trans_key:
            name = default
        if plugin.use_locale:
            domain = 'plugin.{}'.format(id)
            name = trans('plugin.name', domain=domain)
        return name

    def get_desc(self, id: str) -> str:
        """
        Get description (translated)

        :param id: plugin id
        :return: plugin description
        """
        plugin = self.get(id)
        default = plugin.description
        trans_key = 'plugin.' + id + '.description'
        tooltip = trans(trans_key)
        if tooltip == trans_key:
            tooltip = default
        if plugin.use_locale:
            domain = 'plugin.{}'.format(id)
            tooltip = trans('plugin.description', domain=domain)
        return tooltip

    def dump_locale(self, plugin, path: str):
        """
        Dump locale

        :param plugin: plugin
        :param path: path to locale file
        """
        options = {}
        options['plugin.name'] = plugin.name
        options['plugin.description'] = plugin.description

        sorted_keys = sorted(plugin.options.keys())
        for key in sorted_keys:
            option = plugin.options[key]
            if 'label' in option:
                option_key = key + '.label'
                options[option_key] = option['label']
            if 'description' in option:
                option_key = key + '.description'
                options[option_key] = option['description']
            if 'tooltip' in option and option['tooltip'] is not None and option['tooltip'] != '':
                option_key = key + '.tooltip'
                options[option_key] = option['tooltip']

        # dump options to .ini file:
        ini = configparser.ConfigParser()
        ini['LOCALE'] = options

        # save with utf-8 encoding
        with io.open(path, mode="w", encoding="utf-8") as f:
            ini.write(f)

    def has_preset(self, id: str) -> bool:
        """
        Check if preset exists

        :param id: preset id
        :return: True if preset exists
        """
        return id in self.presets

    def get_preset(self, id: str) -> dict:
        """
        Get preset by id

        :param id: preset id
        :return: preset dict
        """
        if self.has_preset(id):
            return self.presets[id]

    def set_preset(self, id: str, preset: dict):
        """
        Set config value

        :param id: id
        :param preset: preset
        """
        self.presets[id] = preset

    def replace_presets(self, presets: dict):
        """
        Replace presets

        :param presets: presets dict
        """
        self.presets = presets

    def load_presets(self):
        """Load presets"""
        self.presets = self.provider.load()

    def get_presets(self) -> dict:
        """
        Return all presets

        :return: dict with presets
        """
        return self.presets

    def reset_options(self, plugin_id: str, keys: list):
        """
        Reset plugin options

        :param plugin_id: plugin id
        :param keys: list of keys
        """
        updated = False
        user_config = self.window.core.config.get('plugins')
        if plugin_id in user_config:
            for key in keys:
                if key in user_config[plugin_id]:
                    del user_config[plugin_id][key]
                self.remove_preset_values(plugin_id, key)
                updated = True

        if updated:
            print("[FIX] Updated options for plugin: {}".format(plugin_id))
            self.window.core.config.save()


    def clean_presets(self):
        """Remove invalid options from presets"""
        if self.presets is None:
            self.load_presets()

        removed = False
        if self.presets is not None:
            for id in self.presets:
                preset = self.presets[id]
                for config_preset in preset["config"]:
                    for key in list(preset["config"][config_preset]):
                        if config_preset in self.plugins:
                            if key not in self.plugins[config_preset].options:
                                removed = True
                                preset["config"][config_preset].pop(key)
        if removed:
            self.save_presets()
            print("[FIX] Removed invalid keys from plugin presets.")

    def remove_preset_values(self, plugin_id:str, key: str):
        """
        Update preset value

        :param plugin_id: plugin id
        :param key: key
        """
        updated = False
        if self.presets is None:
            self.load_presets()

        if self.presets is None:
            return
        for id in self.presets:
            preset = self.presets[id]
            for config_preset in preset["config"]:
                if config_preset == plugin_id:
                    if key in preset["config"][config_preset]:
                        preset["config"][config_preset].pop(key)
                        updated = True
        if updated:
            self.save_presets()

    def update_preset_values(self, plugin_id:str, key: str, value: any):
        """
        Update preset value

        :param plugin_id: plugin id
        :param key: key
        :param value: value
        """
        updated = False
        if self.presets is None:
            self.load_presets()

        if self.presets is None:
            return
        for id in self.presets:
            preset = self.presets[id]
            for config_preset in preset["config"]:
                if config_preset == plugin_id:
                    if key in preset["config"][config_preset]:
                        preset["config"][config_preset][key] = value
                        updated = True
        if updated:
            self.save_presets()


    def save_presets(self):
        """Save presets"""
        self.provider.save(self.presets)

    def dump_locale_by_id(self, id: str, path: str):
        """
        Dump locale by id

        :param id: plugin id
        :param path: path to locale file
        """
        if id in self.plugins:
            self.dump_locale(self.plugins[id], path)

    def dump_locales(self):
        """
        Dump all locales
        """
        langs = ['en', 'pl']
        for id in self.plugins:
            domain = 'plugin.' + id
            for lang in langs:
                path = os.path.join(
                    self.window.core.config.get_app_path(),
                    'data',
                    'locale',
                    domain + '.' + lang + '.ini'
                )
                self.dump_locale(self.plugins[id], str(path))
