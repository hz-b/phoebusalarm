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

from collections import namedtuple
from operator import attrgetter
import warnings
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

from .alarmnodes import (
    BaseNode,
    AlarmNode,
    AlarmPV,
    InclusionMarker,
    id_from_node_or_str,
)

TreeEntry = namedtuple("TreeEntry", ["node", "parentId", "children"])


class DuplicatedNodeIdError(ValueError):
    """Exception thrown if an id already exists in the tree."""

    def __init__(self, node, message=""):
        super().__init__(
            self, " ".join(("Duplicate ID '%s' " % node.identifier, message))
        )
        self.nodeId = node.identifier


class RootNodeRemovalError(ValueError):
    """Exception thrown if attempting to remove the root node"""


class AlarmTree:
    """
    Tree to hold the alarm configuration
    """

    def __init__(self, configName="Accelerator"):
        # dictionary of form id: [Node object, parent_id, [children]]
        self.nodes = {}

        # set a root node
        self.root = None
        rootNode = BaseNode(tag=configName, identifier=configName)
        self.add_node(rootNode, None)

    def add_node(self, node, parent=None):
        """
        add the given node to the tree at parent

        Parameters
        ----------
        node : node object
            Node to add to tree.
        parent : node or id string, optional
            The parent of the node to be added. The default is None.

        Raises
        ------
        DuplicatedNodeIdError
            Each node must be unique.
        TypeError
            A node object must at least have the identifier
        ValueError
            For invalid value for parent.
        """
        try:
            if node.identifier in self.nodes:
                raise DuplicatedNodeIdError(node, "can't create node")
        except (AttributeError, TypeError) as ex:
            raise TypeError("node object must have an identifier attribute") from ex

        pid = id_from_node_or_str(parent)

        if pid is None:
            if self.root is not None:
                raise ValueError("A tree takes one root only.")
            self.root = node.identifier
        elif pid not in self.nodes:
            raise ValueError("Parent node '%s' is not in the tree" % pid)

        self.nodes[node.identifier] = TreeEntry(node, pid, [])

        if pid is not None:
            self.nodes[pid].children.append(node.identifier)

    def all_nodes(self):
        """A list of all nodes"""
        return [entry.node for entry in self.nodes.values()]

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

        pid = id_from_node_or_str(parent)

        if pid is None:
            pid = self.root

        identifier = pid + "/" + name
        alarmNode = AlarmNode(
            name=name, identifier=identifier, tag=tag, sortKey=sortKey
        )
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
            thisElement = ET.Element("config", name=self.get_node(self.root).tag)
            rootID = self.root
        else:
            thisNode = self.get_node(rootID)
            thisElement = thisNode.get_xml_element(ext=ext)

        for child in sorted(self.children(rootID), key=attrgetter("sortKey")):
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

        if parentID == self.root and len(self.children(parentID)) > 1:
            warnings.warn(
                "creating invalid alh, alarm tree has more than one top group"
            )

        for child in sorted(self.children(parentID), key=attrgetter("sortKey")):
            childID = child.identifier
            childLines = child.get_alh_lines(parent=parentName, ext=ext)
            childLines.append("")
            grandChildLines = self.get_alh_lines(childID, ext=ext)
            lineList.extend(childLines)
            lineList.extend(grandChildLines)

        return lineList

    def get_node(self, nid):
        """
        return the node for the given node id
        """
        return self.nodes[nid].node if nid is not None else None

    def children(self, parent):
        "get list of direct child nodes for the parent"
        pid = id_from_node_or_str(parent)
        return [self.nodes[cid].node for cid in self.nodes[pid].children]

    def get_xml_string(self, forceXMLext=False):
        """get the tree as an xml string"""
        if forceXMLext:
            ext = ".xml"
        else:
            ext = None

        # get elements and make a pretty xml
        rootElement = self.get_element_tree(ext=ext)
        roughString = ET.tostring(rootElement, "utf-8")
        reparsed = minidom.parseString(roughString)
        prettyString = reparsed.toprettyxml(indent="  ")
        return prettyString

    def get_alh_string(self, forceALHext=True):
        """get the tree as alarm handler string"""
        if forceALHext:
            ext = ".alh"
        else:
            ext = None

        lineList = self.get_alh_lines(ext=ext)

        return "\n".join(lineList)

    def is_leaf(self, node):
        """
        check if the given node as any children, i.e., true if it is a leaf
        """
        nid = id_from_node_or_str(node)
        return not bool(self.nodes[nid].children)

    def link_past_node(self, node):
        """
        remove the node and add its children to the parent
        """

        nid = id_from_node_or_str(node)
        pid = self.nodes[nid].parentId
        cids = self.nodes[nid].children

        if pid is None:
            raise RootNodeRemovalError("Can't link past the root node")

        self.nodes[pid].children.remove(nid)
        self.nodes[pid].children.extend(cids)
        self.nodes.pop(nid)

        for cid in cids:
            newEntry = TreeEntry(self.nodes[cid].node, pid, self.nodes[cid].children)
            self.nodes[cid] = newEntry

    def parent(self, node):
        """
        get the parent of given node or node-id
        """
        nid = id_from_node_or_str(node)
        pid = self.nodes[nid].parentId

        parentNode = self.nodes[pid].node if pid is not None else None
        return parentNode

    def remove_node(self, node):
        """
        remove this node and its children, return number of removed nodes.
        """
        nid = id_from_node_or_str(node)
        if nid == self.root:
            raise RootNodeRemovalError("You can't remove the root node")
        pid = self.nodes[nid].parentId
        self.nodes[pid].children.remove(nid)

        numberRemoved = self.recursive_node_remove(nid)

        return numberRemoved

    def recursive_node_remove(self, nid):
        """
        INTERNAL
        recurse the tree from node and remove all its children
        leaves link from parent
        """

        removedEntry = self.nodes.pop(nid)
        numberRemoved = 1
        for cid in removedEntry.children:
            removedChildren = self.recursive_node_remove(cid)
            numberRemoved += removedChildren

        return numberRemoved

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

        with open(outputPath, "w") as outFile:
            outFile.write(self.get_xml_string(forceXMLext))

    def write_alh(self, outputPath, forceALHext=True):
        """
        write the alarm tree as an alh file compatible with the alarm handler

        Parameters
        ----------
        outputPath : file path
            file to write to.
        forceALHext : Bool, optional
            Force inlcude file extensions to '.alh'. The default is True.
        """
        with open(outputPath, "w") as outFile:
            outFile.write(self.get_alh_string(forceALHext))


if __name__ == "__main__":
    import doctest

    doctest.testmod()
