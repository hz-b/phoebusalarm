# -*- coding: utf-8 -*-
"""
Test for the phoebus alarm tree
ToDo:
    Inclusion Marker test (against config working with phoebus)
"""

import os
import unittest
from treelib.exceptions import DuplicatedNodeIdError
import xml.etree.ElementTree as ET

import context
from phoebusalarm.alarmtree import AlarmTree, AlarmNode, AlarmPV, InclusionMarker


class TestInclusionMarker(unittest.TestCase):
    """
    Test the InclusionMarker Class
    """
    filePath = "test.xml"

    def test_marker(self):
        marker = InclusionMarker(self.filePath)
        xml = marker.get_xml_element()

        self.assertEqual(xml.tag, "xi:include")
        self.assertEqual(xml.attrib["href"], self.filePath)
        self.assertEqual(xml.attrib["xpointer"], "element(/1/1)")


class TestAlarmNode(unittest.TestCase):
    """
    Test the element tree conversion in the AlarmNode class
    """
    guidance = "some text goes here"
    display = "/path/to/somewhere"
    name = "Name"
    alias = "Another name"

    def setUp(self):
        self.alarmNode = AlarmNode(name=self.name)

    def test_basics(self):
        xml = self.alarmNode.get_xml_element()
        self.assertIsInstance(xml, ET.Element)
        self.assertEqual(xml.tag, "component")
        self.assertEqual(xml.attrib["name"], self.name)

    def test_alias(self):
        self.alarmNode.alias = self.alias
        self.assertEqual(self.alarmNode.tag, self.alias)


class TestAlarmTree(unittest.TestCase):
    """
    Test featuers of the alarm tree class
    """

    def test_unique(self):
        tree = AlarmTree(configName="Test")
        node1 = tree.create_node("Group1")
        node2 = tree.create_node("Group2")
        node3 = tree.create_node("SubGroup", parent=node1)
        node4 = tree.create_node("SubGroup", parent=node2)
        self.assertRaises(DuplicatedNodeIdError, tree.create_node,
                          "SubGroup", parent=node2)


class TestAlarmPV(unittest.TestCase):
    """
    Test the element tree conversion in the AlarmPV class
    """

    pvName = "test:ai1"
    pvDesc = "a description"
    pvFilter = "test:ai2 < 3"

    def setUp(self):
        self.alarmPV = AlarmPV(self.pvName)

    def test_basics(self):
        xml = self.alarmPV.get_xml_element()
        self.assertEqual(xml.tag, "pv")
        self.assertEqual(xml.attrib["name"], self.pvName)

    def test_bool_attr(self):
        xml = self.alarmPV.get_xml_element()
        for attrib in ["latching", "enabled", "annunciating"]:
            eleList = xml.findall(attrib)
            self.assertEqual(len(eleList), 1,
                             "there should be exactly one {!s} element".format(attrib))
            self.assertIn(eleList[0].text, ["true", "false"],
                          "{!s} must be true or false".format(attrib))

    def test_delay(self):
        self.alarmPV.delay = 10
        xml = self.alarmPV.get_xml_element()
        delayEle = xml.findall("delay")
        self.assertEqual(len(delayEle), 1,
                         "there must be one delay element")
        self.assertEqual(delayEle[0].text, "10",
                         "delay element has incorrect text")

    def test_count(self):
        self.alarmPV.count = 5
        xml = self.alarmPV.get_xml_element()
        countEle = xml.findall("count")
        self.assertEqual(len(countEle), 0,
                         "there should be no count element without delay")
        self.alarmPV.delay = 10
        xml = self.alarmPV.get_xml_element()
        countEle = xml.findall("count")
        self.assertEqual(len(countEle), 1,
                         "there should be one count element with delay")
        self.assertEqual(countEle[0].text, "5",
                         "count element has incorrect text")

    def test_description(self):
        self.alarmPV.desc = self.pvDesc
        xml = self.alarmPV.get_xml_element()
        descEle = xml.findall("description")
        self.assertEqual(len(descEle), 1, "there should one description element")
        self.assertEqual(descEle[0].text, self.pvDesc)


class TestEndToEnd(unittest.TestCase):
    """
    Test building of an entire tree and compare to xml exported from phoebus
    """
    outFile = "unittest_output.xml"
    referenceFile = os.path.join(os.path.dirname(__file__),
                                 "reference_config.xml")

    def setUp(self):
        self.alarmTree = AlarmTree(configName="Test")
        # add an configure a top group
        group1 = self.alarmTree.create_node("Group1")
        group1.add_guidance("Description", "A very important Alarm group")
        group1.add_guidance("Contacts", "Global contact for Group1")
        group1.add_display("Web", "https://en.wikipedia.org/wiki/Guidance")
        group1.add_display("Control", "/opt/epics/alarm_test/alarm_ctr.bob")
        # add a subgroup
        group1_1 = self.alarmTree.create_node("Group1_1", parent=group1)
        group1_1.add_command("run command", "/home/iocuser/test.sh")
        group1_1.add_mail("group1_1@phoebus_test.de", delay=60)
        # add some PVs
        pv1 = self.alarmTree.create_alarm("test:ai1", parent=group1_1)
        pv1.desc = "First Alarm PV"
        pv1.enable = True
        pv1.latch = True
        pv1.annunciate = True

        pv2 = self.alarmTree.create_alarm("test:ai2", parent=group1_1)
        pv2.desc = "Second Alarm PV"
        pv2.enable = True
        pv2.latch = True
        pv2.annunciate = True
        pv2.delay = 5
        pv2.filter = "test:ai1<3"

        # another subgroup
        group1_2 = self.alarmTree.create_node("Group1_2", parent=group1)
        group1_2.add_sevr_pv("test:sevr", title="severity")
        # and a PV
        pv3 = self.alarmTree.create_alarm("test:ai3", parent=group1_2)
        pv3.desc = "Third Alarm PV"
        pv3.enabled = True
        pv3.latch = False
        pv3.annunciate = False

    def test_xml_write(self):
        self.alarmTree.write_xml(outputPath=self.outFile)
        actualTree = ET.parse(self.outFile)
        actualXML = ET.tostring(actualTree.getroot())
        referenceTree = ET.parse(self.referenceFile)
        referenceXML = ET.tostring(referenceTree.getroot())
        self.maxDiff = None
        self.assertEqual(actualXML, referenceXML)

    def tearDown(self):
        os.remove(self.outFile)


if __name__ == '__main__':
    unittest.main()
