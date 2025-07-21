from collections.abc import MutableSequence, MutableMapping
from dcc.collections import sparsearray
from . import asciibase, asciiattribute, asciiplug, asciidata

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class AsciiDataHandle(asciibase.AsciiBase):
    """
    Ascii class used to update values within the datablock.
    """

    # region Dunderscores
    __slots__ = ('_attribute', '_block', '_index')

    def __init__(self, block, index, **kwargs):
        """
        Private method called after a new instance has been created.

        :type block: Any
        :type index: Union[int, str, None]
        :rtype: None
        """

        # Call parent method
        #
        super(AsciiDataHandle, self).__init__()

        # Declare private variables
        #
        self._attribute = kwargs.get('attribute', self.nullWeakReference)
        self._block = block
        self._index = index
    # endregion

    # region Properties
    @property
    def attribute(self):
        """
        Getter method that returns the attribute associated with this data handle.

        :rtype: asciiattribute.AsciiAttribute
        """

        return self._attribute()

    @property
    def block(self):
        """
        Getter method that returns a container within the datablock.

        :rtype: Sequence
        """

        return self._block

    @property
    def index(self):
        """
        Getter method that returns the index inside the datablock.

        :rtype: Union[int, str, None]
        """

        return self._index
    # endregion

    # region Methods
    def copy(self, block, values):
        """
        Copies the supplied values to the specified block.

        :type block: sparsearray.SparseArray
        :type values: Union[MutableSequence, MutableMapping]
        :rtype: None
        """

        cls = self.attribute.getDataType()
        block.clear()

        if isinstance(values, MutableSequence):

            for (i, item) in enumerate(values):

                block[i] = cls(self.attribute)
                block[i].set(item)

        elif isinstance(values, MutableMapping):

            for (i, item) in values.items():

                block[i] = cls(self.attribute)
                block[i].set(item)

        else:

            raise TypeError(f'copy() expects either a sequence or map ({type(values).__name__} given)!')

    def get(self):
        """
        Private method that returns an indexed block.

        :rtype: Any
        """

        # Trace plug hierarchy
        #
        block = self.block[self.index] if isinstance(self.index, (int, str)) else self.block

        if isinstance(block, asciidata.AsciiData):

            return block.get()

        else:

            return block

    def set(self, value):
        """
        Private method that updates an indexed block.

        :type value: Any
        :rtype: None
        """

        # Evaluate block type
        #
        if isinstance(self.block, sparsearray.SparseArray):

            # Evaluate index type
            #
            if isinstance(self.index, int):

                self.block[self.index].set(value)

            elif self.index is None:

                self.copy(self.block, value)

            else:

                raise TypeError(f'set() expects an integer index ({type(self.index).__name__} given)!')

        elif isinstance(self.block, asciidata.AsciiCompound):

            # Evaluate index type
            #
            block = self.block[self.index] if isinstance(self.index, (int, str)) else self.block

            if isinstance(block, sparsearray.SparseArray):

                self.copy(block, value)

            else:

                block.set(value)

        elif isinstance(self.block, asciidata.AsciiData):

            # Evaluate index type
            #
            if isinstance(self.index, int):

                self.block[self.index] = value

            else:

                self.block.set(value)

        else:

            raise TypeError(f'set() expects a valid block ({type(self.block).__name__} given)!')
    # endregion


class AsciiDataBlock(asciibase.AsciiBase):
    """
    Ascii class used to interface with data blocks.
    All data is stored inside a dictionary using attribute short names for keys.
    """

    # region Dunderscores
    __slots__ = ('__node__', '__blocks__')

    def __init__(self, node, **kwargs):
        """
        Private method called after a new instance has been created.

        :type node: asciinode.AsciiNode
        :rtype: None
        """

        # Call parent method
        #
        super(AsciiDataBlock, self).__init__()

        # Declare private variables
        #
        self.__node__ = node.weakReference()
        self.__blocks__ = {}

    def __repr__(self):
        """
        Private method that returns a string representation of this instance.

        :rtype: str
        """

        return repr(self.__blocks__)
    # endregion

    # region Properties
    @property
    def node(self):
        """
        Getter method that returns the node associated with this plug.

        :rtype: asciinode.AsciiNode
        """

        return self.__node__()
    # endregion

    # region Methods
    def items(self):
        """
        Returns a generator that yields key-value pairs from the datablock.

        :rtype: Iterator[Tuple[str, Any]]
        """

        return self.__blocks__.items()

    def constructHandle(self, plug):
        """
        Returns a data handle that points to the value this plug is associated with.

        :type plug: asciiplug.AsciiPlug
        :rtype: AsciiDataHandle
        """

        block = self.allocateBlock(plug)
        index = plug.position()

        return AsciiDataHandle(block, index, attribute=plug.attribute.weakReference())

    def allocateBlock(self, plug):
        """
        Ensures that a block exists for the supplied plug.

        :type plug: asciiplug.AsciiPlug
        :rtype: Any
        """

        # Check if block already exists
        #
        plugs = tuple(plug.trace())
        lastIndex = len(plugs) - 1

        block = None

        for (i, childPlug) in enumerate(plugs):

            # Evaluate position in hierarchy
            #
            attribute = childPlug.attribute
            shortName = attribute.shortName

            if i == 0:

                # Check if top-level block exists
                #
                block = self.__blocks__.get(shortName, None)

                if block is not None:

                    continue

                # Create new top-level block
                #
                if childPlug.isArray:

                    block = sparsearray.SparseArray()

                else:

                    cls = asciidata.getDataType(attribute)
                    block = cls(attribute)

                self.__blocks__[shortName] = block

            elif 0 < i < lastIndex:

                # Check if indexed block exists
                #
                index = childPlug.position()

                if isinstance(block, sparsearray.SparseArray):

                    array = block

                    if not array.hasIndex(index):

                        cls = asciidata.getDataType(attribute)
                        block = cls(attribute)

                        array[index] = block

                    else:

                        block = array[index]

                elif isinstance(block, asciidata.AsciiCompound):

                    block = block[index]

                else:

                    raise TypeError(f'allocateBlock() encountered an unexpected type: {type(block).__name__}')

            else:

                # Evaluate last block type
                #
                index = childPlug.position()

                if not (isinstance(block, sparsearray.SparseArray) and isinstance(index, int)):

                    continue

                # Check if block requires resizing
                #
                if not block.hasIndex(index):

                    cls = asciidata.getDataType(attribute)
                    block[index] = cls(attribute)

        return block
    # endregion