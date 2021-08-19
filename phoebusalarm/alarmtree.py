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

from operator import attrgetter
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

from treelib import Tree

from .alarmnodes import (AlarmNode, AlarmPV, InclusionMarker)





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

    def create_node(self, name, parent=None, tag=None, sortKey=0):
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
        sortKey : float, optional
            A value to sort the nodes by in the output

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
        alarmNode = AlarmNode(name=name, identifier=identifier, tag=tag,
                              sortKey=sortKey)
        self.add_node(alarmNode, pid)

        return alarmNode

    def create_alarm(self, channelPV, parent=None, sortKey=0):
        """
        create and AlarmPV and add it to the tree

        Parameters
        ----------
        channelPV : string
            The alarm PV.
        parent : Node or identifier string, optional
            The parent to add this to. The root element is used when None.
            The default is None.
        sortKey : float, optional
            A value to sort the nodes by in the output

        Returns
        -------
        alarmPV : AlarmPV instansce
            The instance of the created AlarmPV.

        """
        if parent is None:
            parent = self.root

        alarmPV = AlarmPV(channelPV, sortKey=sortKey)
        self.add_node(alarmPV, parent)
        return alarmPV

    def create_inclusion(self, filename, parent=None, sortKey=0):
        """
        create and inclusionMarker and add it to the tree

        Parameters
        ----------
        filename : string
            The file name the inclusion should point to.
        parent : TYPE, optional
            The parent to add this to. The root element is used when None.
            The default is None.
        sortKey : float, optional
            A value to sort the nodes by in the output

        Returns
        -------
        inclusionNode : InclusionMarker
            The created InclusionMarker instance.

        """
        if parent is None:
            parent = self.root
        inclusionNode = InclusionMarker(filename, sortKey=sortKey)
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

        for child in sorted(self.children(rootID), key=attrgetter('sortKey')):
            childID = child.identifier
            childElement = self.get_element_tree(childID, ext=ext)
            thisElement.append(childElement)

        return thisElement

    def get_alh_lines(self, parentID=None, ext=None):
        """
        return the tree of all childeren of parentID as a list of alh lines

        Parameters
        ----------
        parentID : string, optional
            Identifier of the element to use as root. Use None to start at
            the tree root. The default is None. The root node it self will not
            be exported.
        ext : string, optional
            Extension to use for inlcuded files. None keeps the original
            filenames. The default is None.

        Returns
        -------
        thisElement : Element
            An ElementTree Element with subelements representing this alarm
            tree. Use to dump as xml

        """
        lineList = []
        if parentID is None or parentID == self.root:
            parentID = self.root
            parentName = "NULL"
        else:
            parentNode = self.get_node(parentID)
            parentName = parentNode.tag

        for child in sorted(self.children(parentID), key=attrgetter('sortKey')):
            childID = child.identifier
            childLines = child.get_alh_lines(parent=parentName, ext=ext)
            childLines.append("")
            grandChildLines = self.get_alh_lines(childID, ext=ext)
            lineList.extend(childLines)
            lineList.extend(grandChildLines)

        return lineList

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

    def write_alh(self, outputPath, forceALHext=True):

        if forceALHext:
            ext = '.alh'
        else:
            ext = None

        lineList = self.get_alh_lines(ext=ext)
        with open(outputPath, "w") as outFile:
            for line in lineList:
                outFile.write("%s\n"%line)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
