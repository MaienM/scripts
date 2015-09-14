import sys

import win32api
import win32gui
import ctypes, ctypes.wintypes
from PyQt5.QtWidgets import QApplication, QWidget, QSystemTrayIcon, QMenu
from PyQt5.QtGui import QKeySequence, QIcon
from pygs import QxtGlobalShortcut


class Mover(object):
    AXIS_X = 0
    AXIS_Y = 1
    
    DIRECTION_NEXT = 1
    DIRECTION_PREV = -1

    def __init__(self, *ranges):
        self.ranges = ranges
        
    def prepared(self, axis, direction):
        return lambda: self(axis, direction)
        
    def __call__(self, axis, direction):
        # Get the current window handle.
        window = win32gui.GetForegroundWindow()
        
        # Get the current window rect.
        wrect = win32gui.GetWindowRect(window)
        wx, wy, ww, wh = self.to_dimensions(wrect)
        wstart, wsize = self.for_axis(axis, *wrect)
        
        # Determine the center of the window.
        # This is used to determine the monitor which the window is primarily in.
        center = (wx + ww / 2, wy + wh / 2)
        
        # Determine the current monitor rect.
        for monitor in win32api.EnumDisplayMonitors():
            mrect = win32api.GetMonitorInfo(monitor[0])['Work']
            if self.between(mrect[0], center[0], mrect[2]) and self.between(mrect[1], center[1], mrect[3]):
                break
        mx, my, mw, mh = self.to_dimensions(mrect)
        mstart, msize = self.for_axis(axis, *mrect)
                    
        # Determine which segments are at least 80% covered by the window.
        segments = []
        segment_center = -1
        for i, range in enumerate(self.ranges):
            sstart = mstart + range[0] * msize
            ssize = (range[1] - range[0]) * msize
            if wstart < sstart + 0.1 * ssize and sstart + ssize - 0.1 * ssize < wstart + wsize :
                segments.append(i)
            if self.between(sstart, center[axis], sstart + ssize):
                segment_center = i
                
        # None, so fallback to the segment containing the center of the window.
        if len(segments) == 0:
            segments = [segment_center]
                    
        # Determine the next segment.
        # If the window is currently in more than one segment, simply move to
        # either the start or the end of the segment, depending on the
        # direction.
        # If the window is in just one segment, move one segment away from that segment in the chosen direction.
        if len(segments) > 1:
            if direction == self.DIRECTION_PREV:
                segment = segments[0]
            else:
                segment = segments[-1]
        else:
            segment = (segments[0] + direction) % len(self.ranges)
        new_range = self.ranges[segment]
                
        # Calculate the new rect.
        if axis == self.AXIS_X:
            new_rect = (
                mx + new_range[0] * mw,
                my,
                (new_range[1] - new_range[0]) * mw,
                mh,
            )
        elif axis == self.AXIS_Y:
            new_rect = (
                mx,
                my + new_range[0] * mh,
                mw,
                (new_range[1] - new_range[0]) * mh,
            )
            
        # Set the new window rect.
        args = (window, 0,) + tuple([int(a) for a in new_rect]) + (0,)
        win32gui.SetWindowPos(*args)

    @staticmethod
    def between(a, b, c):
        return a <= b and b <= c
        
    @staticmethod
    def to_dimensions(rect):
        return (rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])

    @staticmethod
    def for_axis(axis, *a):
        return a[axis::2]

        
class MoverWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.hotkeys = {}
        for modifiers, moverargs in MODIFIERS.items():
                for key, args in HOTKEYS.items():
                    keys = modifiers + '+' + key
                    hotkey = self.hotkeys[keys] = QxtGlobalShortcut()
                    hotkey.activated.connect(Mover(*moverargs).prepared(*args))
                    hotkey.setShortcut(QKeySequence(keys))
                    
        self.tray = MoverTrayIcon(self)
        self.tray.show()
            
    def closeEvent(self, e):
        # Hide tray menu when the mover is exited.
        self.tray.hide()
    

class MoverTrayIcon(QSystemTrayIcon):
    def __init__(self, mover):
        # Get the icon.
        icon = QIcon('mover.gif')
        
        # Initialize the tray icon.
        self.mover = mover
        super().__init__(icon, mover)
        
        # Add a context menu.
        menu = QMenu(mover)
        self.setContextMenu(menu)
        
        # Exit the mover.
        action = menu.addAction("&Exit")
        action.triggered.connect(mover.close)
    

MODIFIERS = {
    'Ctrl':             ((0, 0.50), (0.50, 1)),                # 50%
    'Ctrl+Shift':       ((0, 1), (0, 1)),                              # 100%
    'Alt':              ((0, 0.33), (0.33, 0.66), (0.66, 1)),  # 33%
    'Alt+Shift':        ((0, 0.66), (0.33, 1)),                # 66%
}


HOTKEYS = {
    'Up':           (Mover.AXIS_Y, Mover.DIRECTION_PREV),
    'Down':         (Mover.AXIS_Y, Mover.DIRECTION_NEXT),
    'Left':         (Mover.AXIS_X, Mover.DIRECTION_PREV),
    'Right':        (Mover.AXIS_X, Mover.DIRECTION_NEXT),
}

                    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MoverWidget()
    sys.exit(app.exec_())
