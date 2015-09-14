#!/usr/bin/env python3

import configparser
import os.path
import sys
from subprocess import Popen

from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QSystemTrayIcon, QMenu
from PyQt5.QtGui import QPixmap, QIcon, QKeySequence, QCursor
from PyQt5.QtCore import Qt, QSize
from pygs import QxtGlobalShortcut


class Switcher(QWidget):
    def __init__(self):
        super().__init__()
        
        # Add a tray icon.
        self.tray = SwitcherTrayIcon(self)
        self.tray.show()
        
        # Bind the hotkey.
        self.hotkey = QxtGlobalShortcut()
        self.hotkey.activated.connect(self.toggle)
        
        # (Re)load the switcher.
        self.reload()
        
        # Hide the title bar, keep on top.
        self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowStaysOnTopHint)
        
        # Show the window.
        self.show()
        self.setFocus()
        
    def toggle(self):
        # Toggle the visibility.
        if self.isVisible():
            self.hide()
        else:
            self.show()
            
    def show(self):
        # Show the window.
        super().show()
        
        # Center on the desired screen.
        screen = self.screen
        desktop = QApplication.desktop()
        if screen == 'current':
            screen = desktop.screenNumber(QCursor.pos())
        screenRect = desktop.screenGeometry(int(screen))
        self.move(screenRect.center() - self.rect().center())
        
    def reload(self):
        # Read the config.
        self.load_config()
        
        # Update the hotkey.
        self.hotkey.setShortcut(QKeySequence(self.config['General']['hotkey']))
        
        # Initialize the UI.
        self.init_ui()
        
    def load_config(self):
        # Read the config.
        self.config = configparser.ConfigParser()
        self.config.read('switcher.ini')

        # Get the dimensions.
        self.icon_size = int(self.config['General']['icon_size'])
        self.padding = int(self.config['General']['padding'])
        
        # Get the desired screen.
        self.screen = self.config['General']['screen']
        if self.screen != 'current':
            int(self.screen)
        
        # Parse the switches settings.
        self.switches = []
        for segment in [s for s in self.config.sections() if s != 'General']:
            self.switches.append({
                'position': [int(p) for p in self.config[segment]['position'].split(',', 1)],
                'icon': self.config[segment]['icon'],
                'label': self.config[segment]['label'] or segment,
                'run': self.config[segment]['run'],
            })
        
    def init_ui(self):
        # Calculate dimensions using padding and icon size.
        def dim(x, y):
            return (
                self.padding + (self.padding + self.icon_size) * x,
                self.padding + (self.padding + self.icon_size) * y,
            )
        
        # Size the window.
        width, height = dim(
            max([m['position'][0] for m in self.switches]) + 1,
            max([m['position'][1] for m in self.switches]) + 1
        )
        self.resize(width, height)
        
        # Remove all old buttons.
        for btn in getattr(self, 'buttons', []):
            btn.deleteLater()
        
        # For each of the switches, create an icon.
        self.buttons = []
        icon_size = QSize(self.icon_size, self.icon_size)
        for switch in self.switches:
            # Create the button.
            btn = QPushButton(None, self)
            btn.show()
            self.buttons.append(btn)
            
            # Load the icon.
            icon = QPixmap()
            icon.load(switch['icon'])
            icon = icon.scaled(icon_size, Qt.KeepAspectRatio)
            btn.setIcon(QIcon(icon))
            btn.setIconSize(icon_size)
            btn.setFixedSize(icon_size)
            
            # Set the tool tip.
            btn.setToolTip(switch['label'])

            # Position the button.
            btn.move(*dim(*switch['position']))
            
            # Listen to button clicks.
            btn.clicked.connect(SwitcherRunner(self, switch['run']))
        
    def keyPressEvent(self, e):
        # Hide on escape key.
        if e.key() == Qt.Key_Escape:
            self.hide()
            
        # Reload on R key.
        elif e.key() == Qt.Key_R:
            self.reload()
            
    def closeEvent(self, e):
        # Hide tray menu when the switcher is exited.
        self.tray.hide()
    

class SwitcherTrayIcon(QSystemTrayIcon):
    def __init__(self, switcher):
        # Get the icon.
        icon = QIcon('switcher.ico')
        
        # Initialize the tray icon.
        self.switcher = switcher
        super().__init__(icon, switcher)
        
        # Add a context menu.
        menu = QMenu(switcher)
        self.setContextMenu(menu)
        
        # Show/hide the switcher.
        action = menu.addAction("&Show")
        action.triggered.connect(switcher.show)
        action = menu.addAction("&Hide")
        action.triggered.connect(switcher.hide)
        self.activated.connect(self.toggle_switcher)
        
        # Reload the switcher.
        action = menu.addAction("&Reload")
        action.triggered.connect(switcher.reload)
        
        # Exit the switcher.
        action = menu.addAction("&Exit")
        action.triggered.connect(switcher.close)
        
    def toggle_switcher(self, e):
        # Show/hide the switcher on double click of the tray icon.
        if e == QSystemTrayIcon.DoubleClick:      
            self.switcher.toggle()
            
            
class SwitcherRunner(object):
    def __init__(self, switcher, cmd):
        self.switcher = switcher
        self.cmd = cmd
        
    def __call__(self):
        p = Popen(os.path.normpath(self.cmd))
        p.communicate()
        self.switcher.hide()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    switcher = Switcher()
    sys.exit(app.exec_())