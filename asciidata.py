import numpy

from maya.api import OpenMaya as om
from abc import ABCMeta, abstractmethod
from collections import deque
from itertools import islice, chain
from dcc.collections import sparsearray
from . import asciibase, asciiattribute

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class AsciiData(asciibase.AsciiBase, metaclass=ABCMeta):
    """
    Ascii class used to interface with user data.
    """

    # region Dunderscores
    __slots__ = ('__attribute__', '__value__')
    __default__ = None

    def __init__(self, attribute, **kwargs):
        """
        Private method called after a new instance is created.

        :type attribute: asciiattribute.AsciiAttribute
        :rtype: None
        """

        # Call parent method
        #
        super(AsciiData, self).__init__()

        # Declare class variables
        #
        self.__attribute__ = attribute.weakReference()
        self.__value__ = self.default()

    def __str__(self):
        """
        Private method that stringifies this instance.

        :rtype: str
        """

        return str(self.__value__)

    def __repr__(self):
        """
        Private method that stringifies this instance.

        :rtype: str
        """

        return f'<{self.className}({self.__value__})>'

    @classmethod
    @abstractmethod
    def __loads__(cls, value):
        """
        Returns the python equivalent of this ascii string.

        :rtype: Any
        """

        pass

    @classmethod
    @abstractmethod
    def __dumps__(cls, value):
        """
        Returns the ascii equivalent of this python object.

        :rtype: str
        """

        pass
    # endregion

    # region properties
    @property
    def attribute(self):
        """
        Getter method that returns the attribute associated with this datablock.

        :rtype: mason.asciiattribute.AsciiAttribute
        """

        return self.__attribute__()
    # endregion

    # region Methods
    def isNonDefault(self):
        """
        Evaluates whether this data has been changed.

        :rtype: bool
        """

        return not self.isEquivalent(self.default())

    def default(self):
        """
        Returns the default value for this data type.

        :rtype: Any
        """

        classDefault = self.__class__.__default__
        userDefault = self.attribute.defaultValue
        default = userDefault if userDefault is not None else classDefault

        cls = type(default)

        if callable(cls) and default is not None:

            return cls(default)

        else:

            return default

    def isEquivalent(self, other):
        """
        Evaluates whether the other value is equivalent to this one.

        :type other: Any
        :rtype: bool
        """

        return self.__value__ == other

    def get(self):
        """
        Returns the value from this data block.

        :rtype: Any
        """

        return self.__value__

    def set(self, value):
        """
        Updates the value associated in this data block.

        :type value: Any
        :rtype: None
        """

        self.__value__ = value

    @classmethod
    def readAscii(cls, strings):
        """
        Evaluates the supplied ascii string.

        :type strings: List[str]
        :rtype: List[Any]
        """

        return cls.__loads__(strings)

    def writeAscii(self):
        """
        Returns a string representation of this data type suitable for ascii serialization.

        :rtype: str
        """

        return self.__dumps__(self.get())
    # endregion


class AsciiGeneric(AsciiData):

    __slots__ = ()
    __default__ = None

    @classmethod
    def __loads__(cls, strings):

        return []

    @classmethod
    def __dumps__(cls, value):

        return ''


class AsciiNumericData(AsciiData, metaclass=ABCMeta):

    __slots__ = ()
    __data_type__ = None
    __size__ = 0

    def __getitem__(self, index):

        return self.__value__[index]

    def __setitem__(self, index, value):

        self.__value__[index] = value

    @classmethod
    def __loads__(cls, strings):

        if cls.__size__ == 0:

            return None

        elif cls.__size__ == 1:

            return numpy.array(strings, dtype=cls.__data_type__).tolist()

        else:

            return numpy.array(strings, dtype=cls.__data_type__).reshape(-1, cls.__size__).tolist()

    @classmethod
    def __dumps__(cls, value):

        if cls.__size__ == 0:

            return ''

        elif cls.__size__ == 1:

            return str(value)

        else:

            return ' '.join(value)


