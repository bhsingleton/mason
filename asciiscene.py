import os

from maya import cmds as mc
from maya.api import OpenMaya as om
from datetime import datetime
from collections import deque, namedtuple, defaultdict

from . import asciibase, asciiargparser, asciinode

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


Requirement = namedtuple('Requirement', ['plugin', 'version', 'nodeType', 'dataType'])


class AsciiRegistry(object):
    """
    Ascii container class used to lookup nodes.
    """

    # region Dunderscores
    __slots__ = ('nodes', 'names', 'types', 'uuids')

    def __init__(self):
        """
        Private method called after a new instance has been created.
        """

        # Call parent method
        #
        super(AsciiRegistry, self).__init__()

        # Declare public variables
        #
        self.nodes = {}
        self.names = {}
        self.types = defaultdict(list)
        self.uuids = {}
    # endregion

    # region Methods
    def iterNodes(self):
        """
        Returns a generator that yields all nodes.

        :rtype: iter
        """

        return self.nodes.values()

    def iterTopLevelNodes(self):
        """
        Returns a generator that yields all top level nodes.

        :rtype: iter
        """

        # Iterate through nodes
        #
        for node in self.iterNodes():

            # Check if node has a parent
            #
            if node.parent is None:

                yield node

            else:

                continue

    def walk(self):
        """
        Walks through the entire ascii tree.
        Be warned this can be an expensive operation depending on the file size!

        :rtype: iter
        """

        # Walk through hierarchy
        #
        queue = deque(self.iterTopLevelNodes())

        while len(queue):

            # Pop node at start of queue
            #
            node = queue.popleft()
            yield node

            # Yield from node's descendants
            #
            yield from node.iterDescendants()

    def iterNodesByType(self, nodeType):
        """
        Returns a generator that yields nodes of a specific type.
        TODO: Add support for derived node types.

        :type nodeType: str
        :rtype: iter
        """

        # Iterate through nodes
        #
        for node in self.iterNodes():

            # Check node type
            #
            if node.type == nodeType:

                yield node

            else:

                continue

    def iterDefaultNodes(self):
        """
        Returns a generator that yields all default nodes.

        :rtype: iter
        """

        # Iterate through nodes
        #
        for node in self.iterTopLevelNodes():

            # Check if this is default node
            #
            if node.isDefaultNode:

                yield node

            else:

                continue

    def iterUserNodes(self):
        """
        Returns a generator that yields all user created nodes.

        :rtype: iter
        """

        # Iterate through nodes
        #
        for node in self.walk():

            # Check if this is default node
            #
            if not node.isDefaultNode:

                yield node

            else:

                continue

    def getNodeByHashCode(self, hashCode):
        """
        Returns the node associated with the given hash code.

        :type hashCode: int
        :rtype: asciinode.AsciiNode
        """

        return self.nodes.get(hashCode, None)

    def getNodeByName(self, name):
        """
        Returns the node associated with the given name.
        This should should also include the namespace.

        :type name: str
        :rtype: asciinode.AsciiNode
        """

        hashCode = self.names.get(name, 0)
        return self.getNodeByHashCode(hashCode)

    def getNodeByUUID(self, uuid):
        """
        Returns the node associated with the given UUID.

        :type uuid: str
        :rtype: asciinode.AsciiNode
        """

        hashCode = self.uuids.get(uuid, 0)
        return self.getNodeByHashCode(hashCode)

    def hasUUID(self, uuid):
        """
        Evaluates whether or not the given UUID is in use.

        :type uuid: str
        :rtype: bool
        """

        return self.uuids.get(uuid, None) is not None

    def generateUUID(self, *args):
        """
        Generates a UUID that is safe to use inside the scene.
        You can also uniquify your own UUID by supplying it as an argument.

        :rtype: str
        """

        # Check number of arguments
        #
        numArgs = len(args)
        uuid = None

        if numArgs == 1:

            uuid = args[0]

        else:

            uuid = om.MUuid().generate().asString()

        # Iterate until UUID is truly unique
        #
        while self.hasUUID(uuid):

            uuid = om.MUuid().generate().asString()

        return uuid
    # endregion


