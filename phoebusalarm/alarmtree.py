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
Provides a python interface to write phoebus compatible alarm configurations.

Create a tree, then add nodes and alarms with create_node and create_alarm.
Modify the nodes/alarm by adding guidance, commands, automated_action, displays
and mail notifications. Change the properties of the alarm by changing its
attributes.

Example Usage:
>>> tree = AlarmTree("MachineName")
>>> node = tree.create_node("Subsystem1")
>>> pv1 = tree.create_alarm("SubSys1:ai1", node)
>>> pv1.desc = "An analog input"
>>> pv2 = tree.create_alarm("test:bi1", node)
>>> pv2.desc = "An import state"
>>> pv2.latch = False
>>> node.add_guidance("Help", "Take some recommned action")
>>> node.add_guidance("Contact", "Call 123456 for help")
>>> node.add_command("fix it", "/opt/bin/fix_everything.sh")
>>> node.add_display("Panel", "SubSys1.bob")
>>> tree.write_xml("output.xml")

"""
from collections import namedtuple, OrderedDict
from itertools import chain
import os
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

from treelib import Node, Tree

# define for more clarity later
Guidance = namedtuple("guidance", ['title', 'details'])
Display = namedtuple("display", ['title', 'details'])
Command = namedtuple("command", ['title', 'details'])
Action = namedtuple("automated_action", ['title', 'details', 'delay'])


class AlarmNode(Node):
    """
    Representation of an alarm tree node
    """
    def __init__(self, name, identifier=None, tag=None):
        """
        Constructor

        Parameters
        ----------
        name : string
            The name of the node as used in phoebus.
        identifier : string, optional
            A unique identifier of the Node. If None, a UUID will be created.
            The default is None.
        tag : string, optional
            An alternative tag of the node. Not exported to xml.
            The default is None, which sets tag=name.
        """
        if tag is None:
            tag = name

        super().__init__(tag=tag, identifier=identifier)
        self.guidances = []
        self.commands = []
        self.displays = []
        self.actions = []
        self._xmlType = "component"
        self._name = name

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

    def add_display(self, title, details):
        """
        add a helpful display

        Parameters
        ----------
        title : str
            title of the display shown in phoebus context menu.
        details : str
            path to the display file or full URL if you need to pass macros,
            see phoebus alarm doc for details.
        """
        self.displays.append(Display(title, details))

    def add_auto_action(self, title, delay, command):
        """
        add an automatic action, executed when the alarm triggers

        Parameters
        ----------
        title : str
            title to identify action.
        delay : int
            time in seconds the alarm needs to be unacknoledged
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

        self.actions.append(Action(title, "mailto:{0}".format(recipients),
                                   delay))

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

    def get_xml_element(self, **kwargs):
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


class AlarmPV(AlarmNode):
    """
    Representation of an alarm PV
    """
    def __init__(self, channelPV):
        super().__init__(name=channelPV, identifier=channelPV)
        self.desc = ""
        self.enabled = True
        self.latch = True
        self.annunciate = True
        self.delay = 0
        self.count = 0
        self.filter = ""
        self._xmlType = "pv"

    def get_xml_element(self, **kwargs):
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
            toAdd["filter"] = self.filter

        for name, value in toAdd.items():
            prop = ET.SubElement(xmlElement, name)
            if isinstance(value, bool):
                prop.text = str(value).lower()
            else:
                prop.text = str(value)

        return xmlElement


class InclusionMarker(Node):
    """
    Marker for indicating file inclusions
    """

    def __init__(self, filename):
        super().__init__()
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
            linkTarget = os.path.splitext(self.filename)[0]+ext
        else:
            linkTarget = self.filename
        xmlAttributes = {"href": linkTarget,
                         "xpointer": "element(/1/1)",
                         "xmlns:xi": "http://www.w3.org/2001/XInclude"}
        xmlElement = ET.Element(self._xmlType, attrib=xmlAttributes)
        return xmlElement