class AsciiBool(AsciiNumericData):

    __slots__ = ()
    __states__ = {'on': True, 'yes': True, 'true': True}
    __data_type__ = bool
    __default__ = False

    @classmethod
    def __loads__(cls, strings):

        return [cls.__states__.get(string.lower(), False) for string in strings]

    @classmethod
    def __dumps__(cls, value):

        return str(value).lower()


class AsciiInt(AsciiNumericData):

    __slots__ = ()
    __data_type__ = int
    __size__ = 1
    __default__ = 0


class AsciiInt2(AsciiInt):

    __slots__ = ()
    __size__ = 2
    __default__ = [0, 0]


class AsciiInt3(AsciiInt):

    __slots__ = ()
    __size__ = 3
    __default__ = [0, 0, 0]


class AsciiFloat(AsciiNumericData):

    __slots__ = ()
    __data_type__ = float
    __size__ = 1
    __default__ = 0.0


class AsciiFloat2(AsciiFloat):

    __slots__ = ()
    __size__ = 2
    __default__ = [0.0, 0.0, 0.0]


class AsciiFloat3(AsciiFloat):

    __slots__ = ()
    __size__ = 3
    __default__ = [0.0, 0.0, 0.0]


class AsciiFloat4(AsciiFloat):

    __slots__ = ()
    __size__ = 4
    __default__ = [0.0, 0.0, 0.0, 0.0]


class AsciiString(AsciiData):

    __slots__ = ()
    __default__ = ''

    @classmethod
    def __loads__(cls, strings):

        return [''.join(strings)]

    @classmethod
    def __dumps__(cls, value):

        return f'"{value}"'


class AsciiMatrix(AsciiData):

    __slots__ = ()
    __default__ = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]
    ]

    @property
    def isTransformation(self):

        return isinstance(self.__value__, dict)

    def isNonDefault(self):

        if not self.isTransformation:

            return self.__value__ == self.__class__.__default__

        else:

            return True

    @classmethod
    def __loads__(cls, strings):

        numStrings = len(strings)
        matrix = None

        if numStrings == 16:

            matrix = numpy.array(strings, dtype=float).reshape(4, 4).tolist()

        elif numStrings == 38:

            matrix = {
                'scale': numpy.array(strings[1:4]).astype(float),
                'rotate': numpy.array(strings[4:7]).astype(float),
                'rotateOrder': int(strings[7]),
                'translate': numpy.array(strings[8:11]).astype(float),
                'shear': numpy.array(strings[11:14]).astype(float),
                'scalePivot': numpy.array(strings[14:17]).astype(float),
                'scalePivotTranslate': numpy.array(strings[17:20]).astype(float),
                'rotatePivot': numpy.array(strings[20:23]).astype(float),
                'rotatePivotTranslate': numpy.array(strings[23:26]).astype(float),
                'rotateOrient': numpy.array(strings[26:30]).astype(float),
                'jointOrient': numpy.array(strings[30:34]).astype(float),
                'inverseParentScale': numpy.array(strings[34:37]).astype(float),
                'compensateForParentScale': bool(strings[37])
            }

        else:

            raise ValueError('Invalid number of arguments supplied to ascii matrix!')

        return [matrix]

    @classmethod
    def __dumps__(cls, value):

        if isinstance(value, dict):

            return '"xform" {scale} {rotate} {rotateOrder} {translate} {shear} {scalePivot} {scalePivotTranslate} {rotatePivot} {rotatePivotTranslate} {rotateOrient} {jointOrient} {inverseParentScale} {compensateForParentScale}'.format(
                scale=' '.join(map(str, value['scale'])),
                rotate=' '.join(map(str, value['rotate'])),
                rotateOrder=str(value['rotateOrder']),
                translate=' '.join(map(str, value['translate'])),
                shear=' '.join(map(str, value['shear'])),
                scalePivot=' '.join(map(str, value['scalePivot'])),
                scalePivotTranslate=' '.join(map(str, value['scalePivotTranslate'])),
                rotatePivot=' '.join(map(str, value['rotatePivot'])),
                rotatePivotTranslate=' '.join(map(str, value['rotatePivotTranslate'])),
                rotateOrient=' '.join(map(str, value['rotateOrient'])),
                jointOrient=' '.join(map(str, value['jointOrient'])),
                inverseParentScale=' '.join(map(str, value['inverseParentScale'])),
                compensateForParentScale=str(value['compensateForParentScale'])
            )

        else:

            return ' '.join(map(str, chain(*value)))