class AsciiScene(asciibase.AsciiBase):
    """
    Overload of AsciiBase used to interface with the ascii scene file.
    All runtime commands are executed from the ascii file parser.
    At this time there is very little support for relationships or namespaces.
    """

    # region Dunderscores
    __slots__ = (
        '_filePath',
        '_selection',
        'registry',
        'requirements',
        'fileInfo',
        'currentUnit',
        'relationships'
    )

    __codeset__ = 1252  # TODO: Find a better way to track this!

    def __init__(self, filePath, **kwargs):
        """
        Private method called after a new instance has been created.

        :type filePath: str
        :rtype: None
        """

        # Call parent method
        #
        super(AsciiScene, self).__init__(**kwargs)

        # Declare private variables
        #
        self._filePath = filePath
        self._selection = []

        # Declare public variables
        #
        self.registry = AsciiRegistry()
        self.requirements = deque()
        self.fileInfo = {}
        self.currentUnit = dict.fromkeys(('linear', 'angle', 'time'))
        self.relationships = deque()

        # Create default nodes
        #
        for nodeName in mc.ls(defaultNodes=True):

            self.createNode(mc.nodeType(nodeName), name=nodeName, default=True, skipSelect=True)

    def __str__(self):
        """
        Private method that stringifies this instance.

        :rtype: str
        """

        return self.filePath

    def __repr__(self):
        """
        Private method that returns a string representation of this instance.

        :rtype: str
        """

        return f'<{self.className}:{self.filename} @ {self.fileInfo["UUID"]}>'

    def __dumps__(self):
        """
        Returns a list of command line strings that can be serialized.
        TODO: There's a bug where calling 'saveAs' with a different filename will not reflect in the file header.

        :rtype: list[str]
        """

        # Concatenate file header
        #
        time = datetime.today()

        commands = [
            f'//Maya ASCII {self.version} scene',
            f'//Name: {self.filename}',
            f'//Last modified: {time.strftime("%A, %B %d, %Y")}, {time.strftime("%H:%M:%S %p")}',
            f'//Codeset: {self.__codeset__}'
        ]

        # Append scene specific commands
        #
        commands.extend(self.getRequiresCmds())
        commands.append(self.getCurrentUnitCmd())
        commands.extend(self.getFileInfoCmds())

        # Append commands from user created nodes
        #
        connections = []

        for node in self.registry.iterUserNodes():

            commands.extend(node.__dumps__())
            connections.extend(node.getConnectAttrCmds())

        # Append commands from default nodes
        #
        for node in self.registry.iterDefaultNodes():

            strings = node.__dumps__()
            numStrings = len(strings)

            if numStrings > 1:

                commands.extend(strings)

            connections.extend(node.getConnectAttrCmds())

        # Append relationship commands
        #
        commands.extend([x.command for x in self.relationships])
        commands.extend(connections)

        # Append closing comment
        #
        commands.append(f'// End of {self.filename}')

        return commands
    # endregion

    # region Properties
    @property
    def filePath(self):
        """
        Getter method that returns the file path for this scene.

        :rtype: str
        """

        return self._filePath

    @filePath.setter
    def filePath(self, filePath):
        """
        Setter method that updates the file path for this scene.

        :type filePath: str
        :rtype: None
        """

        self._filePath = filePath

    @property
    def filename(self):
        """
        Getter method that returns the filename for this scene.

        :rtype: str
        """

        return os.path.split(self._filePath)[-1]

    @filename.setter
    def filename(self, filename):
        """
        Setter method that updates the filename for this scene.

        :type filename: str
        :rtype: None
        """

        self._filePath = os.path.join(self.directory, filename)

    @property
    def name(self):
        """
        Getter method that returns the name of the scene.

        :rtype: str
        """

        return os.path.splitext(self.filename)[0]

    @property
    def directory(self):
        """
        Getter method that returns the directory for this scene.

        :rtype: str
        """

        return os.path.dirname(self._filePath)

    @property
    def version(self):
        """
        Getter method that returns the version this file is derived from.

        :rtype: str
        """

        return self.fileInfo['version']

    @property
    def uuid(self):
        """
        Getter method that returns the scene UUID.

        :rtype: str
        """

        return self.fileInfo['UUID']

    @property
    def selection(self):
        """
        Getter method used to return the active selection.
        This value changes as a file is being read in.

        :rtype: list[asciinode.AsciiNode]
        """

        return self._selection

    @selection.setter
    def selection(self, nodes):
        """
        Setter method used to update the active selection.

        :type nodes: list[asciinode.AsciiNode]
        :rtype: None
        """

        self._selection = nodes
    # endregion

    # region Methods
    def nodes(self):
        """
        Getter method that returns a list of top level nodes.

        :rtype: list[asciinode.AsciiNode]
        """

        return list(self.iterNodes())

    def iterNodes(self):
        """
        Returns a generator that can iterate through all of the top level nodes.

        :rtype: iter
        """

        return self.registry.iterTopLevelNodes()

    def walk(self):
        """
        Walks through the entire ascii tree.
        Be warned this can be an expensive operation depending on the file size!

        :rtype: iter
        """

        return self.registry.walk()

    def getNodeByDagPath(self, dagPath):
        """
        Returns a node associated with the given dag path.

        :type dagPath: list[str]
        :rtype: asciinode.AsciiNode
        """

        # Iterate through path
        #
        node = None
        children = self.nodes

        for name in dagPath:

            # Collect nodes with name
            #
            found = [x for x in children if x.name == name]
            numFound = len(found)

            if numFound == 0:

                return

            elif numFound == 1:

                node = found[0]
                children = node.children

            else:

                raise TypeError(f'Duplicate node names detected in dag path: {dagPath}!')

        return node

    def getNodeByName(self, fullPathName):
        """
        Returns a node associated with the given name.

        :type fullPathName: str
        :rtype: asciinode.AsciiNode
        """

        # Check if this is a fully qualified path name
        #
        paths = fullPathName.split('|')
        numPaths = len(paths)

        if numPaths == 1:

            namespace, name = self.splitName(fullPathName)
            absoluteName = f'{namespace}:{name}'

            return self.registry.getNodeByName(absoluteName)

        else:

            return self.getNodeByDagPath(paths)

    def getNodesByType(self, nodeType):
        """
        Returns a list of nodes that are derived from the given type name.

        :type nodeType: str
        :rtype: list[asciinode.AsciiNode]
        """

        return list(self.registry.iterNodesByType(nodeType))

    def requires(self, plugin, version, nodeType=None, dataType=None):
        """
        Updates the file dependencies.

        :type plugin: str
        :type version: str
        :type nodeType: str
        :type dataType: str
        :rtype: None
        """

        self.requirements.append(Requirement(plugin, version, nodeType, dataType))

    def createNode(self, typeName, name='', parent=None, default=False, skipSelect=True):
        """
        Creates a new ascii node.

        :type typeName: str
        :type name: str
        :type parent: asciinode.AsciiNode
        :type default: bool
        :type skipSelect: bool
        :rtype: asciinode.AsciiNode
        """

        # Create new node
        #
        namespace, name = self.splitName(name)
        log.info(f'Creating node: {namespace}:{name}')

        node = asciinode.AsciiNode(
            typeName,
            name=name,
            namespace=namespace,
            parent=parent,
            default=default,
            scene=self.weakReference()
        )

        self.registry.nodes[node.hashCode()] = node  # This is the only hard reference we allow!

        # Check if node should be selected
        #
        if not skipSelect:

            self.selection = [node]

        return node

    def select(self, *names, replace=True):
        """
        Selects the nodes associated with the given names.

        :type replace: bool
        :rtype: None
        """

        # Get node from name
        #
        nodes = [self.getNodeByName(x) for x in names]

        if replace:

            self.selection = nodes

        else:

            self.selection.extend(nodes)

    def getRequiresCmds(self):
        """
        Returns a list of command string that can recreate the current scene dependencies.

        :rtype: list[str]
        """

        # Iterate through requirements
        #
        numCommands = len(self.requirements)
        commands = [None] * numCommands

        for (i, requirement) in enumerate(self.requirements):

            # Append arguments to parser
            #
            parser = asciiargparser.AsciiArgParser('requires')
            parser[0] = requirement.plugin
            parser[1] = requirement.version

            # Check if node type is valid
            #
            if requirement.nodeType is not None:

                parser['-nodeType'] = requirement.nodeType

            # Check if data type is valid
            #
            if requirement.dataType is not None:

                parser['-dataType'] = requirement.dataType

            # Concatenate command string
            #
            commands[i] = parser.toString()

        return commands

    def getCurrentUnitCmd(self):
        """
        Returns a command string that can recreate the current scene units.

        :rtype: str
        """

        return 'currentUnit -l {linear} -a {angle} -t {time};'.format(
            linear=self.currentUnit['linear'],
            angle=self.currentUnit['angle'],
            time=self.currentUnit['time']
        )

    def getFileInfoCmds(self):
        """
        Returns a list of command strings that can recreate the current scene info.

        :rtype: list[str]
        """

        return [f'fileInfo "{key}" "{value}";' for (key, value) in self.fileInfo.items()]

    def getFileCmds(self):
        """
        Returns a list of command strings that can recreate the scene references.

        :rtype: list[str]
        """

        return []

    def saveAs(self, filePath):
        """
        Saves any changes to the supplied file path.

        :type filePath: str
        :rtype: None
        """

        log.info(f'Saving ASCII file to: {filePath}')

        with open(filePath, 'w') as asciiFile:

            for line in self.__dumps__():

                asciiFile.write(f'{line}\r')

        log.info('DONE')

    def save(self):
        """
        Saves any changes made to this scene.

        :rtype: None
        """

        self.saveAs(self.filePath)
    # endregion
