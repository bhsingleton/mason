import weakref

from abc import ABCMeta, abstractmethod
from .decorators import classproperty

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class AsciiBase(object, metaclass=ABCMeta):
    """
    Abstract base class used for all Ascii objects.
    """

    # region Dunderscores
    __slots__ = ('__weakref__',)

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.
        """

        # Call parent method
        #
        super(AsciiBase, self).__init__()

    def __hash__(self):
        """
        Private method that returns a hashable value for this instance.

        :rtype: int
        """

        return self.hashCode()
    # endregion

    # region Properties
    @classproperty
    def className(cls):
        """
        Getter method that returns a null weak reference.

        :rtype: lambda
        """

        return cls.__name__

    @classproperty
    def nullWeakReference(self):
        """
        Getter method that returns a null weak reference.

        :rtype: lambda
        """

        return lambda: None
    # endregion

    # region Methods
    def hashCode(self):
        """
        Returns a hashable value for this instance.

        :rtype: int
        """

        return id(self)

    def weakReference(self):
        """
        Returns a weak reference to this object.

        :rtype: weakref.ref
        """

        return weakref.ref(self)

    @classmethod
    def splitName(cls, name):
        """
        Returns the namespace and name from the given string.

        :type name: str
        :rtype: str, str
        """

        # Strip any pipe delimiters
        #
        name = cls.stripDagPath(name)

        # Split using namespace delimiter
        #
        strings = name.split(':')
        numStrings = len(strings)

        if numStrings >= 2:

            return ':'.join(strings[:-1]), strings[-1]

        else:

            return '', strings[0]

    @staticmethod
    def stripDagPath(name):
        """
        Method used to remove any pipe characters from the supplied name.

        :type name: str
        :rtype: str
        """

        return name.split('|')[-1]

    @staticmethod
    def stripNamespace(name):
        """
        Method used to remove any colon characters from the supplied name.

        :type name: str
        :rtype: str
        """

        return name.split(':')[-1]

    @classmethod
    def stripAll(cls, name):
        """
        Method used to remove any unwanted characters from the supplied name.

        :type name: str
        :rtype: str
        """

        name = cls.stripDagPath(name)
        name = cls.stripNamespace(name)

        return name
    # endregion
