from collections.abc import MutableSequence

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class SparseArray(MutableSequence):
    """
    Overload of MutableMapping used as a sparse array container.
    """

    __slots__ = ('__items__',)

    def __init__(self):
        """
        Private method called after a new instance has been created.
        """

        # Call parent method
        #
        super(SparseArray, self).__init__()

        # Declare class variables
        #
        self.__items__ = {}

    def __str__(self):
        """
        Private method that returns a string representation of this instance.

        :rtype: str
        """

        return str(self.toList())

    def __getitem__(self, index):
        """
        Private method that returns either an indexed child.

        :type index: int
        :rtype: object
        """

        # Check index sign
        #
        if 0 <= index < self.__len__():

            return self.__items__.get(index, None)

        else:

            return self.toList()[index]

    def __setitem__(self, index, item):
        """
        Private method that updates an indexed child.

        :type index: int
        :type item: object
        :rtype: None
        """

        self.__items__[index] = item

    def __delitem__(self, index):
        """
        Private method that deletes an indexed child.

        :type index: int
        :rtype: None
        """

        del self.__items__[index]

    def __contains__(self, item):
        """
        Private method that evaluates if the supplied item is in this array.

        :type item: object
        :rtype: bool
        """

        return item in self.__items__.values()

    def __iter__(self):
        """
        Private method that returns a generator for this object.

        :rtype: iter
        """

        return iter(self.__items__.values())

    def __len__(self):
        """
        Private method that evaluates the number of children belonging to this object.

        :rtype: int
        """

        return len(self.__items__)

    def insert(self, index, item):
        """
        Inserts an item at the specified index.

        :type index: int
        :type item: object
        :rtype: None
        """

        self.__setitem__(index, item)

    def append(self, item):
        """
        Appends an item to the end of this array.

        :type item: object
        :rtype: None
        """

        self.insert(self.__len__(), item)

    def appendIfUnique(self, item):
        """
        Appends an items to the end of this array only if it doesn't exist.

        :type item: object
        :rtype: None
        """

        if item not in self:

            self.insert(self.__len__(), item)

    def extend(self, items):
        """
        Appends the supplied items onto this array.

        :type items: list
        :rtype: None
        """

        for item in items:

            self.append(item)

    def remove(self, item):
        """
        Removes the supplied item from this array.

        :type item: object
        :rtype: None
        """

        del self.__items__[self.index(item)]

    def clear(self):
        """
        Removes all items from this array.

        :rtype: None
        """

        self.__items__.clear()

    def index(self, item):
        """
        Returns the index the supplied item is located at.

        :type item: object
        :rtype: int
        """

        return self.toList(item).index(item)

    def get(self, index, default=None):
        """
        Returns an indexed item with an optional default in case there's no item.

        :type index: int
        :type default: object
        :rtype: object
        """

        return self.__items__.get(index, default)

    def lastIndex(self):
        """
        Returns the last known index currently in use.

        :rtype: int
        """

        if self.__len__() > 0:

            return self.indices()[-1]

        else:

            return None

    def indices(self):
        """
        Returns a sorted list of indices currently in use.

        :rtype: list[int]
        """

        return list(self.iterIndices())

    def iterIndices(self):
        """
        Returns a generator that iterates over sorted list of indices.

        :rtype: iter
        """

        return sorted(self.__items__.keys())

    def values(self):
        """
        Returns a list of values currently in use.

        :rtype: list
        """

        return self.__items__.values()

    def items(self):
        """
        Returns a list of key-value pairs that make up this sparse array.

        :rtype: list
        """

        return self.__items__.items()

    @property
    def isSequential(self):
        """
        Getter method that evaluates whether the indices are consecutive.

        :rtype: bool
        """

        return self.indices() == list(range(self.__len__()))

    def nextAvailableIndex(self):
        """
        Returns the next available index in this array.

        :rtype: int
        """

        # Look for a mismatch
        #
        for (physicalIndex, logicalIndex) in enumerate(self.indices()):

            if physicalIndex != logicalIndex:

                return physicalIndex

        # Return last index
        #
        if self.__len__() > 0:

            return self.lastIndex()

        else:

            return 0

    def toList(self, default=None):
        """
        Converts this sparse array into a list.
        All empty entries will be filled with the default value.

        :type default: object
        :rtype: list
        """

        if self.__len__() > 0:

            return [self.__items__.get(x, default) for x in range(self.lastIndex() + 1)]

        else:

            return []

    def toDict(self):
        """
        Converts this sparse array into a dictionary.

        :rtype: dict
        """

        return dict(self.__items__)
