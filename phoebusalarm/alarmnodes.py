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
The alarm nodes used in the alarm tree

Currently there are:
    nodes
    pvs
    inlcusion markers
"""

from collections import namedtuple, OrderedDict
from itertools import chain
import os
import urllib.parse
import uuid
import xml.etree.ElementTree as ET

from . import alh_export
from .alarmfilter import AlarmFilter

# define for more clarity later
Guidance = namedtuple("guidance", ["title", "details"])
Display = namedtuple("display", ["title", "details"])
Command = namedtuple("command", ["title", "details"])
Action = namedtuple("automated_action", ["title", "details", "delay"])


def id_from_node_or_str(node):
    """
    pass node object or id string and get the id string
    """

    try:
        nid = node.identifier
    except AttributeError:
        nid = node
    return nid


class BaseNode:
    """
    Common funcitonality of "Groups" and "Inclusions"
    """

    def __init__(self, identifier=None, tag=None, sortKey=0):
        """
        Constructor

        Parameters
        ----------
        identifier : string, optional
            A unique identifier of the Node. If None, a UUID will be created.
            The default is None.
        tag : string, optional
            An alternative tag of the node.
        sortKey : float, optional
            A key to sort the nodes/pvs by. The default is insertion order
        """

        if identifier is None:
            self._id = str(uuid.uuid1())
        else:
            self._id = identifier

        if tag is None:
            self.tag = self.identifier
        else:
            self.tag = tag

        self.sortKey = sortKey

    @property
    def sortKey(self):
        """
        sortkey defines the order of nodes on export.
        """
        return self._sortKey

    @sortKey.setter
    def sortKey(self, newKey):
        """
        sort key should be a float
        """
        self._sortKey = float(newKey)

    # identifier should not be modified, read-only access to protected _id member
    @property
    def identifier(self):
        """unique ID of the node"""
        return self._id


class AlarmNode(BaseNode):
    """
    Representation of an alarm tree node
    """

    def __init__(self, name, identifier=None, tag=None, sortKey=0):
        """
        Constructor

        Parameters
        ----------
        name : string
            The name of the node as used in phoebus. Will be the ALIAS in alh.
        identifier : string, optional
            A unique identifier of the Node. If None, a UUID will be created.
            The default is None.
        tag : string, optional
            An alternative tag of the node. Not exported to xml.
            Used as the unique name in alh export.
            The default is None, which sets tag=name.
        sortKey : float, optional
            A key to sort the nodes/pvs by. The default is insertion order
        """
        if tag is None:
            tag = name

        super().__init__(identifier=identifier, tag=tag, sortKey=sortKey)

        self.guidances = []
        self.commands = []
        self.displays = []
        self.actions = []
        self._xmlType = "component"
        self._name = name

    @property
    def name(self):
        """name of the node in phoebus (Group ALIAS in alh)"""
        return self._name

    def add_guidance(self, title, details):
        """
        add a guidance to the alarm

        Parameters
        ----------
        title : str
            title of the guidance shown in phoebus context menu.
        details : str
            guidance text, link, info etc.
        """
        self.guidances.append(Guidance(title, details))

    def add_command(self, title, details):
        """
        add a command, can be executed on demand in phoebus

        Parameters
        ----------
        title : str
            title of the command shown in phoebus context menu.
        details : str
            the command to execute.
        """
        self.commands.append(Command(title, details))

    def add_display(self, title, path, macros=None):
        """
        add a helpful display

        Parameters
        ----------
        title : str
            title of the display shown in phoebus context menu.
        path : str
            path to the display file or full URL if you need to pass macros,
            see phoebus alarm doc for details.
        macros : dict, optional
            a dictionary of macros to pass to phoebus. Macro name should be the
            dict key. The macros will be properly quoted and appended to the
            URL passed in details. This is a convenient alternative to
            directly passing a fully formed ressource URL as path.
            Beware, path must be a valid URL if passing macros.
        """
        if macros is not None:
            if not isinstance(macros, dict):
                raise TypeError("Macros must be passed as dict")
            parseResult = urllib.parse.urlparse(path, scheme="file")

            if not parseResult.path.startswith("/"):
                raise ValueError(
                    "absolute path required to use macros " + parseResult.path
                )

            if not parseResult.query:
                macros = OrderedDict(sorted(macros.items()))
                queryStr = urllib.parse.urlencode(macros)
                parseResult = parseResult._replace(query=queryStr)

            url = urllib.parse.urlunparse(parseResult)
        else:
            url = path

        self.displays.append(Display(title, url))

    def add_auto_action(self, title, delay, command):
        """
        add an automatic action, executed when the alarm triggers

        Parameters
        ----------
        title : str
            title to identify action.
        delay : int
            time in seconds the alarm needs to be unacknowledged
            before action is triggered.
        details : str
            DESCRIPTION.
        """
        self.actions.append(Action(title, "cmd:{0}".format(command), delay))

    def add_mail(self, recipients, delay, title="mail"):
        """
        add mail notification to the alarm.

        Parameters
        ----------
        recipients : str or list
            the recipients of the notification.
        delay : int
            time in seconds the alrm is unacknowledged before sending mail.
        title : TYPE, optional
            title to use inside phoebus. The default is "mail".
        """

        if not isinstance(recipients, str):
            recipients = ",".join(recipients)

        self.actions.append(Action(title, "mailto:{0}".format(recipients), delay))

    def add_sevr_pv(self, pv, title="Severity PV"):
        """
        write the alarm severity value to another PV

        Parameters
        ----------
        pv : str
            the PV to write to.
        title : str, optional
            Title used in phoebus. The default is "Severity PV".
        """
        self.actions.append(Action(title, "sevrpv:{0}".format(pv), 0))

    def get_xml_element(self, **kwargs):  # pylint: disable=unused-argument
        """
        convert the node to an element tree description to dump as xml

        Returns
        -------
        xmlElement : ElementTree element
            the alarm node as an ElementTree with appropriate children.
        """

        xmlElement = ET.Element(self._xmlType, name=self._name)

        for entry in chain(self.guidances, self.displays, self.commands, self.actions):
            subElement = ET.SubElement(xmlElement, type(entry).__name__)
            for name, value in entry._asdict().items():
                prop = ET.SubElement(subElement, name)
                prop.text = str(value)

        return xmlElement

    def get_alh_lines(self, parent, **kwargs):  # pylint: disable=unused-argument
        """
        return a list of alh lines representing the node

        Parameters
        ----------
        parent : string
            The tag of the parent node.

        Returns
        -------
        lineList : List of Strings
            A list of lines which can be written to a file, representing this node.
        """
        lineList = ["GROUP {0} {1}".format(parent, self.tag)]

        if self._name != self.tag:
            aliasString = "$ALIAS {0}".format(self._name)
            lineList.append(aliasString)

        for guidance in self.guidances:
            lineList.append("$GUIDANCE")
            lineList.append(guidance.details)
            lineList.append("$END")

        for command in self.commands:
            lineList.append("$COMMAND {cmd}".format(cmd=command.details))

        for display in self.displays:
            lineList.append(alh_export.format_display(display.details))

        for action in self.actions:
            lineList.append(alh_export.format_action(action.details, action.delay))

        return lineList


class AlarmPV(AlarmNode):
    # I am okay with 8 instead of pylints max 7
    # pylint: disable=too-many-instance-attributes
    """
    Representation of an alarm PV
    """

    def __init__(self, channelPV, **kwargs):
        super().__init__(name=channelPV, identifier=channelPV, **kwargs)
        self.desc = ""
        self.enabled = True
        self.latch = True
        self.annunciate = True
        self.delay = 0
        self.count = 0
        self.filter = ""
        self._xmlType = "pv"

    def add_filter(self, expr, value=1, replaceDict=None):
        """
        Add a filter condition to the PV, in the style of alh FORCE_PV.
        This creates an AlarmFilter object and adds it as the filter.

        Parameters
        ----------
        expr : str
            a PV or an EPICS CALC like expression, such as A>B or A+B=C.
            It must not contain constants for alh compatibility. The
            expression is compared to the value, with the default 1, i.e., true.
            If neither no replaceDict is given, expr is assumed to simply be a PV.
        value : numeric or True, optional
            give the value of expression to activate the filter at.
            The default is 1. Use True if the expression is directly True/False,
            i.e. 0 or 1. This will create a simpler Phoebus filter than using
            1.
        replaceDict : dict, optional
            A dictionary containing the possible key A-F. The value for each
            key is used to replace the corresponding variable in the expr.
            The default is None.
        """
        if replaceDict is None:
            replaceDict = {}
        self.filter = AlarmFilter(expr, value, **replaceDict)

    def get_xml_element(self, **kwargs):  # pylint: disable=unused-argument
        """
        convert the node to an element tree description to dump as xml

        Returns
        -------
        xmlElement : ElementTree element
            the alarm node as an ElementTree with appropriate children.
        """
        xmlElement = super().get_xml_element()

        toAdd = OrderedDict()

        if self.desc:
            toAdd["description"] = self.desc

        toAdd["enabled"] = self.enabled
        toAdd["latching"] = self.latch
        toAdd["annunciating"] = self.annunciate

        if self.delay != 0:
            toAdd["delay"] = self.delay
            if self.count != 0:
                toAdd["count"] = self.count

        if self.filter:
            try:
                toAdd["filter"] = self.filter.get_phoebus_filter()
            except AttributeError:
                toAdd["filter"] = self.filter

        for i, (name, value) in enumerate(toAdd.items()):
            subelement = ET.Element(name)
            if isinstance(value, bool):
                subelement.text = str(value).lower()
            else:
                subelement.text = str(value)

            xmlElement.insert(i, subelement)

        return xmlElement

    def get_alh_lines(self, parent, **kwargs):
        """
        return a list of alh lines representing the node

        Parameters
        ----------
        parent : string
            The tag of the parent node.

        Raises
        ------
        ValueError
            If the filter of the node can not be represented as a FORCE_PV in alh.

        Returns
        -------
        lineList : List of Strings
            A list of lines which can be written to a file, representing this node.
        """
        lineList = super().get_alh_lines(parent)

        try:
            filterEnables = self.filter.enabling
        except AttributeError:
            filterEnables = False

        if self.enabled:
            defaultEnabled = not filterEnables
        else:
            defaultEnabled = False

        mask = alh_export.make_mask(defaultEnabled, self.latch)

        lineList[0] = "CHANNEL {par} {pv} {mask}".format(
            par=parent, pv=self._name, mask=mask
        )

        if self.desc:
            lineList.insert(1, "$ALIAS {0}".format(self.desc))

        if self.delay > 0:
            line = "$ALARMCOUNTFILTER {cnt} {dly}".format(
                cnt=self.count, dly=self.delay
            )
            lineList.append(line)

        if self.filter:
            try:
                lineList.extend(self.filter.get_alh_force(self.latch))
            except AttributeError as ex:
                raise ValueError(
                    "can't create alh force PV from %s" % type(self.filter)
                ) from ex

        return lineList


class InclusionMarker(BaseNode):
    """
    Marker for indicating file inclusions
    """

    def __init__(self, filename, sortKey=0):
        super().__init__(sortKey=sortKey)
        self.filename = filename
        self._xmlType = "xi:include"

    def get_xml_element(self, ext=None):
        """
        convert the node to an element tree description to dump as xml

        Parameters
        ----------
        ext : str, optional
            provide an extension to replace the one in the filename with, e.g.
            '.xml'. Keeps the original if None. The default is None.

        Returns
        -------
        xmlElement : ElementTree element
            the alarm node as an ElementTree with appropriate children.
        """
        if ext is not None:
            linkTarget = os.path.splitext(self.filename)[0] + ext
        else:
            linkTarget = self.filename
        xmlAttributes = {
            "href": linkTarget,
            "xpointer": "element(/1/1)",
            "xmlns:xi": "http://www.w3.org/2001/XInclude",
        }
        xmlElement = ET.Element(self._xmlType, attrib=xmlAttributes)
        return xmlElement

    def get_alh_lines(self, parent, ext=None):
        """
        return a list of alh lines representing the node

        Parameters
        ----------
        parent : string
            The tag of the parent node.
        ext : str, optional
            provide an extension to replace the one in the filename with, e.g.
            '.alh'. Keeps the original if None. The default is None.

        Returns
        -------
        lineList : list
            A list of lines which can be written to a file, representing this node.
        """
        if ext is not None:
            linkTarget = os.path.splitext(self.filename)[0] + ext
        else:
            linkTarget = self.filename

        lineList = ["INCLUDE {parent} {file}".format(file=linkTarget, parent=parent)]
        return lineList
