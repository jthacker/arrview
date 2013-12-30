import random

from traits.api import HasTraits, List, Str, Button, Instance
from traitsui.api import ListStrEditor, View, Item


class MyObj(HasTraits):
    name = Str

    def __repr__(self):
        return "MyObj(name=%s)" % self.name

class Demo(HasTraits):
    my_list = List(MyObj)

    add = Button("ADD")
    clear = Button("CLEAR")

    traits_view = \
        View(
            Item('my_list', editor=ListStrEditor()),
            Item('add'),
            Item('clear'),
        )

    def _my_list_default(self):
        return [MyObj(name='Item1'), MyObj(name='Item2')]

    def _add_fired(self):
        new_item = MyObj(name="Item%d" % random.randint(3, 999))
        self.my_list.append(new_item)

    def _clear_fired(self):
        self.my_list = []


class DemoContainer(HasTraits):
    demo = Instance(Demo, Demo())

    view = View(
            Item('demo', style='custom'))

if __name__ == "__main__":
    demoContainer = DemoContainer()
    demoContainer.configure_traits()
