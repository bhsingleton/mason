import os
import shutil

from mason import asciifileparser

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def parse(filePath):
    """
    Returns a full parsed Maya ASCII file.

    :type filePath: str
    :rtype: mason.asciiscene.AsciiScene
    """

    return asciifileparser.AsciiFileParser(filePath).scene


def createNewScene(destination):
    """
    Copies the untitled scene file to the specified location.

    :type destination: str
    :rtype: None
    """

    try:

        source = os.path.join(os.path.dirname(__file__), 'tests', 'untitled.ma')
        return shutil.copyfile(source, destination)

    except shutil.SameFileError as exception:

        log.debug(exception)
        return ''
