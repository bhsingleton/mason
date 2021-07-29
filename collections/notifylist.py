import weakref

from collections.abc import MutableSequence
from .weakreflist import WeakRefList

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class NotifyList(MutableSequence):
    """
    Overload of MutableSequence used to provide callback mechanisms for any list changes.
    """

    __slots__ = ('__items__', '__callbacks__')

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.
        """

        # Call parent method
        #
        super(NotifyList, self).__init__()

        # Declare private variables
        #
        self.__items__ = kwargs.get('cls', list).__call__()
        self.__callbacks__ = {'itemAdded': WeakRefList(), 'itemRemoved': WeakRefList(), 'setItemCheck': WeakRefList()}

        # Check for any arguments
        #
        numArgs = len(args)

        if numArgs == 1:

            self.extend(args[0])

    def __getitem__(self, index):
        """
        Private method that returns an indexed item.


        :type index: int
        :rtype: Any
        """

        return self.__items__[index]

    def __setitem__(self, index, value):
        """
        Private method that updates an indexed item.

        :type index: int
        :type value: Any
        :rtype: None
        """

        value = self.setItemCheck(value)

        self.__items__[index] = value
        self.itemAdded(index, value)

    def __delitem__(self, index):
        """
        Private method that removes an indexed item.

        :type index: int
        :rtype: None
        """

        self.pop(index)

    def __iter__(self):
        """
        Private method that returns a generator for this list.

        :rtype: iter
        """

        return iter(self.__items__)

    def __len__(self):
        """
        Private method that evaluates the length of this list.

        :rtype: int
        """

        return len(self.__items__)

    def move(self, index, value):
        """
        Moves an index item to a different index.

        :type index: int
        :type value: Any
        :rtype: None
        """

        currentIndex = self.__items__.index(value)
        self.__items__[currentIndex], self.__items__[index] = self.__items__[index], self.__items__[currentIndex]

    def insert(self, index, value):
        """
        Inserts an item at the specified index.

        :type index: int
        :type value: Any
        :rtype: None
        """

        value = self.setItemCheck(value)

        self.__items__.insert(index, value)
        self.itemAdded(index, value)

    def append(self, value):
        """
        Appends an item at the end of the list.

        :type value: Any
        :rtype: None
        """

        value = self.setItemCheck(value)

        self.__items__.append(value)
        self.itemAdded(self.__len__() - 1, value)

    def appendIfUnique(self, value):
        """
        Appends an item so long as it doesn't already exist.

        :type value: Any
        :rtype: None
        """

        if value not in self:

            self.append(value)

    def extend(self, items):
        """
        Copies the supplied items to the end of this list.

        :type items: list[Any]
        :rtype: None
        """

        for item in items:

            self.append(item)

    def remove(self, child):
        """
        Removes the specified item from this list.

        :type child: Any
        :rtype: None
        """

        self.pop(self.index(child))

    def index(self, value):
        """
        Returns the index for the supplied value.

        :type value: Any
        :rtype: int
        """

        return self.__items__.index(value)

    def pop(self, index):
        """
        Removes the indexed item from this list and returns it.

        :type index: int
        :rtype: FbxObject
        """

        item = self.__items__.pop(index)
        self.itemRemoved(item)

        return item

    def clear(self):
        """
        Removes all items from this list.

        :rtype: None
        """

        self.__items__.clear()

    def callbackNames(self):
        """
        Returns a list of callback names that can be used.

        :rtype: list[str]
        """

        return list(self.__callbacks__.keys())

    def addCallback(self, name, func):
        """
        Appends the supplied function to the specified callback group.

        :type name: str
        :type func: function
        :rtype: None
        """

        # Check if function has already been registered
        #
        callbacks = self.__callbacks__[name]

        if func not in callbacks:

            callbacks.append(func)

    def removeCallback(self, name, func):
        """
        Removes the supplied ID from the specified callback group.

        :type name: str
        :type func: function
        :rtype: None
        """

        # Check if function was registered
        #
        callbacks = self.__callbacks__[name]

        if func in callbacks:

            callbacks.remove(func)

    def itemAdded(self, index, item):
        """
        Notifies any functions if an item has been added.

        :type index: int
        :type item: Any
        :rtype: None
        """

        for func in self.__callbacks__['itemAdded']:

            func(index, item)

    def itemRemoved(self, item):
        """
        Notifies any functions if an item has been removed.

        :type item: Any
        :rtype: None
        """

        for func in self.__callbacks__['itemRemoved']:

            func(item)

    def setItemCheck(self, item):
        """
        Notifies any functions of a set item request.

        :type item: Any
        :rtype: bool
        """

        callbacks = self.__callbacks__['setItemCheck']

        for func in callbacks:

            item = func(item)

        return item
