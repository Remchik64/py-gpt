#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.22 18:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTextEdit, QApplication

from ....utils import trans


class ChatInput(QTextEdit):
    def __init__(self, window=None):
        """
        Chat input

        :param window: main window
        """
        super(ChatInput, self).__init__(window)
        self.window = window
        self.setAcceptRichText(False)
        self.setFocus()
        self.value = self.window.config.data['font_size.input']
        self.max_font_size = 42
        self.min_font_size = 8

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()

        selected_text = self.textCursor().selectedText()
        if selected_text:
            action = menu.addAction(trans('text.context_menu.audio.read'))
            action.triggered.connect(self.audio_read_selection)
        menu.exec_(event.globalPos())

    def audio_read_selection(self):
        """
        Read selected text (audio)
        """
        self.window.controller.output.speech_selected_text(self.textCursor().selectedText())

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(ChatInput, self).keyPressEvent(event)
        self.window.controller.ui.update_tokens()
        if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
            mode = self.window.config.get('send_mode')
            if mode > 0:  # Enter or Shift + Enter
                if mode == 2:  # Shift + Enter
                    modifiers = QApplication.keyboardModifiers()
                    if modifiers == QtCore.Qt.ShiftModifier:
                        self.window.controller.input.user_send()
                else:  # Enter
                    self.window.controller.input.user_send()
                self.setFocus()

    def wheelEvent(self, event):
        """
        Wheel event: set font size
        :param event: Event
        """
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                if self.value < self.max_font_size:
                    self.value += 1
            else:
                if self.value > self.min_font_size:
                    self.value -= 1

            self.window.config.data['font_size.input'] = self.value
            self.window.config.save()
            self.window.controller.settings.update_font_size()
            event.accept()
        else:
            super(ChatInput, self).wheelEvent(event)
