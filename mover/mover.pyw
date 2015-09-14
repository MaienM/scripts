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
        wleft, wright = self.for_axis((axis + 1) % 2, *wrect)
        wright += wleft
        
        # Determine the center of the window.
        # This is used to determine the segment which the window is primarily in.
        center = (wx + ww / 2, wy + wh / 2)
        
        # Determine the monitor rects.
        monitors = [win32api.GetMonitorInfo(m[0])['Work'] for m in win32api.EnumDisplayMonitors()]

        # Determine the segments in line with what you want.
        segments = []
        for mrect in monitors:
            mstart, mend = self.for_axis(axis, *mrect)
            msize = abs(mend - mstart)
            mleft, mright = self.for_axis((axis + 1) % 2, *mrect)
            mright += mleft

            for i, range_ in enumerate(self.ranges):
                sstart = mstart + range_[0] * msize
                ssize = abs(range_[1] - range_[0]) * msize
                segments.append((sstart, ssize, mleft, mright))
        segments.sort(key = lambda s: s[0])
        print(segments)

        # Determine the segments the monitor is currenly covering for at least 80%.
        segments_in = []
        for i, segment in enumerate(segments):
            sstart, ssize, sleft, sright = segment
            if wstart < sstart + 0.1 * ssize and sstart + ssize - 0.1 * ssize < wstart + wsize and \
               wleft < sleft + 0.1 * ssize and sright - 0.1 * ssize < wright + wsize :
                segments_in.append(i)
        print(segments_in)
                    
        # Determine the next segment.
        # If the window is currently in more than one segment, simply move to
        # either the start or the end of the segment, depending on the
        # direction.
        # If the window is in just one segment, move one segment away from that
        # segment in the chosen direction.
        segment_new = None
        if len(segments_in) == 0:
            segment_new = 0
        elif len(segments_in) > 1:
            if direction == self.DIRECTION_PREV:
                segment_new = segments_in[0]
            else:
                segment_new = segments_in[-1]
        else:
            segment_new = (segments_in[0] + direction) % len(segments)
        sstart, ssize, sleft, sright = segments[segment_new]
                
        # Calculate the new rect.
        if axis == self.AXIS_X:
            new_rect = (
                sstart,
                wy,
                sstart + ssize,
                wy + wh,
            )
        elif axis == self.AXIS_Y:
            new_rect = (
                wx,
                sstart,
                wx + ww,
                sstart + ssize,
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
