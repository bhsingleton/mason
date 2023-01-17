from abc import ABCMeta, abstractmethod
from six import with_metaclass
from collections import deque

from . import asciibase

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class AsciiTreeMixin(with_metaclass(ABCMeta, asciibase.AsciiBase)):
    """
    Overload of AsciiBase used to outline parent/child behaviour.
    """

    # region Dunderscores
    __slots__ = ()

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.
        """

        # Call parent method
        #
        super(AsciiTreeMixin, self).__init__(*args, **kwargs)

    def __getitem__(self, index):
        """
        Private method that returns either an indexed child.

        :type index: int
        :rtype: AsciiObject
        """

        return self.children[index]

    def __setitem__(self, index, value):
        """
        Private method that updates an indexed child.

        :type index: int
        :rtype: None
        """

        self.children[index] = value

    def __delitem__(self, index):
        """
        Private method that deletes an indexed child.

        :type index: int
        :rtype: None
        """

        del self.children[index]

    def __iter__(self):
        """
        Private method that returns a generator for this object.

        :rtype: iter
        """

        return self.iterChildren()

    def __len__(self):
        """
        Private method that evaluates the number of children belonging to this object.

        :rtype: int
        """

        return self.numberOfChildren
    # endregion

    # region Properties
    @property
    @abstractmethod
    def parent(self):
        """
        Getter method that returns the parent of this object.

        :rtype: AsciiTreeMixin
        """

        pass

    @property
    def isLeaf(self):
        """
        Getter method that evaluates if this is a leaf attribute.

        :rtype: bool
        """

        return self.numberOfChildren == 0

    @property
    def isChild(self):
        """
        Getter method that evaluates whether this object is a child.

        :rtype: bool
        """

        return self.parent is not None

    @property
    @abstractmethod
    def children(self):
        """
        Getter method that returns the children for this object.

        :rtype: list[AsciiTreeMixin]
        """

        pass

    @property
    def numberOfChildren(self):
        """
        Getter method that evaluates the number of children belonging to this object.

        :rtype: int
        """

        return len(self.children)
    # endregion

    # region Methods
    def iterParents(self):
        """
        Returns a generator that can iterate over all of the parents relative to this object.

        :rtype: iter
        """

        # Walk up hierarchy
        #
        current = self.parent

        while current is not None:

            yield current
            current = current.parent

    def topLevelParent(self):
        """
        Returns the top level parent relative to this object.
        If this object has no parents then itself is returned.

        :rtype: asciiobject.AsciiObject
        """

        return list(self.trace())[-1]

    def isTopLevelParent(self):
        """
        Evaluates whether this object is a top level parent.

        :rtype: bool
        """

        return self.parent is self

    def home(self):
        """
        Returns a generator that can walk home from this object.
        Unlike iterParents this generator yields itself.

        :rtype: iter
        """

        yield self
        yield from self.iterParents()

    def trace(self):
        """
        Returns a generator that can retrace the hierarchy to this object.

        :rtype: iter
        """

        return reversed(list(self.home()))

    def iterChildren(self):
        """
        Returns a generator that can iterate over all the children relative to this object.

        :rtype: iter
        """

        return iter(self.children)

    def iterDescendants(self):
        """
        Returns a generator that can iterate over all descendants relative to this object.

        :rtype: iter
        """

        queue = deque(self.children)

        while len(queue) > 0:

            child = queue.popleft()
            yield child

            queue.extend(child.children)

    def hasChild(self, child):
        """
        Evaluates whether or not the supplied child belongs to this attribute.

        :type child: AsciiObject
        :rtype: bool
        """

        return child in self.children

    def depth(self):
        """
        Returns the hierarchical depth of this object.

        :rtype: int
        """

        return len(list(self.home()))
    # endregion