class AlarmTree(Tree):
    """
    Tree to hold the alarm configuration
    """

    def __init__(self, configName="", tree=None, deep=False,
                 identifier=None):
        super().__init__(tree=tree, deep=deep, identifier=identifier)
        # create a root node
        if configName:
            super().create_node(tag=configName, identifier=configName)

    def create_node(self, name, parent=None, tag=None):
        """
        create an AlarmNode and add it to the tree

        Parameters
        ----------
        name : string
            The name of the node to add.
        parent : Node or identifier string, optional
            The parent to add this to. The root element is used when None.
            The default is None.
        tag : string, optional
            An alternate description of the node.
            Not exported to xml. Used as GroupName in alh.
            The default is tag=name.

        Returns
        -------
        alarmNode : AlarmNode
            The instance of the added AlarmNode.

        """

        pid = parent.identifier if isinstance(parent, self.node_class) else parent
        if pid is None:
            if self.root is None:
                super().create_node(tag="Accelerator", identifier="Accelerator")
            pid = self.root

        identifier = pid+"/"+name
        alarmNode = AlarmNode(name=name, identifier=identifier, tag=tag)
        self.add_node(alarmNode, pid)

        return alarmNode

    def create_alarm(self, channelPV, parent=None):
        """
        create and AlarmPV and add it to the tree

        Parameters
        ----------
        channelPV : string
            The alarm PV.
        parent : Node or identifier string, optional
            The parent to add this to. The root element is used when None.
            The default is None.

        Returns
        -------
        alarmPV : AlarmPV instansce
            The instance of the created AlarmPV.

        """
        if parent is None:
            parent = self.root

        alarmPV = AlarmPV(channelPV)
        self.add_node(alarmPV, parent)
        return alarmPV

    def create_inclusion(self, filename, parent=None):
        """
        create and inclusionMarker and add it to the tree

        Parameters
        ----------
        filename : string
            The file name the inclusion should point to.
        parent : TYPE, optional
            The parent to add this to. The root element is used when None.
            The default is None.

        Returns
        -------
        inclusionNode : InclusionMarker
            The created InclusionMarker instance.

        """
        if parent is None:
            parent = self.root
        inclusionNode = InclusionMarker(filename)
        self.add_node(inclusionNode, parent)
        return inclusionNode

    def get_element_tree(self, rootID=None, ext=None):
        """
        return the tree starting at rootID as an ElementTree element

        Parameters
        ----------
        rootID : string, optional
            Identifier of the element to use as root. Use None to start at
            the tree root. The default is None.
        ext : string, optional
            Extension to use for inlcuded files. None keeps the original
            filenames. The default is None.

        Returns
        -------
        thisElement : Element
            An ElementTree Element with subelements representing this alarm
            tree. Use to dump as xml

        """

        if rootID is None or rootID == self.root:
            thisElement = ET.Element("config",
                                     name=self.get_node(self.root).tag)
            rootID = self.root
        else:
            thisNode = self.get_node(rootID)
            thisElement = thisNode.get_xml_element(ext=ext)

        for child in self.children(rootID):
            childID = child.identifier
            childElement = self.get_element_tree(childID, ext=ext)
            thisElement.append(childElement)

        return thisElement

    def write_xml(self, outputPath, forceXMLext=False):
        """
        write the alarm tree to an xml file readable by phoebus

        Parameters
        ----------
        outputPath : file path
            file to write to.
        forceXMLext : Bool, optional
            Force inlcude file extensions to '.xml'. The default is False.
        """
        if forceXMLext:
            ext = '.xml'
        else:
            ext = None

        # get elements and make a pretty xml
        rootElement = self.get_element_tree(ext=ext)
        roughString = ET.tostring(rootElement, 'utf-8')
        reparsed = minidom.parseString(roughString)
        prettyString = reparsed.toprettyxml(indent="  ")

        with open(outputPath, "w") as outFile:
            outFile.write(prettyString)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
