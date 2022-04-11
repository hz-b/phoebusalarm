# -*- coding: utf-8 -*-

# Copyright 2021 Malte Gotz

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
command line script to convert alarm handler files to phoebus xml
"""


import argparse
import logging
import os

from phoebusalarm.alhparser import parse_alh
from phoebusalarm.alarmtree import InclusionMarker
from phoebusalarm._version import get_versions


def paste_subtree_into_base(baseTree, subTree, inclusionId):
    """add subtree at inclusionId into baseTree and remove inclusionId

    also remove the root element (config) from the subtree"""

    logger = logging.getLogger(__name__)
    parent = baseTree.parent(inclusionId)
    firstLevelList = subTree.children(subTree.root)
    if len(firstLevelList) != 1:
        raise RuntimeError("There should only be one top-level group")

    rootRemoved = subTree.remove_subtree(firstLevelList[0].identifier)
    try:
        baseTree.paste(parent.identifier, rootRemoved)
    except ValueError as ex:
        logger.critical("Failed to include %s into tree. "
                        "Original exception: %s",
                        firstLevelList[0].identifier, ex)

    baseTree.remove_node(inclusionId)


def recursive_alh_parse(inPath, outPath, singleFile=False, configName=None,
                        ignoreExisting=False):
    """
    Wrap the parse_alh function and call it on any included files as well

    Parameters
    ----------
    inPath : path
        path to the alarm handler file.
    outPath : path
        path of the output xml file.
    singleFile : bool, optional
        combines all included alarm handler files into one xml if true.
        The default is False
    configName : str, optional
        Name of the config for phoebus. Uses the base of the inPath fileName
        if None. The default is None.
    ignoreExisting : bool, optional
        skip recursion if the output file exists. The default is false

    Returns
    -------
    baseTree : AlarmTree
        The alarm tree as read from the alarmhandler files.

    """

    if singleFile and ignoreExisting:
        raise ValueError("must overwrite exsiting files, if creating a single output")

    overwrite = not ignoreExisting

    inputDir, inputName = os.path.split(inPath)
    outputDir, outputName = os.path.split(outPath)

    if configName is None:
        configName = os.path.splitext(inputName)[0]

    baseTree = parse_alh(inPath, configName)

    inclusionNodes = [node for node in baseTree.all_nodes()
                      if isinstance(node, InclusionMarker)]

    for inclusion in inclusionNodes:
        subOutName = os.path.splitext(inclusion.filename)[0]+".xml"
        if os.path.isabs(inclusion.filename):
            subInPath = inclusion.fileName
            subOutPath = subOutName
        else:
            subInPath = os.path.join(inputDir, inclusion.filename)
            subOutPath = os.path.join(outputDir, subOutName)

        if overwrite or not os.path.isfile(subOutPath):
            subConfigName = baseTree.parent(inclusion.identifier).identifier
            subTree = recursive_alh_parse(subInPath, subOutPath, singleFile,
                                          configName=subConfigName)

            if singleFile:
                paste_subtree_into_base(baseTree, subTree, inclusion.identifier)

    if not singleFile:
        baseTree.write_xml(outPath, forceXMLext=True)

    return baseTree


def alh_to_xml():
    dscString = ("Converts alarm handler config files into phoebus compatible "
                 "xml files. Optionally recurses through the files "
                 "included in the top alarm handler config.")

    ver = get_versions()['version']

    parser = argparse.ArgumentParser(description=dscString)
    parser.add_argument('--version', action='version',
                        version='%(prog)s v' + ver)
    parser.add_argument("input", help="alarm handler file to convert")
    parser.add_argument("-o", "--output",
                        help="output xml-file")
    parser.add_argument("-c", "--config",
                        help="name of the config in phoebus/kafka")
    parser.add_argument("-r", "--recursive", action='store_true',
                        help="convert all files included by the input file")
    parser.add_argument("-f", "--single-file", action='store_true',
                        help="output a single file even for recursion")
    parser.add_argument("-t", "--trim", action='store_true',
                        help="remove the top-level group to reduce depth of tree")
    parser.add_argument("-i", "--ignore-existing", action='store_true',
                        help="do not overwrite existing files when recursing")
    parser.add_argument("-v", "--verbosity", action='count', default=0,
                        help="increase log detail")

    args = parser.parse_args()

    try:
        logLevel = {0: logging.ERROR,
                    1: logging.WARNING,
                    2: logging.INFO}[args.verbosity]
        fmt = "%(levelname)s: %(message)s"
    except KeyError:
        logLevel = logging.DEBUG
        fmt = "%(name)s: %(levelname)s: %(message)s"

    logging.basicConfig(format=fmt, level=logLevel)

    inputPath = os.path.abspath(args.input)
    inputDir, inputName = os.path.split(inputPath)

    if args.output:
        outputPath = args.output
    # generate outputpath by replacing extension with xml
    else:
        outputName = os.path.splitext(inputName)[0]+".xml"
        outputPath = os.path.join(inputDir, outputName)

    # use given config name or detimine from file name
    if args.config:
        configName = args.config
    else:
        configName = os.path.splitext(inputName)[0]

    # build the tree
    if args.recursive:
        tree = recursive_alh_parse(inputPath, outputPath, args.single_file)
    else:
        tree = parse_alh(inputPath)

    # remove the top element (config)
    if args.trim:
        firstLevelList = tree.children(tree.root)
        if len(firstLevelList) != 1:
            logging.error("Multiple top level groups, can't remove")
        else:
            tree = tree.remove_subtree(firstLevelList[0].identifier)

    config = tree.get_node(tree.root)
    config.tag = configName

    tree.write_xml(outputPath, forceXMLext=True)
    logging.info("Output written to: %s", outputPath)


if __name__ == "__main__":
    alh_to_xml()
