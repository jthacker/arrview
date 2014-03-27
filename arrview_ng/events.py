from PySide.QtCore import Qt, QObject, QEvent as QEV
from PySide.QtGui import QGraphicsView, QWheelEvent

from .util import Scale, rep, QPointFTuple, QPointTuple, toiterable


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


class MouseState(object):
    def __init__(self, pos, screen_pos, buttons, wheel_delta):
        self.pos = pos
        self.screen_pos = screen_pos
        self.buttons = buttons
        self.wheel_delta = wheel_delta

    def __repr__(self):
        return rep(self, ['screen_pos', 'pos', 'buttons', 'wheel_delta'])


class GraphicsViewEventFilter(QObject):
    def __init__(self, graphicsview, tools=None):
        super(GraphicsViewEventFilter, self).__init__(parent=graphicsview)
        self.graphicsview = graphicsview
        for tool in tools.iterkeys():
            if hasattr(tool, 'attach_event'):
                tool.attach_event(graphicsview)
        self.tools = { tool:tuple(toiterable(filters)) for tool,filters in tools.iteritems() }
        
    def convert_mouse_event(self, ev):
        screen_pos = QPointTuple(ev.pos())
        pos = QPointFTuple(self.graphicsview.screen_pos_to_pixmap_pos(screen_pos))
        buttons = frozenset((b for b in _qtmousebuttons if ev.buttons() & b))
        delta = 0 if not isinstance(ev, QWheelEvent) else ev.delta()
        return MouseState(pos, screen_pos, buttons, delta)

    def filter(self, evtype, state):
        '''Return True when the event should not propogate any further'''
        for tool,filters in self.tools.iteritems():
            for filter in filters:
                if filter.matches(evtype, state):
                    handled = _event_map[evtype](tool)(self.graphicsview, state)
                    return True
        return False

    def eventFilter(self, obj, ev):
        eventtype = ev.type()
        state = None
        if eventtype in _mouse_events:
            state = self.convert_mouse_event(ev)
        elif eventtype in _key_events:
            state = self.convert_key_event(ev)

        if state is None:
            return super(GraphicsViewEventFilter, self).eventFilter(obj, ev)

        return self.filter(eventtype, state)


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
