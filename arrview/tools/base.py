from __future__ import absolute_import

from traits.api import Event, Float, HasTraits, Instance, Int, List, Str, Tuple, WeakRef

import weakref

from arrview.util import rep


class MouseButtons(object):
    def __init__(self, left=False, middle=False, right=False):
        self._left = left
        self._middle = middle
        self._right = right

    @property
    def left(self):
        return self._left and not(self._right or self._middle)

    @property
    def right(self):
        return self._right and not(self._left or self._middle)

    @property
    def middle(self):
        return self._middle and not(self._left or self._right)

    def all(self):
        return self._left and self._middle and self._right

    def none(self):
        return not (self._left or self._middle or self._right)

    def __repr__(self):
        return rep(self, ['left','middle','right'])


class MouseState(HasTraits):
    coords = Tuple(Float, Float, default=(0,0))
    screenCoords = Tuple(Float, Float, default=(0,0))
    delta = Int
    buttons = Instance(MouseButtons, MouseButtons)

    wheeled = Event
    pressed = Event
    released = Event
    moved = Event
    doubleclicked = Event
    entered = Event
    left = Event

    def __repr__(self):
        return rep(self, ['coords','screenCoords', 'delta', 'buttons'])


class GraphicsTool(HasTraits):
    # Only use dynamic notifications in the _init method when setting
    # up listeners. This has to be done because the class isn't fully
    # initialized until it is passed to the graphics view and init is called.
    # This can lead to null pointer exceptions.

    name = Str('DEFAULT_NAME')
    mouse = Instance(MouseState)
    factory = WeakRef('GraphicsToolFactory')

    def __init__(self, factory, graphics, mouse):
        super(GraphicsTool, self).__init__(mouse=mouse, factory=factory)
        self.graphics = weakref.proxy(graphics)
        mouse.on_trait_event(self.mouse_entered, 'entered')
        mouse.on_trait_event(self.mouse_left, 'left')
        mouse.on_trait_event(self.mouse_moved, 'moved')
        mouse.on_trait_event(self.mouse_pressed, 'pressed')
        mouse.on_trait_event(self.mouse_wheeled, 'wheeled')
        mouse.on_trait_event(self.mouse_released, 'released')
        mouse.on_trait_event(self.mouse_double_clicked, 'doubleclicked')
        self.init()

    def init(self):
        pass

    def destroy(self):
        pass

    def mouse_pressed(self):
        pass

    def mouse_moved(self):
        pass

    def mouse_wheeled(self):
        pass

    def mouse_released(self):
        pass

    def mouse_double_clicked(self):
        pass

    def mouse_entered(self):
        pass

    def mouse_left(self):
        pass


class GraphicsToolFactory(HasTraits):
    klass = Instance(GraphicsTool)

    def init_tool(self, graphics, mouse):
        return self.klass(factory=self, graphics=graphics, mouse=mouse)


class ToolSet(HasTraits):
    factories = List(GraphicsToolFactory)

    def __init__(self, **traits):
        super(ToolSet, self).__init__(**traits)
        self._tools = []

    @property
    def tools(self):
        return self._tools

    def init_tools(self, graphics, mouse):
        return [t.init_tool(graphics, mouse) for t in self.factories]
