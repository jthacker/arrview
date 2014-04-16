from PySide.QtCore import Qt, QObject, QEvent as QEV
from PySide.QtGui import QGraphicsView, QWheelEvent

from collections import namedtuple
from .util import Scale, rep, toiterable

_qtmousebuttons = (Qt.LeftButton, Qt.MidButton, Qt.RightButton)
_mouse_events = { QEV.MouseMove, QEV.MouseButtonPress, QEV.MouseButtonRelease,
        QEV.MouseButtonDblClick, QEV.Wheel}
_key_events = {}
_event_map = {
        QEV.MouseMove: lambda o: o.mouse_move_event,
        QEV.MouseButtonPress: lambda o: o.mouse_press_event, 
        QEV.MouseButtonRelease: lambda o: o.mouse_release_event,
        QEV.MouseButtonDblClick: lambda o: o.mouse_double_click_event,
        QEV.Wheel: lambda o: o.mouse_wheel_event }

MouseEvent = namedtuple('MouseEvent',['graphics', 'mouse'])

class MouseState(object):
    def __init__(self, pos, screen_pos, buttons, wheel_delta):
        self.pos = pos
        self.screen_pos = screen_pos
        self.buttons = buttons
        self.wheel_delta = wheel_delta

    def __repr__(self):
        return rep(self, ['screen_pos', 'pos', 'buttons', 'wheel_delta'])


class GraphicsViewEventFilter(QObject):
    def __init__(self, graphicsview, tools=tuple()):
        super(GraphicsViewEventFilter, self).__init__(parent=graphicsview)
        self.graphicsview = graphicsview
        self.tools = []
        for tool,filters in tools:
            self.add_tool(tool, filters)
   
    def add_tool(self, tool, filters):
        if not filter(lambda tf: tf[0]==tool, self.tools) and hasattr(tool, 'attach_event'):
            tool.attach_event(self.graphicsview)
        self.tools.insert(0, (tool, tuple(toiterable(filters))))

    def remove_tool(self, tool):
        tfs = filter(lambda tf: tf[0]==tool, self.tools)
        assert len(tfs) <= 1, 'There should be no duplicates in self.tools'
        if len(tfs) == 1:
            tool,filters = tfs[0]
            if hasattr(tool, 'detach_event'):
                tool.detach_event(self.graphicsview)
            self.tools.remove(tool)

    def convert_mouse_event(self, ev):
        screen_pos = ev.pos()
        pos = self.graphicsview.screen_pos_to_pixmap_pos(screen_pos)
        if isinstance(ev, QWheelEvent):
            delta = ev.delta()
            buttons = frozenset()
        else:
            delta = 0
            buttons = frozenset((b for b in _qtmousebuttons if (ev.buttons() & b) or (ev.button()==b)))
        return MouseState(pos, screen_pos, buttons, delta)

    def eventFilter(self, obj, ev):
        eventtype = ev.type()
        state = None
        event = None
        if eventtype in _mouse_events:
            state = self.convert_mouse_event(ev)
            event = MouseEvent(self.graphicsview, state)
        elif eventtype in _key_events:
            state = self.convert_key_event(ev)
            event = KeyEvent(state)
        if state is None:
            return super(GraphicsViewEventFilter, self).eventFilter(obj, ev)
        return self.filter(eventtype, event, state)

    def filter(self, evtype, event, state):
        '''Return True when the event should not propogate any further'''
        for tool,filters in self.tools:
            for filter in filters:
                if filter.matches(evtype, state):
                    handled = _event_map[evtype](tool)(event)
                    if handled:
                        return True
        return False


class Filter(object):
    def __init__(self, eventtypes, statefilters=tuple()):
        self.eventtypes = tuple(toiterable(eventtypes))
        self.statefilters = statefilters

    def matches(self, evtype, state):
        return evtype in self.eventtypes and all(f(state) for f in self.statefilters)


class MouseFilter(Filter):
    def __init__(self, evtypes, buttons=tuple()):
        statefilters = tuple(lambda state: state.buttons == {b} for b in toiterable(buttons))
        super(MouseFilter, self).__init__(evtypes, statefilters)
