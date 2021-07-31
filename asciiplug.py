import re

from enum import IntEnum
from itertools import chain
from collections import namedtuple

from . import asciitreemixin, asciiattribute, asciidata
from .collections import sparsearray

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class AsciiPlug(asciitreemixin.AsciiTreeMixin):
    """
    Ascii class used to interface with attribute plugs.
    The child plugs are populated based on the attribute definition.
    Editing the child arrays will result in unpredictable behaviour!
    """

    __slots__ = (
        '_node',
        '_attribute',
        '_index',
        '_index',
        '_parent',
        '_elements',
        '_children',
        '_dataBlock',
        '_locked',
        '_keyable',
        '_channelBox',
        '_source',
        '_destinations'
    )

    def __init__(self, node, attribute, **kwargs):
        """
        Private method called after a new instance has been created.
        The keyword arguments are for internal use only!

        :type node: asciinode.AsciiNode
        :type attribute: asciiattribute.AsciiAttribute
        :keyword parent: weakref.ref
        :keyword index: int
        :rtype: None
        """

        # Call parent method
        #
        super(AsciiPlug, self).__init__()

        # Declare private variables
        #
        self._node = node.weakReference()
        self._attribute = attribute.weakReference()
        self._index = kwargs.get('index', None)
        self._parent = kwargs.get('parent', self.nullWeakReference)
        self._children = []
        self._locked = False
        self._keyable = attribute.keyable
        self._channelBox = attribute.channelBox
        self._source = self.nullWeakReference
        self._destinations = []

        # Initialize plug specific attributes
        #
        if self.isArray and not self.isElement:

            self._elements = sparsearray.SparseArray()

        elif self.isCompound:

            self._children = [AsciiPlug(node, child, parent=self.weakReference()) for child in attribute.children]

        else:

            dataType = asciidata.getDataType(attribute)

            if dataType is not None:

                self._dataBlock = dataType(attribute)

    def __str__(self):
        """
        Private method that returns a string representation of this instance.

        :rtype: str
        """

        return f'<{self.__class__.__module__}.{self.__class__.__name__} object: {self.name}>'

    def __getitem__(self, key):
        """
        Private method that returns an indexed plug.
        Only array and compound plugs work with this method!

        :type key: Union[int, str]
        :rtype: AsciiPlug
        """

        # Check index type
        #
        if isinstance(key, int):

            # Check if this is an array plug
            #
            if self.isArray and not self.isElement:

                return self.elementByLogicalIndex(key)

            else:

                return self.child(key)

        elif isinstance(key, str):

            return self.__getitem__(self.node.attribute(key))  # Locate the associated attribute

        elif isinstance(key, asciiattribute.AsciiAttribute):

            return self.__getitem__(self.attribute.children.index(key))  # Locate the attribute index

        elif isinstance(key, slice):

            return [self.__getitem__(i) for i in range(key.start, key.stop + 1, 1)]  # Return range of plugs

        elif key is None:

            return self  # This is here purely for laziness...

        else:

            raise IndexError(f'__getitem__() expects either an int or str ({type(key).__name__} given)!')

    @property
    def node(self):
        """
        Getter method that returns the node associated with this plug.

        :rtype: asciinode.AsciiNode
        """

        return self._node()

    @property
    def attribute(self):
        """
        Getter method that returns the attribute associated with this plug.

        :rtype: asciiattribute.AsciiAttribute
        """

        return self._attribute()

    @property
    def name(self):
        """
        Getter method that returns the full name of this plug.

        :rtype: str
        """

        return self.partialName(includeNodeName=True, includeIndices=True, useFullAttributePath=True, useLongNames=True)

    def partialName(self, **kwargs):
        """
        Returns a partial name for this plug.

        :keyword includeNodeName: bool
        :keyword includeIndices: bool
        :keyword useFullAttributePath: bool
        :keyword useLongNames: bool
        :rtype: str
        """

        # Check if full path should be generated
        #
        includeNodeName = kwargs.get('includeNodeName', False)
        includeIndices = kwargs.get('includeIndices', False)
        useFullAttributePath = kwargs.get('useFullAttributePath', False)
        useLongNames = kwargs.get('useLongNames', False)

        name = ''

        if useFullAttributePath:

            # Evaluate plug path
            #
            plugs = list(self.trace())
            numPlugs = len(plugs)

            if numPlugs == 1:

                return self.partialName(includeNodeName=includeNodeName, useLongNames=useLongNames)

            # Iterate through path
            #
            lastIndex = len(plugs) - 1

            for (i, plug) in enumerate(plugs):

                # Check if this is an array plug
                # We want to skip this to avoid any redundancies in child elements
                #
                if (plug.isArray and not plug.isElement) and i != lastIndex:

                    continue

                # Evaluate next portion of string
                #
                delimiter = '.' if len(name) > 0 else ''
                partialName = plug.partialName(includeIndices=includeIndices, useLongNames=useLongNames)

                name += f'{delimiter}{partialName}'

        else:

            # Check if long names should be used
            #
            if useLongNames:

                name += f'{self.attribute.longName}'

            else:

                name += f'{self.attribute.shortName}'

            # Check if index should be included
            #
            if includeIndices and self.isElement:

                name += f'[{self.logicalIndex}]'

        # Check if node name should be included
        #
        if includeNodeName:

            return f'{self.node.absoluteName()}.{name}'

        else:

            return name

    @property
    def parent(self):
        """
        Getter method that returns the parent of the plug.

        :rtype: AsciiPlug
        """

        return self._parent()

    @property
    def children(self):
        """
        Getter method that returns the children for this plug.

        :rtype: Union[sparselist.SparseList, list]
        """

        if self.isArray and not self.isElement:

            return self._elements

        else:

            return self._children

    @property
    def isReadable(self):
        """
        Getter method that returns the readable state on this plug.

        :rtype: bool
        """

        return self.attribute.readable

    @property
    def isWritable(self):
        """
        Getter method that returns the writable state on this plug.

        :rtype: bool
        """

        return self.attribute.writable

    @property
    def isStorable(self):
        """
        Getter method that returns the storable state on this plug.

        :rtype: bool
        """

        return self.attribute.storable

    @property
    def isKeyable(self):
        """
        Getter method that returns the keyable state on this plug.

        :rtype: bool
        """

        return self._keyable

    @isKeyable.setter
    def isKeyable(self, keyable):
        """
        Setter method that updates the keyable state on this plug.

        :type keyable: bool
        :rtype: None
        """

        self._keyable = keyable

    @property
    def isLocked(self):
        """
        Getter method that returns the locked state on this plug.

        :rtype: bool
        """

        return self._locked

    @isLocked.setter
    def isLocked(self, locked):
        """
        Getter method that returns the locked state on this plug.

        :type locked: bool
        :rtype: None
        """

        self._locked = locked

    @property
    def isSequential(self):
        """
        Getter method that evaluates whether the child elements are in consecutive order.

        :rtype: bool
        """

        return self._elements.isSequential

    @property
    def isCompound(self):
        """
        Getter method that evaluates whether this plug represents a dictionary.

        :rtype: bool
        """

        return self.attribute.isCompound

    @property
    def isArray(self):
        """
        Getter method that evaluates whether this plug represents an array.

        :rtype: bool
        """

        return self.attribute.isArray

    @property
    def isConnected(self):
        """
        Getter method that evaluates whether this plug has an incoming connection.

        :rtype: bool
        """

        return self.source() is not None

    def source(self):
        """
        Returns the source plug connected to this plug.

        :rtype: AsciiPlug
        """

        return self._source()

    def destinations(self):
        """
        Returns the destinations plugs this plug is connected to.

        :rtype: list[AsciiPlug]
        """

        return [x() for x in self._destinations]

    def connect(self, otherPlug):
        """
        Connects this plug to the destination.

        :type otherPlug: AsciiPlug
        :rtype: bool
        """

        # Check if connection is legal
        #
        isLegal = self.node.legalConnection(self, otherPlug)

        if not isLegal:

            return

        # Connect plugs
        #
        otherPlug._source = self.weakReference()
        self._destinations.append(otherPlug.weakReference())

        # Notify node of connections
        #
        self.node.connectionMade(self, otherPlug)

        return True

    def disconnect(self, otherPlug):
        """
        Disconnects this plug from the destination.

        :type otherPlug: AsciiPlug
        :rtype: bool
        """

        # Check if connection is legal
        #
        isLegal = self.node.legalDisconnection(self, otherPlug)

        if not isLegal:

            return

        # Disconnect plugs
        #
        otherPlug._source = self.nullWeakReference
        self._destinations.remove(otherPlug.weakReference())

        # Notify node of disconnection
        #
        self.node.disconnectionMade(self, otherPlug)

        return True

    def breakConnections(self, source=False, destinations=False):
        """
        Breaks any connections related to this plug.

        :type source: bool
        :type destinations: bool
        :rtype: None
        """

        # Check if source should be broken
        #
        otherPlug = self.source()

        if source and otherPlug is not None:

            otherPlug.disconnect(self)

        # Check if destinations should be broken
        #
        otherPlugs = self.destinations()

        if destinations:

            for otherPlug in otherPlugs:

                self.disconnect(otherPlug)

    @property
    def isNonDefault(self):
        """
        Getter method that evaluates whether this plug has been changed.

        :rtype: bool
        """

        # Evaluate plug type
        #
        if self.isArray and not self.isElement:

            return any([x.isNonDefault for x in self._elements.values()])

        elif self.isCompound:

            return any([x.isNonDefault for x in self._children])

        else:

            return self._dataBlock.isNonDefault()

    @property
    def size(self):
        """
        Getter method that evaluates the number of elements belonging to this plug.

        :rtype: int
        """

        return self.numElements

    @size.setter
    def size(self, size):
        """
        Setter method that updates the number of elements belonging to this plug.
        No need to update the child dictionary since the elementByLogicalIndex method will handle that for us.

        :type size: int
        :rtype: None
        """

        # Check if this is an array plug
        #
        if self.isArray and not self.isElement:

            current = self.numElements

            for index in range(current, size, 1):

                self._elements[index] = AsciiPlug(self.node, self.attribute, index=index, parent=self.weakReference())

        elif self.isElement:

            self.parent.size = size

        else:

            pass

    def child(self, index):
        """
        Returns a child from this plug.

        :type index: Union[int, str, asciiattribute.AsciiAttribute]
        :rtype: AsciiPlug
        """

        # Verify this is a compound plug
        #
        if not self.isCompound:

            raise TypeError('child() expects a compound plug!')

        # Check argument type
        #
        if isinstance(index, int):

            return self._children[index]

        elif isinstance(index, str):

            return self.child(self.node.attribute(index))

        if isinstance(index, asciiattribute.AsciiAttribute):

            return self.child(self.attribute.children.index(index))

        else:

            raise TypeError(f'child() expects an attribute ({type(index).__name__} given)!')

    @property
    def logicalIndex(self):
        """
        Getter method that returns the index for this plug.

        :rtype: int
        """

        return self._index

    @property
    def isElement(self):
        """
        Getter method that evaluates whether this plug represents an element.

        :rtype: bool
        """

        return self.isArray and self.logicalIndex is not None

    @property
    def numElements(self):
        """
        Getter method that evaluated the number of elements in use.

        :rtype: int
        """

        return len(self._elements)

    def getExistingArrayAttributeIndices(self):
        """
        Returns an ordered list of element indices that are currently in use.

        :rtype: list[int]
        """

        return self._elements.indices()

    def elementByLogicalIndex(self, index):
        """
        Returns a plug element at the specified logical index.

        :type index: int
        :rtype: AsciiPlug
        """

        # Verify this is an array plug
        #
        if self.isArray and not self.isElement:

            # Check if element exists
            #
            element = self._elements.get(index, None)

            if element is None:

                element = AsciiPlug(self.node, self.attribute, index=index, parent=self.weakReference())
                self._elements[index] = element

            return element

        else:

            raise TypeError('elementByLogicalIndex() expects an array plug!')

    def elementByPhysicalIndex(self, index):
        """
        Returns a plug element at the specified physical index.

        :type index: int
        :rtype: AsciiPlug
        """

        # Verify this is an array plug
        #
        if self.isArray and not self.isElement:

            # Check if physical index exists
            #
            indices = self.getExistingArrayAttributeIndices()
            numIndices = len(indices)

            if 0 <= index < numIndices:

                return self.elementByLogicalIndex(indices[index])

            else:

                return None

        else:

            raise TypeError('elementByLogicalIndex() expects an array plug!')

    def nextAvailableIndex(self):
        """
        Returns the next available logical index.

        :rtype: int
        """

        return self._elements.nextAvailableIndex()

    def getValue(self):
        """
        Updates the value associated with this plug.

        :rtype: Any
        """

        # Evaluate plug type
        #
        if self.isArray and not self.isElement:

            # Check if elements are sequential
            #
            if self.isSequential:

                return [x.getValue() for x in self._elements.values()]

            else:

                return {x: y.getValue for (x, y) in self._elements.items()}

        elif self.isCompound:

            # Check if this is a non-numeric compound attribute
            #
            if self.attribute.attributeType == 'compound':

                return {x.attribute.longName: x.getValue() for x in self._children}

            else:

                return [x.getValue() for x in self._children]

        else:

            # Return value from data block
            #
            return self._dataBlock.get()

    def setValue(self, value):
        """
        Updates the value associated with this plug.

        :type value: Any
        :rtype: None
        """

        # Evaluate plug type
        #
        if self.isArray and not self.isElement:

            # Check value type
            #
            if isinstance(value, (list, tuple)):

                for (index, item) in enumerate(value):

                    element = self.elementByLogicalIndex(index)
                    element.setValue(item)

            elif isinstance(value, dict):

                for (index, item) in value.items():

                    element = self.elementByLogicalIndex(index)
                    element.setValue(item)

            else:

                raise TypeError('setValue() expects a list of values for array plugs!')

        elif self.isCompound:

            # Check if there are enough items
            #
            numItems = len(value)

            if self.numberOfChildren == numItems:

                for (child, item) in zip(self._children, value):

                    child.setValue(item)

            else:

                raise TypeError('setValue() mismatch found between number of values and plugs!')

        else:

            # Assign value to data block
            #
            self._dataBlock.set(value)
            log.debug(f'{self.name} = {self._dataBlock}')

    def getSetAttrCmds(self, nonDefault=True):
        """
        Returns a list of command strings that can recreate any changes made to this plug.

        :type nonDefault: bool
        :rtype: list[str]
        """

        # Check if plug is storable
        #
        commands = []

        if not self.isStorable:

            return commands

        # Check if this is a multi-instance plug
        #
        name = self.partialName(includeNodeName=False, includeIndices=True, useFullAttributePath=True)

        if self.isArray and not self.isElement:

            # Check number of elements
            #
            if self.numElements == 0:

                return commands

            # Check if data is sequential
            #
            if self.isSequential:

                # Append edit size command
                #
                command = f'\tsetAttr -s {self.numElements} ".{name}";'
                commands.append(command)

            # Iterate through physical elements
            #
            for i in range(self.numElements):

                element = self.elementByPhysicalIndex(i)
                commands.extend(element.getSetAttrCmds())

            return commands

        elif self.isCompound:

            # Check if this is a numeric compound attribute
            #
            if self.attribute.attributeType == 'compound':

                # Iterate through plug children
                #
                numChildren = self.numberOfChildren

                for i in range(numChildren):

                    commands.extend(self.child(i).getSetAttrCmds())

                return commands

            else:

                # Concatenate compound value
                #
                value = ' '.join(map(str, [x.getValue() for x in self._children]))
                command = f'\tsetAttr ".{name}" -type "{self.attribute.attributeType}" {value};'

                return [command]

        else:

            # Check if data block is valid
            #
            if self._dataBlock is None:

                return commands

            # Check if non-default values should be included
            #
            if nonDefault and not self.isNonDefault:

                return commands

            # Check if type flag is required
            #
            command = None
            value = self._dataBlock.writeAscii()

            if self.attribute.isTyped:

                command = f'\tsetAttr ".{name}" -type "{self.attribute.dataType}" {value};'

            else:

                command = f'\tsetAttr ".{name}" {value};'

            return [command]


