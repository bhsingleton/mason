import re
import ast
import numpy

from maya import cmds as mc
from mason import asciibase
from mason.asciiplug import AsciiPlugType

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def state(value):
    """
    Evaluates the state string and converts it to a boolean.

    :type value: str
    :rtype: bool
    """

    return value in ('yes', 'on', 'true')


class AsciiFlagParser(asciibase.AsciiBase):
    """
    Ascii class used to translate command flags.
    """

    __slots__ = ('shortName', 'longName', 'dataType', 'multiUse')

    __datatypes__ = {
        'String': str,
        'UnsignedInt': int,
        'Int': int,
        'Float': float,
        'on|off': state
    }

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.
        """

        # Call parent method
        #
        super(AsciiFlagParser, self).__init__()

        # Declare class variables
        #
        self.shortName = args[0]
        self.longName = args[1]
        self.dataType = None
        self.multiUse = False

        # Inspect number of arguments
        #
        numArgs = len(args)

        if numArgs == 3:

            self.dataType = self.__datatypes__[args[2]]

        elif numArgs == 4:

            self.dataType = self.__datatypes__[args[2]]
            self.multiUse = True

        else:

            pass

    def hasValue(self):
        """
        Evaluates whether this flag expects a value.

        :rtype: bool
        """

        return self.dataType is not None

    def toString(self, value):
        """
        Converts the supplied value into an ascii compatible string.

        :type value: object
        :rtype: str
        """

        if self.dataType is None:

            return self.shortName

        elif self.dataType is str:

            return f'{self.shortName} "{value}"'

        else:

            return f'{self.shortName} {str(value).lower()}'

    def fromString(self, value):
        """
        Converts the ascii string object into a python compatible object.

        :type value: str
        :rtype: object
        """

        if self.dataType is None:

            return None

        else:

            return self.dataType(value)


class AsciiArgParser(asciibase.AsciiBase):
    """
    Ascii class used to translate Maya command arguments.
    Using regex is way faster than the shlex module's split method!
    All arguments are dequoted at runtime.
    """

    __slots__ = ('_name', 'syntax', 'arguments', 'flags')
    __syntax__ = {}
    __quotation__ = '"'
    __command__ = re.compile(r'("(?:[^"\\]|\\.)*"|(?:-{1}[a-zA-Z]+)+|(?:[+-])?(?:[0-9])+(?:\.{1}[0-9]+)?(?:e{1}[\-\+]{1}[0-9]+)?|\w+)')
    __flag__ = re.compile(r'^(-+[a-zA-Z]+)$')
    __number__ = re.compile(r'(?:[+-])?(?:[0-9])+(?:\.{1}[0-9]+)?(?:e{1}\-{1}[0-9]+)?')

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.

        :type command: str
        :rtype: None
        """

        # Call parent method
        #
        super(AsciiArgParser, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._name = ''

        # Declare public variables
        #
        self.syntax = {}
        self.arguments = []
        self.flags = {}

        # Check supplied arguments
        #
        numArgs = len(args)

        if numArgs == 1:

            self.command = args[0]

    def __str__(self):
        """
        Private method that returns a string representation of this instance.

        :rtype: str
        """

        return self.toString()

    def __getitem__(self, key):
        """
        Private method that returns an indexed item.

        :type key: Union[int, str]
        :rtype: Union[bool, int, float, str]
        """

        # Check key type
        #
        if isinstance(key, int):

            return self.asString(key)

        elif isinstance(key, str):

            return self.getFlag(key)

        else:

            raise TypeError(f'__getitem__() expects either a str or int ({type(key).__name__} given)!')

    def __setitem__(self, key, value):
        """
        Private method that updates an indexed item.

        :type key: Union[str, int]
        :type value: Union[bool, int, float, str]
        :rtype: None
        """

        # Check key type
        #
        if isinstance(key, int):

            # Check if array should be expanded
            #
            if key >= self.numArguments:

                diff = (key + 1) - self.numArguments
                self.arguments.extend([None] * diff)

            self.arguments[key] = value

        elif isinstance(key, str):

            self.flags[key] = value

        else:

            raise TypeError(f'__setitem__() expects either an int or str ({type(key).__name__} given)!')

    def __delitem__(self, key):
        """
        Private method that deletes an indexed item.

        :type key: Union[int, str]
        :rtype: None
        """

        # Check key type
        #
        if isinstance(key, int):

            del self.arguments[key]

        elif isinstance(key, str):

            del self.flags[key]

        else:

            raise TypeError(f'__delitem__() expects either a str or int ({type(key).__name__} given)!')

    def __len__(self):
        """
        Private method that evaluates the number of arguments belonging to this command.

        :rtype: int
        """

        return self.numArguments + self.numFlags

    @property
    def command(self):
        """
        Getter method that returns the command string.

        :rtype: str
        """

        return self.toString()

    @command.setter
    def command(self, command):
        """
        Setter method updates the command string.

        :type command: str
        :rtype: None
        """

        # Collect arguments and flags from string
        #
        arguments = self.split(command)

        self.name = arguments.pop(0)
        self.arguments, self.flags = self.strip(arguments, syntax=self.syntax)

    @property
    def name(self):
        """
        Getter method that returns the name of this command.

        :rtype: str
        """

        return self._name

    @name.setter
    def name(self, name):
        """
        Setter method that updates the name of this command.

        :type name: str
        :rtype: None
        """

        # Update private variable
        #
        self._name = name

        # Clear previous arguments
        #
        self.arguments.clear()
        self.flags.clear()

        # Get associated command syntax
        #
        self.syntax = self.getSyntax(name)

    @classmethod
    def split(cls, line):
        """
        Splits the given a command string into arguments.

        :type line: str
        :rtype: list[str]
        """

        return [cls.dequote(x.group(0)) for x in cls.__command__.finditer(line) if x]

    @classmethod
    def strip(cls, arguments, syntax=None):
        """
        Strips any flags from the supplied arguments and returns them in a dictionary.

        :type arguments: deque
        :type syntax: dict
        :rtype: list, dict
        """

        # Iterate through known flags
        # Be sure to do this in reverse to avoid any index errors
        #
        numArguments = len(arguments)
        flags = {}

        for i in range(numArguments - 1, -1, -1):

            # Check if argument is a flag
            #
            argument = arguments[i]

            if not cls.isFlag(argument):

                continue

            # Pop flag from list
            #
            key = arguments.pop(i)
            parser = syntax[key]

            if parser.hasValue():

                flags[key] = parser.fromString(arguments.pop(i))

            else:

                flags[key] = True

        return arguments, flags

    @staticmethod
    def group(items, size=1):
        """
        Groups together a flat list based on the specified chunk size.

        :type items: list
        :type size: int
        :rtype: iter
        """

        return zip(*[iter(items)] * size)

    def package(self, path):
        """
        Groups the arguments together based on the supplied attribute.

        :type path: mason.asciiplug.AsciiPlugPath
        :rtype: list[Any]
        """

        # Inspect path type
        #
        pathType = path.type()

        if pathType == AsciiPlugType.kSingle or pathType == AsciiPlugType.kArray:

            # Check if this is a compound attribute
            # I found an edge case for vertex colours
            #
            attribute = path[-1].attribute()
            dataType = attribute.getDataType()

            if attribute.attributeType == 'compound':

                return numpy.array(self.arguments[1:], dtype=float).reshape([-1, attribute.numberOfChildren])

            else:

                return dataType.readAscii(self.arguments[1:])

        elif pathType == AsciiPlugType.kCompoundArray:

            # Organize array element arguments
            # This syntax is mostly used for skin weights
            #
            return self.asArray(sizeHint=path.sizeHint())

        else:

            return []

    @property
    def numArguments(self):
        """
        Getter method that evaluates the number of arguments.

        :rtype: int
        """

        return len(self.arguments)

    def asString(self, index):
        """
        Returns an indexed argument as a string.

        :type index: int
        :rtype: str
        """

        return self.arguments[index]

    def asBool(self, index):
        """
        Returns an indexed argument as a boolean.

        :type index: int
        :rtype: bool
        """

        return state(self.arguments[index])

    def asInt(self, index):
        """
        Returns all integer arguments as flat array.

        :type index: int
        :rtype: int
        """

        return int(self.arguments[index])

    def asFloat(self, index):
        """
        Returns an float argument as a flat array.

        :type index: int
        :rtype: float
        """

        return float(self.arguments[index])

    def asArray(self, sizeHint=0):
        """
        Organizes the arguments into a sequence of sparse array elements.
        This syntax is mostly used for skin weights.

        :rtype: list[dict[int:Union[int,float]]]
        """

        # Iterate through arguments
        #
        iterator = iter(self.arguments[1:])
        items = [None] * sizeHint
        index = 0

        while True:

            try:

                # Evaluate number of key-value pairs
                #
                numItems = int(next(iterator))
                pairs = {}

                for i in range(0, numItems * 2, 2):

                    key = int(next(iterator))
                    value = ast.literal_eval(next(iterator))

                    pairs[key] = value

                # Assign key-value pairs
                #
                try:

                    items[index] = pairs
                    index += 1

                except IndexError:

                    items.append(pairs)

            except StopIteration:

                break

        return items

    @classmethod
    def getSyntax(cls, command):
        """
        Returns the syntax for the supplied command.

        :type command: str
        :rtype: dict
        """

        #  Check for redundancy
        #
        syntax = cls.__syntax__.get(command, None)

        if syntax is not None:

            return syntax

        # Split help string
        #
        syntax = {}

        docstring = mc.help(command, syntaxOnly=True)
        lines = [x.split() for x in docstring.split('\n')[2:] if len(x) > 0]

        for line in lines:

            parser = AsciiFlagParser(*line)
            syntax[parser.shortName] = parser
            syntax[parser.longName] = parser

        cls.__syntax__[command] = syntax
        return syntax

    @property
    def numFlags(self):
        """
        Getter method that evaluates the number of flags.

        :rtype: int
        """

        return len(self.flags)

    @classmethod
    def isFlag(cls, item):
        """
        Evaluates whether the supplied item represents a command flag.

        :type item: str
        :rtype: bool
        """

        return cls.__flag__.match(item) and item != '-nan'

    def getFlag(self, flag, default=None):
        """
        Getter method used to get the value associated with the supplied flag.

        :type flag: str
        :type default: object
        :rtype: Union[bool, int, float, str]
        """

        return self.flags.get(flag, default)

    def hasFlag(self, flag):
        """
        Evaluates whether or not this command has the given flag.

        :type flag: str
        :rtype: bool
        """

        return self.flags.get(flag, None) is not None

    def toString(self, indent=0):
        """
        Concatenates this command into an ascii compatible string.

        :type indent: int
        :rtype: str
        """

        flags = ' '.join([self.syntax[key].toString(value) for (key, value) in self.flags.items()])
        arguments = ' '.join(self.arguments)
        tabs = '\t' * indent

        return f"{tabs}{self.name} {flags} {arguments};"

    @classmethod
    def dequote(cls, value):
        """
        Removes the surrounding quotes from the supplied string.

        :type value: str
        :rtype: str
        """

        if value.startswith(cls.__quotation__) and value.endswith(cls.__quotation__):

            return value[1:-1]

        else:

            return value