class AsciiIntArray(AsciiData):

    __slots__ = ()
    __default__ = om.MIntArray()

    @classmethod
    def __loads__(cls, strings):

        sizeHint = int(strings[0])
        array = om.MIntArray(sizeHint, 0)

        for i in range(sizeHint):

            array[i] = int(strings[i + 1])

        return [array]

    @classmethod
    def __dumps__(cls, value):

        numIntegers = len(value)
        integers = ' '.join(map(str, value))

        return f'{numIntegers} {integers}'


class AsciiDoubleArray(AsciiData):

    __slots__ = ()
    __default__ = om.MDoubleArray()

    @classmethod
    def __loads__(cls, strings):

        sizeHint = int(strings[0])
        array = om.MDoubleArray(sizeHint, 0.0)

        for i in range(sizeHint):

            array[i] = float(strings[i + 1])

        return [array]

    @classmethod
    def __dumps__(cls, value):

        numDoubles = len(value)
        doubles = ' '.join(map(str, value))

        return f'{numDoubles} {doubles}'


class AsciiPointArray(AsciiData):

    __slots__ = ()
    __default__ = om.MPointArray()

    @classmethod
    def __loads__(cls, strings):

        sizeHint = int(strings[0])
        array = om.MPointArray(sizeHint, om.MPoint.kOrigin)

        for (physicalIndex, logicalIndex) in enumerate(range(0, sizeHint * 4, 4)):

            array[physicalIndex] = om.MPoint(
                float(strings[logicalIndex + 1]),
                float(strings[logicalIndex + 2]),
                float(strings[logicalIndex + 3]),
                float(strings[logicalIndex + 4])
            )

        return [array]

    @classmethod
    def __dumps__(cls, value):

        numPoints = len(value)
        points = ' '.join([f'{x.x} {x.y} {x.z} {x.w}' for x in value])

        return f'{numPoints} {points}'


class AsciiVectorArray(AsciiData):

    __slots__ = ()
    __default__ = om.MVectorArray()

    @classmethod
    def __loads__(cls, strings):

        sizeHint = int(strings[0])
        array = om.MVectorArray(sizeHint, om.MVector.kZeroVector)

        for (physicalIndex, logicalIndex) in enumerate(range(0, sizeHint * 3, 3)):

            array[physicalIndex] = om.MVector(
                float(strings[logicalIndex + 1]),
                float(strings[logicalIndex + 2]),
                float(strings[logicalIndex + 3])
            )

        return [array]

    @classmethod
    def __dumps__(cls, value):

        numVectors = len(value)
        vectors = ' '.join([f'{x.x} {x.y} {x.z}' for x in value])

        return f'{numVectors} {vectors}'


class AsciiStringArray(AsciiData):

    __slots__ = ()
    __default__ = []

    @classmethod
    def __loads__(cls, strings):

        return [strings[1:]]

    @classmethod
    def __dumps__(cls, value):

        numStrings = len(value)
        strings = ' '.join(f'"{x}"' for x in value)

        return f'{numStrings} {strings}'


class AsciiSphere(AsciiData):

    __slots__ = ()

    @classmethod
    def __loads__(cls, strings):

        return [{'radius': float(strings[0])}]

    @classmethod
    def __dumps__(cls, value):

        return str(value['radius'])


class AsciiCone(AsciiData):
    """
    Overload of `AsciiData` that interfaces with cone data.
    """

    __slots__ = ()

    @classmethod
    def __loads__(cls, strings):

        return [{'angle': float(strings[0]), 'cap': float(strings[1])}]

    @classmethod
    def __dumps__(cls, value):

        return f"{value['angle']} {value['cap']}"


