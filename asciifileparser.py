from . import asciiscene, asciiargparser, asciiattribute, asciiplug, asciidata
from .decorators import timer

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class AsciiFileParser(object):
    """
    Ascii file parser designed to pass command lines into a tree builder.
    """

    __slots__ = ('filePath', 'scene')
    __comment__ = '//'
    __delimiter__ = ';'
    __escapechars__ = ''.join([chr(char) for char in range(1, 32)])

    def __init__(self, filePath):
        """
        Private method called after a new instance has been created.

        :type filePath: str
        :rtype: None
        """

        # Call parent method
        #
        super(AsciiFileParser, self).__init__()

        # Declare public variables
        #
        self.filePath = filePath
        self.scene = asciiscene.AsciiScene(self.filePath)

        # Parse file
        #
        try:

            self.__parse__()

        except Exception as exception:

            log.error(exception)
    
    @timer
    def __parse__(self, *args, **kwargs):
        """
        Private method used to parse the ascii file.

        :rtype: None
        """

        # Open ascii file in memory
        #
        with open(self.filePath, 'r') as asciiFile:

            # Iterate through lines in file
            #
            line = ''
            buffer = ''
            lineNumber = 0

            while True:

                # Check for empty string
                #
                line = asciiFile.readline().strip(self.__escapechars__)
                numChars = len(line)

                if numChars == 0:

                    break

                # Check if this is a comment
                #
                if line.startswith(self.__comment__):

                    lineNumber += 1
                    continue

                # Concatenate command line
                #
                buffer = line

                while not buffer.endswith(self.__delimiter__):

                    line = asciiFile.readline().strip(self.__escapechars__)

                    buffer += f' {line}'
                    lineNumber += 1

                # Call command delegate
                #
                parser = asciiargparser.AsciiArgParser(buffer)
                func = getattr(self.__class__, parser.name)

                log.info(f'Line[{lineNumber}]: {buffer}')
                func(self, parser)

                # Increment line number
                #
                lineNumber += 1

        # Notify user
        #
        log.info('%s[EOF]' % self.filePath)

    def file(self, parser):
        """
        Delegate for file commands.
        # TODO: Implement support for references

        :type parser: asciiargparser.AsciiArgParser
        :rtype: None
        """

        # Check reference flags
        #
        if parser.hasFlag('-rdi'):

            pass

        elif parser.hasFlag('-r'):

            pass

        else:

            pass

    def requires(self, parser):
        """
        Delegate for requires commands.

        :type parser: asciiargparser.AsciiArgParser
        :rtype: None
        """

        self.scene.requires(
            parser[0],
            parser[1],
            nodeType=parser.getFlag('-nodeType'),
            dataType=parser.getFlag('-dataType')
        )

    def fileInfo(self, parser):
        """
        Delegate for fileInfo commands.

        :type parser: asciiargparser.AsciiArgParser
        :rtype: None
        """

        key = parser[0]
        value = parser[1]

        log.info(f'File Info: {key} = {value}')
        self.scene.fileInfo[key] = value

    def currentUnit(self, parser):
        """
        Delegate for currentUnit commands.

        :type parser: asciiargparser.AsciiArgParser
        :rtype: None
        """

        self.scene.currentUnit['linear'] = parser['-l']
        self.scene.currentUnit['angle'] = parser['-a']
        self.scene.currentUnit['time'] = parser['-t']

    def createNode(self, parser):
        """
        Delegate for createNode commands.

        :type parser: asciiargparser.AsciiArgParser
        :rtype: None
        """

        # Check if there's a parent flag
        #
        parent = None

        if parser.hasFlag('-p'):

            parent = self.scene.getNodeByName(parser['-p'])

        # Create scene node
        #
        self.scene.createNode(
            parser[0],
            name=parser['-n'],
            parent=parent,
            skipSelect=parser.getFlag('-ss', False)
        )

    def select(self, parser):
        """
        Delegate for select commands.

        :type parser: asciiargparser.AsciiArgParser
        :rtype: None
        """

        self.scene.select(parser[0], replace=True)

    def rename(self, parser):
        """
        Delegate for rename commands.

        :type parser: asciiargparser.AsciiArgParser
        :rtype: None
        """

        self.scene.selection[0].uuid = parser[0]

    def lockNode(self, parser):
        """
        Delegate for lockNode commands.

        :type parser: asciiargparser.AsciiArgParser
        :rtype: None
        """

        self.scene.selection[0].isLocked = bool(parser.getFlag('-l'))

    def addAttr(self, parser):
        """
        Delegate for addAttr commands.

        :type parser: asciiargparser.AsciiArgParser
        :rtype: None
        """

        # Create dynamic attribute
        #
        attribute = asciiattribute.AsciiAttribute(parser, dynamic=True)

        # Check if attribute has parent
        #
        node = self.scene.selection[0]
        parentName = parser.getFlag('-p')

        if parentName is not None:

            attributes = node.listAttr(userDefined=True)
            attribute.parent = attributes[parentName]

        # Assign attribute to node
        #
        node.addAttr(attribute)

    def setAttr(self, parser):
        """
        Delegate for setAttr commands.

        :type parser: asciiargparser.AsciiArgParser
        :rtype: None
        """

        # Check number of arguments
        #
        name = parser[0]
        path = asciiplug.AsciiPlugPath(name, scene=self.scene)

        plugs = path.evaluate()
        numPlugs = len(plugs)

        if numPlugs == 0:

            log.error(f'Unable to locate plug: {name}')
            return

        # Check for keyable flag
        #
        keyable = parser.getFlag('-k')

        if keyable is not None:

            plugs[0].isKeyable = keyable

        # Check for locked flag
        #
        locked = parser.getFlag('-l')

        if locked is not None:

            plugs[0].isLocked = locked

        # Check for size flag
        # The capacity flag takes priority over the size flag
        #
        size = parser.getFlag('-ch', parser.getFlag('-s'))

        if size is not None:

            plugs[0].size = size

        # Check if there are any arguments
        # Be sure to not to count the plug name!
        #
        numArguments = parser.numArguments - 1

        if numArguments > 0:

            # Package values using attribute type
            #
            values = parser.package(path)
            numValues = len(values)

            if numPlugs == numValues:

                for (plug, value) in zip(plugs, values):

                    plug.setValue(value)

            else:

                log.error(f'Unable to set attribute {name}!')

    def connectAttr(self, parser):
        """
        Delegate for connectAttr commands.

        :type parser: asciiargparser.AsciiArgParser
        :rtype: None
        """

        # Locate nodes from arguments
        #
        sources = asciiplug.AsciiPlugPath(parser[0], scene=self.scene).evaluate()
        destinations = asciiplug.AsciiPlugPath(parser[1], scene=self.scene).evaluate()

        if len(sources) != 1 or len(destinations) != 1:

            log.error(f'Unable to locate plugs: {parser[0]} -> {parser[1]}')
            return

        # Get plugs from path parser
        #
        source = sources[0]
        destination = destinations[0]

        nextAvailable = parser.hasFlag('-na')

        if (destination.isArray and not destination.isElement) and nextAvailable:

            index = destination.nextAvailableIndex()
            destination = destination.elementByLogicalIndex(index)

        # Connect plugs
        #
        source.connect(destination)

    def relationship(self, parser):
        """
        Delegate for relationship commands.

        :type parser: asciiargparser.AsciiArgParser
        :rtype: None
        """

        self.scene.relationships.append(parser)
