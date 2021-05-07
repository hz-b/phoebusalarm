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
Provides the parse_alh function, which loads an alarm handler config and
returns an AlarmTree.

The config file is read line by line and processing is dispatched for each
keyword to an appropriate process_keyword function. If your site requires a
different behaviour for a function, e.g., you want to handle SEVRCOMMANDS such
as DOWN_MAJOR, modify these functions.

Alternatively, call the parse_alh function with a userDispatch argument.
This should be a dictionary of keywords and alternative functions to call.

See the process_example for details and what is passed to and returned from
these process_functions.
"""

import logging
import os

from treelib.exceptions import DuplicatedNodeIdError

from phoebusalarm.alarmtree import AlarmTree, AlarmPV


class ParsingLogger(logging.Logger):
    """A custom logger to log the position in the file.

    Logs the file and lineno at info level for each warnig or error.
    """
    def __init__(self, name):
        super().__init__(name)
        self.filename = ""
        self.lineno = 0

    def set_position(self, filename, lineno):
        """update the position in the file
        """
        self.filename = filename
        self.lineno = lineno

    def log_position(self):
        super().info("In file: %s at line %d", self.filename, self.lineno)

    def warning(self, msg, *args, **kwargs):
        self.log_position()
        super().warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.log_position()
        super().error(msg, *args, **kwargs)

    def exception(self, msg, *args, exc_info=True, **kwargs):
        self.log_position()
        super().error(msg, *args, exc_info=exc_info, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.log_position()
        super().error(msg, *args, **kwargs)


# get logger of the custom class and then reset to the default
oldClass = logging.getLoggerClass()
logging.setLoggerClass(ParsingLogger)
logger = logging.getLogger(__name__)
logging.setLoggerClass(oldClass)


def parse_alh(filepath, configName="Accelerator", userDispatch=None):
    """
    parse an alarm handler config file and return an AlarmTree

    Parameters
    ----------
    filepath : path
        the alarm handler file to read.
    configName : str, optional
        The name that should be given to the configuration. Should be the
        same as the kafka topics and alarm-server -config parameter.
        The default is "Accelerator".
    userDispatch : dict, optional
        Pass a set of functions to use for keywords found in the alarm handler
        file. Anything given here will overwrite the default functions.
        The default is None.

    Returns
    -------
    alarmTree : AlarmTree object
        The parsed alh file as an alarm tree. Use the tree's write_xml method
        to write a phoebus compatible xml representation of the tree.
    """

    alarmTree = AlarmTree(configName)
    currentNode = alarmTree.get_node(alarmTree.root)
    continueData = None
    lastCall = None

    # functions to call, depending on keyword
    dispatch = {"GROUP": process_group,
                "INCLUDE": process_include,
                "$ALIAS": process_alias,
                "CHANNEL": process_channel,
                "$SEVRPV": process_sevrpv,
                "$GUIDANCE": process_guidance,
                "$COMMAND": process_command,
                "$SEVRCOMMAND": process_sevrcommand,
                "$ALARMCOUNTFILTER": process_alarmcount,
                "$FORCEPV": process_forcepv,
                "$STATCOMMAND": process_statcommand,
                "$HEARTBEATPV": process_heartbeat,
                "$ACKPV": process_ignored,
                "$BEEPSEVERITY": process_beep,
                "$BEEPSEVR": process_beep}

    if userDispatch is not None:
        dispatch.update(userDispatch)

    with open(filepath, "r") as alhFile:
        logger.info("opened file: %s", filepath)

        for lineno, line in enumerate(alhFile):
            logger.set_position(filepath, lineno)
            # check if continuation was requested by
            if continueData is not None:
                currentNode, continueData = lastCall(line, alarmTree,
                                                     currentNode,
                                                     data=continueData)
            # non-comment, non-empty lines
            elif not line.isspace() and not line.startswith("#"):
                # cleanup whitespace
                line = line.strip()

                try:
                    keyword, alhArgs = line.split(maxsplit=1)
                except ValueError:
                    keyword = line
                    alhArgs = ""

                # treat all FORCEPV keywords as one with different arguments
                if "$FORCEPV" in keyword:
                    extras = keyword.replace("$FORCEPV", "")
                    keyword = "$FORCEPV"
                    alhArgs = " ".join((extras, alhArgs))
                logger.debug("Keyword: %s, with args: %s", keyword, alhArgs)
                # try to call the appropriate procces function
                try:
                    currentNode, continueData = dispatch[keyword](alhArgs,
                                                                  alarmTree,
                                                                  currentNode,
                                                                  keyword=keyword)
                    lastCall = dispatch[keyword]
                except KeyError:
                    logger.error("can't handle keyword %s", keyword)
                except DuplicatedNodeIdError as ex:
                    exStr = str(ex)
                    logger.error("Alh contains duplicate groups, "
                                 "combining them for phoebus. %s", exStr)
                    idStart = exStr.find(" ID '")
                    identifier = exStr[idStart+5:-1]
                    currentNode = alarmTree.get_node(identifier)

    return alarmTree


# ---- process functions -----
# each handles a specific alh keyword
def process_example(alhArgs, tree, currentNode, data=None, **kwargs):
    """
    An example process function. Modify the tree or currentNode as per your
    wishes based on the passed alhArgs.

    Parameters
    ----------
    alhArgs : str
        Everything in the line after the first space or the first underscore
        in the case of the $FORCEPV keyword.
    tree : AlarmTree
        The alarm tree constructed for this file. Modify to add or move nodes.
    currentNode : AlarmNode
        The current AlramNode, which is either a group or a channel in alarm
        handler. Typically this is what you want to change
    data : TYPE, optional
        DESCRIPTION. The default is None.
    **kwargs : TYPE
        DESCRIPTION.

    Returns
    -------
    currentNode : AlarmNode
        The current node. Could be different from the input if a node was added.
    data : None or anything
        Typically None is returned here. This allows a process function to
        request further lines. If it is anthing other than None subsequent lines
        will be passed ot that same processing function without further
        pre-processing. This is used in handling multiline guidances.
    """

    return currentNode, data


def process_group(alhArgs, tree, currentNode, **kwargs):
    parentName, name = alhArgs.split()
    parentId = find_parent(tree, currentNode, parentName)
    currentNode = tree.create_node(name, parent=parentId)
    return currentNode, None


def process_channel(alhArgs, tree, currentNode, **kwargs):
    params = alhArgs.split()
    pvName = params[1]
    parentName = params[0]

    parentId = find_parent(tree, currentNode, parentName)
    try:
        currentNode = tree.create_alarm(pvName, parent=parentId)
    except DuplicatedNodeIdError:
        logger.error("PV %s already exists, adding this channel's settings to "
                     "the previous instance", pvName)
        currentNode = tree.get_node(pvName)
    try:
        mask = params[2]
        if "C" in mask or "D" in mask:
            currentNode.enabled = False
        if "T" in mask:
            currentNode.latch = False
        if "A" in mask:
            logger.info("Ignoring part of mask %s for pv %s, "
                        "because all phoebus alarms must be acknoledged",
                        mask, pvName)
        if "L" in mask:
            logger.info("Ignoring part of mask %s for pv %s, "
                        "because phoebus will log all alarms",
                        mask, pvName)
    except IndexError:
        logger.debug("No mask for %s", pvName)

    return currentNode, None


def process_include(alhArgs, tree, currentNode, **kwargs):
    parentName, fileName = alhArgs.split()
    parentId = find_parent(tree, currentNode, parentName)
#    xmlName = os.path.splitext(fileName)[0]+'.xml'
# can't do this here, because recursion will need the original file name
    tree.create_inclusion(fileName, parent=parentId)
    return currentNode, None


def process_alias(alhArgs, tree, currentNode, **kwargs):
    alias = alhArgs.strip()
    # for alarms, alias becomes the descriptions
    if isinstance(currentNode, AlarmPV):
        currentNode.desc = alias
    # only change groups if the alias is actually different
    elif currentNode._name != alias:
        # use the alias from alh as the name of the node (to use in phoebus)
        # and rember the original alh name only as an alias
        oldNode = currentNode
        oldID = oldNode.identifier
        oldName = oldNode.alias
        parent = tree.parent(oldID)

        if tree.children(oldID):
            logger.error("Can't rename node %s to %s, "
                         "because it has children", oldID, alias)
        else:
            tree.remove_node(oldID)
            newNode = tree.create_node(alias, parent=parent, alias=oldName)
            newNode.guidances = oldNode.guidances
            newNode.commands = oldNode.commands
            newNode.displays = oldNode.displays
            newNode.actions = oldNode.actions
            currentNode = newNode

    return currentNode, None


def process_sevrpv(alhArgs, tree, currentNode, **kwargs):
    pvName = alhArgs.strip()
    currentNode.add_sevr_pv(pvName)
    return currentNode, None


def process_sevrcommand(alhArgs, tree, currentNode, **kwargs):
    sevr, command = alhArgs.split(maxsplit=1)
    commandName = command_name(command)
    if "UP" in sevr:
        if not sevr == "UP_ANY":
            logger.info("%s: phoebus automated action will be executed for "
                        "any alarm increase instead of %s",
                        currentNode.identifier, sevr)

        if any([command in action.details for action in currentNode.actions]):
            logging.info("ignoring duplicate action for %s for severity %s",
                         currentNode.identifier, sevr)
        else:
            currentNode.add_auto_action(commandName, 0, command)
    else:
        logger.warning("No phoebus equivalent for severity down commands, "
                       "ignoring severity command %s for %s",
                       alhArgs, currentNode.identifier)
    return currentNode, None


def process_guidance(alhArgs, tree, currentNode, data=None, **kwargs):
    # first call to guidance
    if data is None:
        # single line guidance is a url, best handles as a display,
        # otherwise request more data
        alhArgs = alhArgs.strip()
        if alhArgs:
            currentNode.add_display("URL", alhArgs)
        else:
            data = ""
    # multiline guidance
    else:
        if "$END" in alhArgs:
            currentNode.add_guidance("help", data)
            data = None
        else:
            data = data + alhArgs
    return currentNode, data


def process_command(alhArgs, tree, currentNode, **kwargs):
    commandName = command_name(alhArgs)
    currentNode.add_command(title=commandName, details=alhArgs)
    return currentNode, None


def process_alarmcount(alhArgs, tree, currentNode, **kwargs):
    count, time = alhArgs.split()
    currentNode.count = count
    currentNode.delay = time
    return currentNode, None


def process_statcommand(alhArgs, tree, currentNode, **kwargs):
    status, command = alhArgs.split(maxsplit=1)
    commandName = command_name(command)
    logger.warning("Replacing STATCOMMAND with automated action for %s, "
                   "please review manually",
                   currentNode.identifier)
    currentNode.add_auto_action(commandName, 0, command)


def process_beep(alhArgs, tree, currentNode, keyword, **kwargs):
    logger.warning("Ignoring %s for %s, "
                   "severity based annunication filtering not possible in phoebus",
                   keyword, currentNode.identifier)


def process_forcepv(alhArgs, tree, currentNode, **kwargs):
    if not isinstance(currentNode, AlarmPV):
        logger.error("Cannot parse forcePV for group %s, because Phoebus"
                     " does not support forcePV/filter for groups",
                     currentNode.tag)
        return currentNode, None

    args = alhArgs.split()

    if "_CALC" in args[0]:
        filterStr = update_filter(currentNode.filter, alhArgs)
    else:
        forcePV = args[0]
        # handle calc like a special PV (will be changed in update_filter)
        if forcePV == "CALC":
            forcePV = "({CALC})"
        forceMask = args[1]
        try:
            forceValue = args[2]
        except IndexError:
            forceValue = 1
        try:
            resetValue = args[3]
        except IndexError:
            resetValue = 0

        # forcePV==forceValue disables alarm -> phoebus filter enables alarm
        if ("C" in forceMask or "D" in forceMask) and currentNode.enabled:
            comp = "!="
        # forcePV==forveValue enables alarm -> same as phoebus filter
        elif not currentNode.enabled and "C" not in forceMask and "D" not in forceMask:
            comp = "=="
        else:
            comp = ""
            logger.error("Can't transfer %s forceMask to a phoebus filter "
                         "for PV %s with default as active=%s",
                         forceMask, currentNode.identifier, currentNode.enabled)

        if resetValue != "NE":
            logger.warning("PV %s uses resetValue %s for force, "
                           "phoebus filter will reset immidiately once "
                           "forcePV != forceValue",
                           currentNode.identifier, resetValue)
        if comp:
            filterStr = " ".join([forcePV, comp, forceValue])

    currentNode.filter = filterStr

    return currentNode, None


def update_filter(filterString, alhArgs):
    """
    change the given filterSring based on the passed alh Arguments

    Parameters
    ----------
    filterString : str
        A string to use as filter with format place holders, e.g. ({CALC})==1.
    alhArgs : str
        The alh line after $FORCEPV, e.g. _CALC A+B.

    Returns
    -------
    newfilterString : str
        Filter string with update values.

    """

    keyFragment, expr = alhArgs.split()
    key = keyFragment.split("_")[-1]  # everything after the last _ in the keyFrgament

    replacementDict = {"A": "{A}",
                       "B": "{B}",
                       "C": "{C}",
                       "D": "{D}",
                       "E": "{E}",
                       "F": "{F}"}

    if key == "CALC":
        for char, fmt in replacementDict.items():
            expr = expr.replace(char, fmt)  # inefficient, lots of new strings

    replacementDict[key] = expr
    newfilterString = filterString.format(**replacementDict)

    return newfilterString


def process_heartbeat(alhArgs, tree, currentNode, **kwargs):
    logger.warning("Ignoring Heartbeat PV, must be added via settings.ini")
    return currentNode, None


def process_ignored(alhArgs, tree, currentNode, keyword, **kwargs):
    logger.warning("No equivalent for %s in phoebus", keyword)
    return currentNode, None


def command_name(commandString):
    """
    get the name of a command from the full command line call
    """
    command, *args = commandString.split()
    path, file = os.path.split(command)
    commandName, ext = os.path.splitext(file)
    return commandName


def find_parent(tree, currentNode, parentName):
    """Find the parentId from the given alh parent
    traversers up the tree from the current node
    """

    if parentName == "NULL":
        parentId = None
    else:
        # alias contains the original alh alarm group name
        while parentName != currentNode.tag:
            currentNode = tree.parent(currentNode.identifier)
        parentId = currentNode.identifier

    return parentId