class AsciiAttributeAlias(AsciiData):

    __slots__ = ()
    __default__ = {}

    @classmethod
    def __loads__(cls, strings):

        return [{strings[i]: strings[i+1] for i in range(0, len(strings), 2)}]

    @classmethod
    def __dumps__(cls, value):

        return '{{{aliases}}}'.format(aliases=', '.join([f'"{key}", "{value}"' for (key, value) in value.items()]))


class AsciiComponentList(AsciiData):

    __slots__ = ()
    __default__ = []

    @classmethod
    def __loads__(cls, strings):

        return [strings[1:]]

    @classmethod
    def __dumps__(cls, value):

        numStrings = len(value)
        strings = ' '.join(f'"{x}"' for x in value)

        return f'{numStrings} {strings}'


class AsciiDataPolyComponent(AsciiData):

    __slots__ = ()

    @classmethod
    def __loads__(cls, strings):

        return [{'type': strings[0], 'component': strings[1], 'index': int(strings[2])}]

    @classmethod
    def __dumps__(cls, value):

        return f"{value['type']} {value['component']} {value['index']}"


class AsciiNurbsCurve(AsciiData):

    __slots__ = ()

    @classmethod
    def __loads__(cls, strings):

        iterator = iter(strings)
        degree = int(next(iterator))
        spans = int(next(iterator))
        form = int(next(iterator))
        isRational = bool(next(iterator))
        dimension = int(next(iterator))

        knotCount = int(next(iterator))
        knots = [int(x) for x in islice(iterator, knotCount)]

        cvCount = int(next(iterator))
        cvs = None

        if isRational:

            cvs = numpy.array(tuple(islice(iterator, cvCount * 4))).reshape([cvCount, 4])

        else:

            cvs = numpy.array(tuple(islice(iterator, cvCount * 3))).reshape([cvCount, 3])

        nurbsCurve = {
            'degree': degree,
            'spans': spans,
            'form': form,
            'isRational': isRational,
            'dimension': dimension,
            'knotCount': knotCount,
            'knots': knots,
            'cvCount': cvCount,
            'cvs': cvs
        }

        return [nurbsCurve]

    @classmethod
    def __dumps__(cls, value):

        return '{degree} {spans} {form} {isRational} {dimension} {knotCount} {knots} {cvCount} {cvs}'.format(
            degree=value['degree'],
            spans=value['spans'],
            form=value['form'],
            isRational=value['isRational'],
            dimension=value['dimension'],
            knotCount=value['knotCount'],
            knots=' '.join(map(str, value['knots'].flatten())),
            cvCount=value['cvCount'],
            cvs=' '.join(map(str, value['cvs'].flatten())),
        )


class AsciiNurbsSurface(AsciiData):

    __slots__ = ()
    __default__ = None

    @classmethod
    def __loads__(cls, strings):

        iterator = iter(strings)
        uDegree = int(next(iterator))
        vDegree = int(next(iterator))
        uForm = int(next(iterator))
        vForm = int(next(iterator))
        isRational = bool(next(iterator))
        uKnotCount = int(next(iterator))
        uKnots = [float(x) for x in islice(iterator, uKnotCount)]
        vKnotCount = int(next(iterator))
        vKnots = [float(x) for x in islice(iterator, vKnotCount)]
        trim = next(iterator)
        cvCount = int(next(iterator))
        cvs = None

        if isRational:

            cvs = numpy.array(tuple(islice(iterator, cvCount * 4))).reshape([cvCount, 4])

        else:

            cvs = numpy.array(tuple(islice(iterator, cvCount * 3))).reshape([cvCount, 3])

        nurbsSurface = {
            'uDegree': uDegree,
            'vDegree': vDegree,
            'uForm': uForm,
            'vForm': vForm,
            'isRational': isRational,
            'uKnotCount': uKnotCount,
            'uKnots': uKnots,
            'vKnotCount': vKnotCount,
            'vKnots': vKnots,
            'trim': trim,
            'cvCount': cvCount,
            'cvs': cvs
        }

        return [nurbsSurface]

    @classmethod
    def __dumps__(cls, value):

        return '{uDegree} {vDegree} {uForm} {vForm} {spans} {form} {isRational} {dimension} {knotCount} {knots} {cvCount} {cvs}'.format(
            uDegree=value['uDegree'],
            vDegree=value['vDegree'],
            uForm=value['uForm'],
            vForm=value['vForm'],
            spans=value['spans'],
            form=value['form'],
            isRational=value['isRational'],
            dimension=value['dimension'],
            knotCount=value['knotCount'],
            knots=' '.join(map(str, value['knots'].flatten())),
            cvCount=value['cvCount'],
            cvs=' '.join(map(str, value['cvs'].flatten())),
        )