AsciiPlugSegment = namedtuple('AsciiPlugSegment', ['attribute', 'index'])
AsciiPlugType = IntEnum('AsciiPlugType', ['kSingle', 'kArray', 'kCompoundArray'])


class AsciiPlugPath(object):
    """
    Ascii class used to evaluate plug paths for hassle free lookups.
    This class expects the following string format: {nodeName}.{attributeName} etc
    Omitting the node name will force the parser to use the active selection!
    To my knowledge there are 3 forms of plug path syntax:
        kSingle: Represents a single plug -> .translate.translateX
        kArray: Represents an array of plugs using a slice object -> .points[0:24]
        kCompoundArray: Represents an array of compound plugs using a slice object -> .weightList[0:24].weights
    Who knows there may be more???
    """

    __slots__ = ('_scene', '_node', '_segments', '_cache')
    __syntax__ = re.compile(r'([a-zA-Z0-9_]+)(?:\[{1}([:0-9]*)\]{1})?')

    def __init__(self, path, scene=None):
        """
        Private method called after a new instance has been created.

        :type path: str
        :type scene: mason.asciiscene.AsciiScene
        :rtype: None
        """

        # Call parent method
        #
        super(AsciiPlugPath, self).__init__()

        # Declare private variables
        #
        self._scene = scene.weakReference()
        self._node = AsciiPlug.nullWeakReference
        self._segments = None
        self._cache = None

        # Check if this is a valid string
        #
        strings = path.split('.')
        numStrings = len(strings)

        if numStrings < 2:

            raise TypeError('AsciiPlugPath() expects a valid string!')

        # Pop node name from strings
        #
        nodeName = strings.pop(0)

        if len(nodeName) == 0:

            self._node = self.scene.selection[0].weakReference()

        else:

            self._node = self.scene.getNodeByName(nodeName).weakReference()

        # Evaluate attribute path
        #
        groups = self.__syntax__.findall('.'.join(strings))
        indices = {name: self.expandIndex(index) for (name, index) in groups}

        attributes = list(self.node.attribute(groups[-1][0]).trace())
        numAttributes = len(attributes)

        self._segments = [None] * numAttributes

        for (i, attribute) in enumerate(attributes):

            index = indices.get(attribute.shortName, indices.get(attribute.longName))
            self._segments[i] = AsciiPlugSegment(attribute=attribute.weakReference(), index=index)

    def __str__(self):
        """
        Private method that returns the string representation of this object

        :rtype: str
        """

        return self.toString()

    def __getitem__(self, index):
        """
        Private method that returns an indexed item.

        :type index: int
        :rtype: Segment
        """

        return self._segments[index]

    def __iter__(self):
        """
        Private method that returns a generator for this collection.

        :rtype: iter
        """

        return iter(self._segments)

    def __len__(self):
        """
        Private method that evaluates the length of this collection.

        :rtype: int
        """

        return len(self._segments)

    @property
    def scene(self):
        """
        Getter method that returns the scene associated with this path.

        :rtype: mason.asciiscene.AsciiScene
        """

        return self._scene()

    @property
    def node(self):
        """
        Getter method that returns the node associated with this path.

        :rtype: mason.asciinode.AsciiNode
        """

        return self._node()

    def type(self):
        """
        Evaluates the path type.

        :rtype: AsciiPlugType
        """

        if self.isSingle():

            return AsciiPlugType.kSingle

        elif self.isArray():

            return AsciiPlugType.kArray

        elif self.isCompoundArray():

            return AsciiPlugType.kCompoundArray

        else:

            raise RuntimeError('type() encountered an unknown path type!')

    def isSingle(self):
        """
        Evaluates whether this path represents a single plug.

        :rtype: bool
        """

        return all([not isinstance(segment.index, slice) for segment in self._segments])

    def isArray(self):
        """
        Evaluates whether this path represents an array of plug elements.

        :rtype: bool
        """

        return isinstance(self._segments[-1].index, slice)

    def isCompoundArray(self):
        """
        Evaluates whether this path represents an array of compound plug elements.

        :rtype: bool
        """

        return self._segments[-1].index is None and isinstance(self._segments[-2].index, slice)

    def sizeHint(self):
        """
        Returns a size hint based on the number of plugs in this path.

        :rtype: int
        """

        return len(self._cache)

    @staticmethod
    def expandIndex(string):
        """
        Evaluates a string index.

        :type string: str
        :rtype: Union[None, int, slice]
        """

        # Check if there are any characters
        #
        numChars = len(string)

        if numChars == 0:

            return None

        # Check if this is a slice
        #
        strings = string.split(':')
        numStrings = len(strings)

        if numStrings == 1:

            return int(strings[0])

        elif numStrings == 2:

            return slice(int(strings[0]), int(strings[1]), 1)

        else:

            raise TypeError(f'index() expects a valid slice object ({string} given)!')

    def evaluate(self):
        """
        Evaluates the plugs associated from the string path.

        :rtype: list[AsciiPlug]
        """

        # Redundancy check
        #
        if self._cache is not None:

            return self._cache

        # Trace plug path
        #
        numLevels = len(self._segments)
        levels = [None] * numLevels

        for (i, segment) in enumerate(self._segments):

            # Evaluate path segment
            #
            index = segment.index
            attribute = segment.attribute()

            if i == 0:

                # Get top-level plug
                #
                plug = self.node.plugs.get(attribute.shortName, None)

                if plug is None:

                    plug = AsciiPlug(self.node, attribute)
                    self.node.plugs[attribute.shortName] = plug
                    self.node.plugs[attribute.longName] = plug

                # Inspect index type
                #
                if isinstance(index, int):

                    levels[i] = [plug[index]]

                elif isinstance(index, slice):

                    levels[i] = plug[index]

                else:

                    levels[i] = [plug]

            else:

                # Inspect index type
                #
                if isinstance(index, int):

                    levels[i] = [plug[attribute][index] for plug in levels[i - 1]]

                elif isinstance(index, slice):

                    levels[i] = list(chain(*[plug[attribute][index] for plug in levels[i - 1]]))

                else:

                    levels[i] = [plug[attribute] for plug in levels[i - 1]]

        # Cache result for faster lookups
        #
        self._cache = levels[-1]
        return self._cache

    def isValid(self):
        """
        Evaluates whether this plug path is valid.
        TODO: I really should implement this at some point...

        :rtype: bool
        """

        return True

    def toString(self, useLongNames=False):
        """
        Converts this plug path to a string.
        Unlike the original user value this returns a fully qualified path name.

        :rtype: str
        """

        # Iterate through segments
        #
        fullPathName = ''

        for (i, segment) in enumerate(self._segments):

            # Append name
            #
            delimiter = '.' if i > 0 else ''
            attribute = segment.attribute()

            if useLongNames:

                fullPathName += f'{delimiter}{attribute.longName}'

            else:

                fullPathName += f'{delimiter}{attribute.shortName}'

            # Append index if any
            #
            index = segment.index

            if isinstance(index, int):

                fullPathName += f'[{index}]'

            elif isinstance(index, slice):

                fullPathName += f'[{index.start}:{index.stop}]'

            else:

                continue

        return fullPathName
