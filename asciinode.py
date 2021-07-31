from . import asciitreemixin, asciiattribute, asciiplug
from .collections import hashtable, weakreflist, notifylist

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class AsciiNode(asciitreemixin.AsciiTreeMixin):
    """
    Overload of AsciiTreeMixin used to interface with scene nodes.
    """

    __slots__ = (
        '_scene',
        '_name',
        '_namespace',
        '_uuid',
        '_type',
        '_parent',
        '_children',
        '_locked',
        '_default',
        '_attributes',
        '_plugs',
        '_database',
        '_connections'
    )

    __attributes__ = {}  # Used for static attributes

    def __init__(self, typeName, **kwargs):
        """
        Private method called after a new instance is created.

        :type typeName: str
        :keyword scene: asciiscene.AsciiScene
        :rtype: None
        """

        # Call parent method
        #
        super(AsciiNode, self).__init__()

        # Declare private variables
        #
        self._scene = kwargs.get('scene', self.nullWeakReference)
        self._name = ''
        self._namespace = ''
        self._uuid = ''
        self._type = typeName
        self._parent = self.nullWeakReference
        self._children = notifylist.NotifyList(cls=weakreflist.WeakRefList)
        self._locked = False
        self._attributes = hashtable.HashTable()  # Used for dynamic attributes
        self._plugs = hashtable.HashTable()
        self._connections = []
        self._default = kwargs.get('default', False)

        # Setup child notifies
        #
        self._children.addCallback('itemAdded', self.childAdded)
        self._children.addCallback('itemRemoved', self.childRemoved)

        # Declare public variables
        #
        self.parent = kwargs.get('parent', None)
        self.name = kwargs.get('name', '')
        self.namespace = kwargs.get('namespace', '')
        self.uuid = kwargs.get('uuid', '')

        # Initialize node attributes
        #
        self.initialize()

    def __str__(self):
        """
        Private method that returns a string representation of this instance.

        :rtype: str
        """

        return f'<{self.__class__.__module__}.{self.__class__.__name__} object: {self.absoluteName()}>'

    def __getitem__(self, key):
        """
        Private method that returns the plug associated with the supplied key.

        :type key: str
        :rtype: asciiplug.AsciiPlug
        """

        return self.findPlug(key)

    def __dumps__(self):
        """
        Returns a list of command line strings that can be serialized.

        :rtype: list[str]
        """

        # Evaluate which commands to concatenate
        #
        commands = []

        if self.isDefaultNode:

            commands.append(self.getSelectCmd())

        else:

            commands.append(self.getCreateNodeCmd())
            commands.append(self.getRenameCmd())

        # Concatenate lockNode command
        # But only if the node has actually been locked!
        #
        if self.isLocked:

            commands.append(self.getLockNodeCmd())

        # Concatenate attribute related commands
        #
        commands.extend(self.getAddAttrCmds())
        commands.extend(self.getSetAttrCmds())

        return commands

    @property
    def scene(self):
        """
        Returns the scene this object is derived from.

        :rtype: mason.asciiscene.AsciiScene
        """

        return self._scene()

    @property
    def name(self):
        """
        Getter method that returns the name of this node.

        :rtype: str
        """

        return self._name

    @name.setter
    def name(self, name):
        """
        Setter method updates the name of this node.

        :type name: str
        :rtype: None
        """

        # Check for redundancy
        #
        newName = self.stripAll(name)
        oldName = self._name

        if newName != oldName:

            self._name = newName
            self.nameChanged(oldName, newName)

    def nameChanged(self, oldName, newName):
        """
        Callback method for any name changes made to this node.

        :type oldName: str
        :type newName: str
        :rtype: None
        """

        # Remove previous name from registry
        #
        absoluteName = f'{self.namespace}:{oldName}'
        hashCode = self.scene.registry.names.get(absoluteName, None)

        if hashCode == self.hashCode():

            del self.scene.registry.names[absoluteName]

        # Append new name to registry
        #
        absoluteName = f'{self.namespace}:{newName}'
        self.scene.registry.names[absoluteName] = self.hashCode()

    @property
    def namespace(self):
        """
        Getter method that returns the namespace this node belongs to.

        :rtype: str
        """

        return self._namespace

    @namespace.setter
    def namespace(self, namespace):
        """
        Setter method updates the namespace this node belongs to.

        :type namespace: str
        :rtype: None
        """

        # Check for redundancy
        #
        oldNamespace = self._namespace
        newNamespace = '' if namespace == ':' else namespace

        if newNamespace != oldNamespace:

            self._namespace = newNamespace
            self.namespaceChanged(oldNamespace, newNamespace)

    def namespaceChanged(self, oldNamespace, newNamespace):
        """
        Callback method for any namespace changes made to this node.

        :type oldNamespace: str
        :type newNamespace: str
        :rtype: None
        """

        # Remove previous name from registry
        #
        absoluteName = f'{oldNamespace}:{self.name}'
        hashCode = self.scene.registry.names.get(absoluteName, None)

        if hashCode == self.hashCode():

            del self.scene.registry.names[absoluteName]

        # Append new name to registry
        #
        absoluteName = f'{newNamespace}:{self.name}'
        self.scene.registry.names[absoluteName] = self.hashCode()

    def absoluteName(self):
        """
        Returns the bare minimum required to be a unique name.

        :rtype: str
        """

        if len(self.namespace) > 0:

            return f'{self.namespace}:{self.name}'

        else:

            return self.name

    @property
    def parent(self):
        """
        Getter method that returns the parent for this object.

        :rtype: AsciiNode
        """

        return self._parent()

    @parent.setter
    def parent(self, parent):
        """
        Setter method that updates the parent for this object.

        :type parent: AsciiNode
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

        if isinstance(parent, AsciiNode):

            self._parent = parent.weakReference()

        elif isinstance(parent, str):

            self.parent = self.scene.registry.getNodeByName(parent)

        elif parent is None:

            self._parent = self.nullWeakReference

        else:

            raise TypeError(f'parent.setter() expects an AsciiNode ({type(parent).__name__} given)!')

        # Cleanup any old references
        #
        self.parentChanged(oldParent, parent)

    def parentChanged(self, oldParent, newParent):
        """
        Callback method that cleans up any parent/child references.

        :type oldParent: AsciiNode
        :type newParent: AsciiNode
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

    @property
    def children(self):
        """
        Getter method that returns the children belonging to this object.

        :rtype: weakreflist.WeakRefList
        """

        return self._children

    def childAdded(self, index, child):
        """
        Adds a reference to this object to the supplied child.

        :type index: int
        :type child: AsciiNode
        :rtype: None
        """

        if child.parent is not self:

            child.parent = self

    def childRemoved(self, child):
        """
        Removes the reference of this object from the supplied child.

        :type child: AsciiNode
        :rtype: None
        """

        child.parent = None

    @property
    def type(self):
        """
        Getter method that returns the name of this node type.

        :rtype: str
        """

        return self._type

    @property
    def uuid(self):
        """
        Getter method that returns the UUID for this node.

        :rtype: str
        """

        return self._uuid

    @uuid.setter
    def uuid(self, uuid):
        """
        Setter method that updates the UUID for this node.

        :type uuid: str
        :rtype: None
        """

        # Check for redundancy
        #
        newUUID = self.scene.registry.generateUUID(uuid)
        oldUUID = self._uuid

        if newUUID != oldUUID:

            self._uuid = newUUID
            self.uuidChanged(oldUUID, newUUID)

    def uuidChanged(self, oldUUID, newUUID):
        """
        Callback method for any namespace changes made to this node.

        :type oldUUID: str
        :type newUUID: str
        :rtype: None
        """

        # Remove previous uuid from registry
        #
        hashCode = self.scene.registry.uuids.get(oldUUID, None)

        if hashCode == self.hashCode():

            del self.scene.registry.uuids[oldUUID]

        # Append new uuid to registry
        #
        self.scene.registry.uuids[newUUID] = self.hashCode()

    @property
    def isLocked(self):
        """
        Getter method that returns the lock state of this node.

        :rtype: int
        """

        return self._locked

    @isLocked.setter
    def isLocked(self, locked):
        """
        Setter method that updates the lock state of this node.

        :type locked: bool
        :rtype: None
        """

        self._locked = bool(locked)

    @property
    def isDefaultNode(self):
        """
        Getter method that evaluates whether this is a default node.

        :rtype: bool
        """

        return self._default

    def initialize(self):
        """
        Initializes the attributes and plugs for this node.

        :rtype: None
        """

        # Check if static attributes exist
        # If not then go ahead and initialize them
        #
        attributes = self.__attributes__.get(self.type)

        if attributes is None:

            attributes = asciiattribute.listPlugin(self.type)
            self.__attributes__[self.type] = attributes

    @property
    def database(self):
        """
        Getter method that returns the database for this node.

        :rtype: asciidatabase.AsciiDatabase
        """

        return self._database

    @property
    def plugs(self):
        """
        Getter method that returns the plugs that are currently in use.

        :rtype: hashtable.HashTable
        """

        return self._plugs

    def iterTopLevelPlugs(self):
        """
        Iterates through all of the top-level plugs.
        Please note that plugs are created on demand so don't expect a complete list from this generator!

        :rtype: iter
        """

        # Iterate through attributes
        #
        for attribute in self.listAttr(fromPlugin=True, userDefined=True).values():

            # Check if this is a top level parent
            #
            if attribute.parent is not None:

                continue

            # Yield associated plug
            #
            plug = self._plugs.get(attribute.shortName, None)

            if plug is not None:

                yield plug

            else:

                continue

    def dagPath(self):
        """
        Returns a dag path for this node.

        :rtype: str
        """

        if self.parent is not None:

            return '|'.join([x.absoluteName() for x in self.trace()])

        else:

            return self.name

    def attribute(self, name):
        """
        Returns an ascii attribute with the given name.

        :type name: str
        :rtype: asciiattribute.AsciiAttribute
        """

        return self.listAttr(fromPlugin=True, userDefined=True).get(name, None)

    def listAttr(self, fromPlugin=False, userDefined=False):
        """
        Returns a list of attributes derived from this node.

        :type fromPlugin: bool
        :type userDefined: bool
        :rtype: hashtable.HashTable
        """

        # Check if plugin defined attributes should be returned
        #
        attributes = hashtable.HashTable()

        if fromPlugin:

            attributes.update(self.__class__.__attributes__[self.type])

        # Check if user defined attributes should be returned
        #
        if userDefined:

            attributes.update(self._attributes)

        return attributes

    def addAttr(self, *args, **kwargs):
        """
        Adds a dynamic attribute to this node.
        This function accepts two different sets of arguments.
        You can either supply a fully formed AsciiAttribute.
        Or you can pass all of the keywords required to create one.

        :rtype: None
        """

        # Check number of arguments
        #
        numArgs = len(args)
        numKwargs = len(kwargs)

        if numArgs == 1:

            # Store reference to attribute
            #
            attribute = args[0]

            self._attributes[attribute.shortName] = attribute
            self._attributes[attribute.longName] = attribute

        elif numKwargs > 0:

            # Create new attribute from kwargs
            #
            attribute = asciiattribute.AsciiAttribute(**kwargs)
            self.addAttr(attribute)

        else:

            raise TypeError(f'addAttr() expects 1 argument ({numArgs} given)!')

    def setAttr(self, plug, value):
        """
        Assigns the supplied value to the given plug.

        :type plug: Union[str, asciiplug.AsciiPlug]
        :type value: Any
        :rtype: None
        """

        # Check plug type
        #
        if isinstance(plug, str):

            plug = self.findPlug(plug)

        # Assign value to plug
        #
        plug.setValue(value)

    def connectAttr(self, source, destination):
        """
        Connects the two supplied plugs together.

        :type source: Union[str, asciiplug.AsciiPlug]
        :type destination: Union[str, asciiplug.AsciiPlug]
        :rtype: None
        """

        # Check source type
        #
        if isinstance(source, str):

            source = self.findPlug(source)

        # Check destination type
        #
        if isinstance(destination, str):

            destination = self.findPlug(destination)

        # Connect plugs
        #
        source.connect(destination)

    def findPlugs(self, path):
        """
        Returns a list of plugs from the supplied string path.

        :type path: str
        :rtype: list[asciiplug.AsciiPlug]
        """

        return asciiplug.AsciiPlugPath(f'{self.absoluteName()}.{path}', scene=self.scene).evaluate()

    def findPlug(self, path):
        """
        Returns the plug associated with the given name.
        If more than one plug is found then a type error is raised.

        :type path: str
        :rtype: asciiplug.AsciiPlug
        """

        plugs = self.findPlugs(path)
        numPlugs = len(plugs)

        if numPlugs == 0:

            return None

        elif numPlugs == 1:

            return plugs[0]

        else:

            raise TypeError('findPlug() multiple plugs found!')

    def legalConnection(self, plug, otherPlug):
        """
        Evaluates whether or not the connection between these two plugs is valid.
        TODO: Implement this behaviour!

        :type plug: asciiplug.AsciiPlug
        :type otherPlug: asciiplug.AsciiPlug
        :rtype: bool
        """

        return True

    def connectionMade(self, plug, otherPlug):
        """
        Callback method for any connection changes made to this node.

        :type plug: asciiplug.AsciiPlug
        :type otherPlug: asciiplug.AsciiPlug
        :rtype: None
        """

        self._connections.append(otherPlug.weakReference())

    def legalDisconnection(self, plug, otherPlug):
        """
        Evaluates whether or not the disconnection between these two plugs is valid.
        TODO: Implement this behaviour!

        :type plug: asciiplug.AsciiPlug
        :type otherPlug: asciiplug.AsciiPlug
        :rtype: bool
        """

        return True

    def connectionBroken(self, plug, otherPlug):
        """
        Callback method for any disconnection changes made to this node.

        :type plug: asciiplug.AsciiPlug
        :type otherPlug: asciiplug.AsciiPlug
        :rtype: None
        """

        self._connections.remove(otherPlug.weakReference())

    def getCreateNodeCmd(self):
        """
        Returns a command string that can create this node.

        :rtype: str
        """

        # Check if node has parent
        #
        if self.parent is not None:

            return f'createNode {self.type} -s -n "{self.absoluteName()}" -p "{self.parent.absoluteName()}";'

        else:

            return f'createNode {self.type} -s -n "{self.absoluteName()}";'

    def getSelectCmd(self):
        """
        Returns a command string that can select this node.

        :rtype: str
        """

        return f'select -ne "{self.absoluteName()}";'

    def getRenameCmd(self):
        """
        Returns a command string that can rename this node's UUID.

        :rtype: str
        """

        return f'\trename -uid "{self.uuid}";'

    def getLockNodeCmd(self):
        """
        Returns a command string that can lock this node.

        :rtype: str
        """

        return f'\tlockNode -l {int(self.isLocked)};'

    def getAddAttrCmds(self):
        """
        Returns a list of commands for user-defined attributes.

        :rtype: list[str]
        """

        return [x.getAddAttrCmd() for x in self.listAttr(userDefined=True).values()]

    def getSetAttrCmds(self):
        """
        Returns a list of commands for non-default plugs.

        :rtype: list[str]
        """

        # Iterate through top-level plugs
        #
        commands = []

        for plug in self.iterTopLevelPlugs():

            commands.extend(plug.getSetAttrCmds())

        return commands

    def getConnectAttrCmds(self):
        """
        Returns a list of command strings that can recreate the outgoing connections from this node.

        :rtype: list[str]
        """

        # Iterate through known connections
        #
        numCommands = len(self._connections)
        commands = [None] * numCommands

        for (i, ref) in enumerate(self._connections):

            # Check if ref is still alive
            #
            otherPlug = ref()

            if otherPlug is None:

                continue

            # Concatenate source name
            #
            plug = otherPlug.source()
            source = plug.partialName(includeNodeName=True, useFullAttributePath=True, includeIndices=True)

            # Check if destination index matters
            #

            if otherPlug.isElement and not otherPlug.attribute.indexMatters:

                destination = otherPlug.parent.partialName(includeNodeName=True, useFullAttributePath=True, includeIndices=True)
                commands[i] = f'connectAttr "{source}" "{destination}" -na;'

            else:

                destination = otherPlug.partialName(includeNodeName=True, useFullAttributePath=True, includeIndices=True)
                commands[i] = f'connectAttr "{source}" "{destination}";'

        return commands
