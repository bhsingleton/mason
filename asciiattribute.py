from maya.api import OpenMaya as om
from dcc.collections import hashtable, weakreflist, notifylist
from . import asciitreemixin, asciiargparser, asciidata

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class AsciiAttribute(asciitreemixin.AsciiTreeMixin):
    """
    Ascii class used to interface with attribute definitions.
    For the sake of simplicity all data is translated back and forth using the AsciiArgParser class.
    It also helps when it comes time to serialize the addAttr commands.
    """

    # region Dunderscores
    __slots__ = (
        '_parent',
        '_children',
        '_parser',
        '_dynamic'
    )

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.
        """

        # Call parent method
        #
        super(AsciiAttribute, self).__init__()

        # Declare private variables
        #
        self._parent = self.nullWeakReference
        self._children = notifylist.NotifyList(cls=weakreflist.WeakRefList)
        self._parser = None
        self._dynamic = kwargs.get('dynamic', True)

        # Setup child notifies
        #
        self._children.addCallback('itemAdded', self.childAdded)
        self._children.addCallback('itemRemoved', self.childRemoved)

        # Check for any arguments
        #
        numArgs = len(args)

        if numArgs == 1:

            self._parser = args[0]

        else:

            self._parser = asciiargparser.AsciiArgParser('addAttr')

        # Declare public variables
        #
        self.parent = kwargs.get('parent', None)

        # Copy any properties from kwargs
        #
        self.update(kwargs)

    def __str__(self):
        """
        Private method that stringifies this instance.

        :rtype: str
        """

        return self.longName

    def __repr__(self):
        """
        Private method that returns a string representation of this instance.

        :rtype: str
        """

        return f'<{self.className}:{self.longName} @ {self.hashCode()}>'
    # endregion

    # region Properties
    @property
    def parent(self):
        """
        Getter method that returns the parent for this object.

        :rtype: AsciiAttribute
        """

        return self._parent()

    @parent.setter
    def parent(self, parent):
        """
        Setter method that updates the parent for this object.

        :type parent: AsciiAttribute
        :rtype: None
        """

        # Check for redundancy
        #
        if parent is self.parent:

            log.debug(f'{self} is already parented to: {parent}')
            return

        # Check for none type
        #
        oldParent = self.parent

        if isinstance(parent, AsciiAttribute):

            self._parent = parent.weakReference()

        elif parent is None:

            self._parent = self.nullWeakReference

        else:

            raise TypeError(f'parent.setter() expects an AsciiAttribute ({type(parent).__name__} given)!')

        # Cleanup any old references
        #
        self.parentChanged(oldParent, parent)

    @property
    def children(self):
        """
        Getter method that returns the children belonging to this object.

        :rtype: weakreflist.WeakRefList
        """

        return self._children

    @property
    def longName(self):
        """
        Getter method that returns the long name of this attribute.

        :rtype: str
        """

        return self._parser['-ln']

    @longName.setter
    def longName(self, longName):
        """
        Setter method that updates the long name of this attribute.

        :type longName: str
        :rtype: None
        """

        self._parser['-ln'] = longName

    @property
    def shortName(self):
        """
        Getter method that returns the short name of this attribute.

        :rtype: str
        """

        return self._parser['-sn']

    @shortName.setter
    def shortName(self, shortName):
        """
        Setter method that updates the short name of this attribute.

        :type shortName: str
        :rtype: None
        """

        self._parser['-sn'] = shortName

    @property
    def niceName(self):
        """
        Getter method that returns the nice name of this attribute.

        :rtype: str
        """

        return self._parser.getFlag('-nn', '')

    @niceName.setter
    def niceName(self, niceName):
        """
        Setter method that updates the nice name of this attribute.

        :type niceName: str
        :rtype: None
        """

        self._parser['-nn'] = niceName

    @property
    def attributeType(self):
        """
        Getter method that returns the attribute type of this attribute.

        :rtype: str
        """

        return self._parser.getFlag('-at')

    @attributeType.setter
    def attributeType(self, attributeType):
        """
        Setter method that updates the attribute type of this attribute.

        :type attributeType: str
        :rtype: None
        """

        self._parser['-at'] = attributeType

    @property
    def dataType(self):
        """
        Getter method that returns the data type of this attribute.

        :rtype: str
        """

        return self._parser.getFlag('-dt')

    @dataType.setter
    def dataType(self, dataType):
        """
        Setter method that updates the data type of this attribute.

        :type dataType: str
        :rtype: None
        """

        self._parser['-dt'] = dataType

    @property
    def readable(self):
        """
        Getter method that returns the readable flag of this attribute.

        :rtype: bool
        """

        return self._parser.getFlag('-r', True)

    @readable.setter
    def readable(self, readable):
        """
        Setter method that updates the readable flag of this attribute.

        :type readable: bool
        :rtype: None
        """

        self._parser['-r'] = readable

    @property
    def writable(self):
        """
        Getter method that returns the writable flag of this attribute.

        :rtype: bool
        """

        return self._parser.getFlag('-w', True)

    @writable.setter
    def writable(self, writable):
        """
        Setter method that updates the writable flag of this attribute.

        :type writable: bool
        :rtype: None
        """

        self._parser['-w'] = writable

    @property
    def storable(self):
        """
        Getter method that returns the storage flag of this attribute.

        :rtype: bool
        """

        return self._parser.getFlag('-s', True)

    @storable.setter
    def storable(self, storable):
        """
        Setter method that updates the storable flag of this attribute.

        :type storable: bool
        :rtype: None
        """

        self._parser['-s'] = storable

    @property
    def cachedInternally(self):
        """
        Getter method that returns the cached flag of this attribute.

        :rtype: bool
        """

        return self._parser.getFlag('-ci', True)

    @cachedInternally.setter
    def cachedInternally(self, cachedInternally):
        """
        Setter method that updates the cached flag of this attribute.

        :type cachedInternally: bool
        :rtype: None
        """

        self._parser['-ci'] = cachedInternally

    @property
    def multi(self):
        """
        Getter method that returns the multi flag of this attribute.

        :rtype: bool
        """

        return self._parser.getFlag('-m', False)

    @multi.setter
    def multi(self, multi):
        """
        Setter method that updates the multi flag of this attribute.

        :type multi: bool
        :rtype: None
        """

        self._parser['-m'] = multi

    @property
    def indexMatters(self):
        """
        Getter method that returns the indexMatters flag of this attribute.

        :rtype: bool
        """

        return self._parser.getFlag('-im', True)

    @indexMatters.setter
    def indexMatters(self, indexMatters):
        """
        Setter method that updates the indexMatters flag of this attribute.

        :type indexMatters: bool
        :rtype: None
        """

        self._parser['-im'] = indexMatters

    @property
    def keyable(self):
        """
        Getter method that returns the keyable flag of this attribute.

        :rtype: bool
        """

        return self._parser.getFlag('-k', False)

    @keyable.setter
    def keyable(self, keyable):
        """
        Setter method that updates the keyable flag of this attribute.

        :type keyable: bool
        :rtype: None
        """

        self._parser['-k'] = keyable

    @property
    def channelBox(self):
        """
        Getter method that returns the channelBox flag of this attribute.

        :rtype: bool
        """

        return self._parser.getFlag('-cb', False)

    @channelBox.setter
    def channelBox(self, channelBox):
        """
        Setter method that updates the channelBox flag of this attribute.

        :type channelBox: bool
        :rtype: None
        """

        self._parser['-cb'] = channelBox

    @property
    def hidden(self):
        """
        Getter method that returns the hidden flag of this attribute.

        :rtype: bool
        """

        return self._parser.getFlag('-h', False)

    @hidden.setter
    def hidden(self, hidden):
        """
        Setter method that updates the hidden flag of this attribute.

        :type hidden: bool
        :rtype: None
        """

        self._parser['-h'] = hidden

    @property
    def usedAsFilename(self):
        """
        Getter method that returns the usedAsFilename flag of this attribute.

        :rtype: bool
        """

        return self._parser.getFlag('-uaf', False)

    @usedAsFilename.setter
    def usedAsFilename(self, usedAsFilename):
        """
        Setter method that updates the usedAsFilename flag of this attribute.

        :type usedAsFilename: bool
        :rtype: None
        """

        self._parser['-uaf'] = usedAsFilename

    @property
    def usedAsColor(self):
        """
        Getter method that returns the usedAsColor flag of this attribute.

        :rtype: bool
        """

        return self._parser.getFlag('-uac', False)

    @usedAsColor.setter
    def usedAsColor(self, usedAsColor):
        """
        Setter method that updates the usedAsColor flag of this attribute.

        :type usedAsColor: bool
        :rtype: None
        """

        self._parser['-uac'] = usedAsColor

    @property
    def minValue(self):
        """
        Getter method that returns the minimum value of this attribute.

        :rtype: Union[int, float]
        """

        return self._parser.getFlag('-min')

    @minValue.setter
    def minValue(self, minValue):
        """
        Setter method that updates the minimum value of this attribute.

        :type: minValue: Union[int, float]
        :rtype: None
        """

        self._parser['-min'] = minValue

    @property
    def maxValue(self):
        """
        Getter method that returns the maximum value of this attribute.

        :rtype: Union[int, float]
        """

        return self._parser.getFlag('-max')

    @maxValue.setter
    def maxValue(self, maxValue):
        """
        Setter method that updates the maximum value of this attribute.

        :type: maxValue: Union[int, float]
        :rtype: None
        """

        self._parser['-max'] = maxValue

    @property
    def softMinValue(self):
        """
        Getter method that returns the soft minimum value of this attribute.

        :rtype: Union[int, float]
        """

        return self._parser.getFlag('-smn')

    @softMinValue.setter
    def softMinValue(self, softMinValue):
        """
        Setter method that updates the soft minimum value of this attribute.

        :type: softMinValue: Union[int, float]
        :rtype: None
        """

        self._parser['-smn'] = softMinValue

    @property
    def softMaxValue(self):
        """
        Getter method that returns the soft maximum value of this attribute.

        :rtype: Union[int, float]
        """

        return self._parser.getFlag('-smx')

    @softMaxValue.setter
    def softMaxValue(self, softMaxValue):
        """
        Setter method that updates the soft maximum value of this attribute.

        :type: softMaxValue: Union[int, float]
        :rtype: None
        """

        self._parser['-smx'] = softMaxValue

    @property
    def defaultValue(self):
        """
        Getter method that returns the default value of this attribute.

        :rtype: object
        """

        return self._parser.getFlag('-dv')

    @defaultValue.setter
    def defaultValue(self, defaultValue):
        """
        Setter method that updates the default value of this attribute.

        :type defaultValue: object
        :rtype: None
        """

        self._parser['-dv'] = defaultValue

    @property
    def isDynamic(self):
        """
        Getter method that evaluates whether this is a user defined attribute.

        :rtype: bool
        """

        return self._dynamic

    @property
    def isCompound(self):
        """
        Getter method that evaluates whether this attribute is made up of child attributes.

        :rtype: bool
        """

        return len(self.children) > 0

    @property
    def isTyped(self):
        """
        Getter method that evaluates whether this attribute represents a typed value.

        :rtype: bool
        """

        return self._parser.hasFlag('-dt')

    @property
    def isArray(self):
        """
        Getter method that evaluates whether this attribute represents an array.

        :rtype: bool
        """

        return self.multi

    @property
    def hasMinValue(self):
        """
        Getter method that evaluates whether this attribute has a minimum value.

        :rtype: bool
        """

        return self.minValue is not None

    @property
    def hasMaxValue(self):
        """
        Getter method that evaluates whether this attribute has a maximum value.

        :rtype: bool
        """

        return self.maxValue is not None

    @property
    def hasSoftMinValue(self):
        """
        Getter method that evaluates whether this attribute has a soft minimum value.

        :rtype: bool
        """

        return self.softMinValue is not None

    @property
    def hasSoftMaxValue(self):
        """
        Getter method that evaluates whether this attribute has a soft maximum value.

        :rtype: bool
        """

        return self.softMaxValue is not None

    @property
    def isClamped(self):
        """
        Getter method that evaluates whether this attribute is clamped.

        :rtype: bool
        """

        return self.hasMinValue or self.hasMaxValue
    # endregion

    # region Callbacks
    def parentChanged(self, oldParent, newParent):
        """
        Callback method that cleans up any parent/child references.

        :type oldParent: AsciiObject
        :type newParent: AsciiObject
        :rtype: None
        """

        # Remove self from former parent
        #
        if oldParent is not None:

            oldParent.children.remove(self)

        # Append self to new parent
        #
        if newParent is not None:

            newParent.children.appendIfUnique(self)

    def childAdded(self, index, child):
        """
        Adds a reference to this object to the supplied child.

        :type index: int
        :type child: AsciiNode
        :rtype: None
        """

        child.parent = self

    def childRemoved(self, child):
        """
        Removes the reference of this object from the supplied child.

        :type child: AsciiNode
        :rtype: None
        """

        child.parent = None
    # endregion

    # region Methods
    def update(self, items):
        """
        Copies any properties from the supplied items.

        :type items: dict
        :rtype: None
        """

        # Check for any keyword arguments
        #
        for (key, value) in items.items():

            # Check if class has attribute
            #
            if not hasattr(self.__class__, key):

                continue

            # Check if this is a property
            #
            func = getattr(self.__class__, key)

            if isinstance(func, property):

                func.fset(self, value)

    def getDataType(self):
        """
        Returns the data wrapper for this attribute.

        :rtype: type
        """

        return asciidata.getDataType(self)

    def getAddAttrCmd(self):
        """
        Returns the command string used to create this attribute.

        :rtype: str
        """

        return self._parser.toString()
    # endregion


def listPluginAttributes(typeName):
    """
    Returns a list of static attributes that belong to the given node type.

    :type typeName: str
    :rtype: hashtable.HashTable
    """

    # Collect all static attribute names
    #
    nodeClass = om.MNodeClass(typeName)
    numAttributes = nodeClass.attributeCount

    attributes = hashtable.HashTable()

    for i in range(numAttributes):

        # Collect attribute properties from command
        #
        obj = nodeClass.attribute(i)
        command = om.MFnAttribute(obj).getAddAttrCmd(False)

        args = asciiargparser.AsciiArgParser(command)

        # Create new attribute
        #
        attribute = AsciiAttribute(args, dynamic=False)

        attributes[attribute.shortName] = attribute
        attributes[attribute.longName] = attribute

        # Check if attribute has a parent
        #
        parent = args.getFlag('-p')

        if parent is not None:

            attribute.parent = attributes[parent]

    return attributes