class AsciiMesh(AsciiData):

    __slots__ = ()

    __mesh_types__ = {
        'v': lambda x: numpy.array(tuple(islice(x, int(next(x)) * 3)), dtype=int).reshape((-1, 3)),
        'vn': lambda x: numpy.array(tuple(islice(x, int(next(x)) * 3)), dtype=int).reshape((-1, 3)),
        'vt': lambda x: numpy.array(tuple(islice(x, int(next(x)) * 2)), dtype=int).reshape((-1, 2)),
        'e': lambda x: numpy.array(tuple(islice(x, int(next(x)) * 3)), dtype=int).reshape((-1, 3)),
    }

    @classmethod
    def __loads__(cls, strings):

        iterator = iter(strings)
        meshes = deque()
        mesh = None

        while True:

            try:

                key = next(iterator)

                if key == 'v':

                    mesh = {'v': None, 'vn': None, 'vt': None, 'e': None}
                    meshes.append(mesh)

                func = cls.__mesh_types__[key]
                mesh[key] = func(iterator)

            except StopIteration:

                break

        return meshes

    @classmethod
    def __dumps__(cls, value):

        return ' '.join([f'{key} {len(item)} {" ".join(map(str, item.flatten()))}' for (key, item) in value.items() if item is not None])


class AsciiPolyFaces(AsciiData):
    """
    As of Maya 3.0 the keywords "mf" and "mh" are obsolete.
    """

    __slots__ = ()

    __poly_face_types__ = {
        'f': lambda x: numpy.array(tuple(islice(x, int(next(x)))), dtype=int),
        'h': lambda x: numpy.array(tuple(islice(x, int(next(x)))), dtype=int),
        'mu': lambda x: numpy.array(tuple(islice(x, int(next(x)))), dtype=int),
        'mc': lambda x: numpy.array(tuple(islice(x, int(next(x)))), dtype=int),
    }

    @classmethod
    def __loads__(cls, strings, **kwargs):

        iterator = iter(strings)
        polyFaces = deque()
        polyFace = None

        while True:

            try:

                key = next(iterator)
                func = cls.__poly_face_types__[key]

                if key == 'f':

                    polyFace = {'f': None, 'h': None, 'mu': [], 'mc': []}
                    polyFaces.append(polyFace)

                if key in ('mu', 'mc'):

                    index = next(iterator)
                    polyFace[key].append(func(iterator))

                else:

                    polyFace[key] = func(iterator)

            except StopIteration:

                break

        return polyFaces

    @classmethod
    def __dumps__(cls, value):

        faceVertexIndices = value['f']
        string = 'f {count} {indices}'.format(count=len(faceVertexIndices), indices=' '.join(map(str, faceVertexIndices)))

        holes = value['h']

        if holes is not None:

            string += ' h {count} {indices}'.format(count=len(holes), indices=' '.join(map(str, holes)))

        for (index, uvSet) in enumerate(value['mu']):

            string += ' mu {index} {count} {indices}'.format(index=index, count=len(uvSet), indices=' '.join(map(str, uvSet)))

        for (index, colorSet) in enumerate(value['mc']):

            string += ' mc {index} {count} {indices}'.format(index=index, count=len(colorSet), indices=' '.join(map(str, colorSet)))

        return string


class AsciiLattice(AsciiData):

    __slots__ = ()

    @classmethod
    def __loads__(cls, strings):

        return {
            'sDivisionCount': int(strings[0]),
            'tDivisionCount': int(strings[1]),
            'uDivisionCount': int(strings[2]),
            'points': numpy.array(strings[4:]).astype(float).reshape(1, 3)
        }

    @classmethod
    def __dumps__(cls, value):

        return '{sDivisionCount} {tDivisionCount} {uDivisionCount} {pointCount} {points}'.format(
            sDivisionCount=value['sDivisionCount'],
            tDivisionCount=value['tDivisionCount'],
            uDivisionCount=value['uDivisionCount'],
            pointCount=len(value['points']),
            points=' '.join(map(str, value['points'].flatten())),
        )


class AsciiCompound(AsciiData):

    def __init__(self, attribute, **kwargs):

        super(AsciiCompound, self).__init__(attribute, **kwargs)

        for attribute in self.attribute.children:

            if attribute.multi:

                self.__value__[attribute.shortName] = sparsearray.SparseArray()

            else:

                cls = getDataType(attribute)
                self.__value__[attribute.shortName] = cls(attribute)

    def __getitem__(self, key):

        if isinstance(key, str):

            return self.__value__[key]

        elif isinstance(key, int):

            return self.__getitem__(tuple(self.__value__.keys())[key])

        else:

            raise KeyError(f'__getitem__() expects a string or int ({type(key).__name__} given)!')

    @classmethod
    def __loads__(cls, value):
        """
        Returns the python equivalent of this ascii string.

        :rtype: Any
        """

        return {}  # There is no syntax for deserializing compound values!

    @classmethod
    def __dumps__(cls, value):
        """
        Returns the ascii equivalent of this python object.

        :rtype: str
        """

        return ''  # There is no syntax for serializing compound values!

    def default(self):

        return dict.fromkeys(tuple(attribute.shortName for attribute in self.attribute.iterChildren()), None)


__data_types__ = {
    'bool': AsciiBool,
    'boolean': AsciiBool,
    'enum': AsciiInt,
    'byte': AsciiInt,
    'int': AsciiInt,
    'int2': AsciiInt2,
    'int3': AsciiInt3,
    'short': AsciiInt,
    'short2': AsciiInt2,
    'short3': AsciiInt3,
    'long': AsciiInt,
    'long2': AsciiInt2,
    'long3': AsciiInt3,
    'time': AsciiFloat,
    'float': AsciiFloat,
    'float2': AsciiFloat2,
    'float3': AsciiFloat3,
    'double': AsciiFloat,
    'double2': AsciiFloat2,
    'double3': AsciiFloat3,
    'double4': AsciiFloat4,
    'doubleLinear': AsciiFloat,
    'distance': AsciiFloat,
    'doubleAngle': AsciiFloat,
    'angle': AsciiFloat,
    'attributeAlias': AsciiAttributeAlias,
    'string': AsciiString,
    'matrix': AsciiMatrix,
    'fltMatrix': AsciiMatrix,
    'intArray': AsciiIntArray,
    'Int32Array': AsciiIntArray,
    'doubleArray': AsciiDoubleArray,
    'pointArray': AsciiPointArray,
    'vectorArray': AsciiVectorArray,
    'stringArray': AsciiStringArray,
    'sphere': AsciiSphere,
    'cone': AsciiCone,
    'componentList': AsciiComponentList,
    'dataPolyComponent': AsciiDataPolyComponent,
    'nurbsCurve': AsciiNurbsCurve,
    'nurbsSurface': AsciiNurbsSurface,
    'nurbsTrimface': None,  # TODO: Implement this nightmare...
    'mesh': AsciiMesh,
    'polyFaces': AsciiPolyFaces,
    'lattice': AsciiLattice,
    'compound': AsciiCompound,
    'typed': AsciiGeneric
}


def getDataType(attribute):
    """
    Returns the data type associated with the given attribute.

    :type attribute: asciiattribute.AsciiAttribute
    :rtype: type
    """

    # Check if this is a typed attribute
    #
    cls = None

    if attribute.isTyped:

        cls = __data_types__.get(attribute.dataType, None)

    else:

        cls = __data_types__.get(attribute.attributeType, None)

    # Check if type is valid
    #
    if callable(cls):

        return cls

    else:

        raise NotImplementedError(f'getDataType() unable to locate data type: {attribute.attributeType}')
