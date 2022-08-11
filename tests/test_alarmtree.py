# -*- coding: utf-8 -*-
"""
Test for the phoebus alarm tree
ToDo:
    Inclusion Marker test (against config working with phoebus)
"""

import os
import unittest
import xml.etree.ElementTree as ET

from phoebusalarm.alarmtree import AlarmTree, DuplicatedNodeIdError


class TestAlarmTree(unittest.TestCase):
    """
    Test featuers of the alarm tree class
    """

    def setUp(self):
        self.tree = AlarmTree(configName="Test")
        self.node1 = self.tree.create_node("Group1")
        self.node2 = self.tree.create_node("Group2")

    def test_unique(self):
        self.tree.create_node("SubGroup", parent=self.node1)
        self.tree.create_node("SubGroup", parent=self.node2)
        with self.assertRaises(DuplicatedNodeIdError):
            self.tree.create_node("SubGroup", parent=self.node2)

    def test_alh_warning(self):
        with self.assertWarns(Warning):
            self.tree.get_alh_lines()

    def test_default_root(self):
        tree = AlarmTree()
        alarm = tree.create_alarm("testpv")

        self.assertIsNotNone(tree.root)
        self.assertIsNotNone(tree.parent(alarm.identifier))
        self.assertIsNot(tree.get_node(tree.root), alarm)
        self.assertIsNot(type(tree.get_node(tree.root)), type(alarm))

    def test_removal(self):
        self.tree.create_node("SubGroup", parent=self.node1)
        self.tree.create_node("SubGroup2", parent=self.node1)

        numberRemoved = self.tree.remove_node(self.node1)
        self.assertEqual(numberRemoved, 3)
        rootChildren = self.tree.children(self.tree.root)
        self.assertEqual(rootChildren, [self.node2])

    def test_is_leaf(self):
        alarm1 = self.tree.create_alarm("test:ai1", self.node1)

        self.assertTrue(self.tree.is_leaf(alarm1))
        self.assertFalse(self.tree.is_leaf(self.node1))
        self.assertTrue(self.tree.is_leaf(self.node2))

    def test_link_past(self):
        alarm1 = self.tree.create_alarm("test:ai1", self.node1)
        alarm2 = self.tree.create_alarm("test:ai2", self.node1)
        alarm3 = self.tree.create_alarm("test:ai3", self.node1)
        self.tree.create_alarm("test:ai4", self.node2)

        self.tree.link_past_node(self.node1)

        self.assertEqual(
            self.tree.children(self.tree.root), [self.node2, alarm1, alarm2, alarm3]
        )

        self.assertEqual(self.tree.parent(alarm1).identifier, self.tree.root)


class TestEndToEnd(unittest.TestCase):
    """
    Test building of an entire tree and compare to xml exported from phoebus
    """

    outFile = "unittest_output"
    referenceXML = os.path.join(os.path.dirname(__file__), "reference_phoebus.xml")
    referenceALH = os.path.join(os.path.dirname(__file__), "reference_alh.alh")

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

        pv2 = self.alarmTree.create_alarm("test:ai2", parent=group1_1)
        pv2.desc = "Second Alarm PV"
        pv2.enable = True
        pv2.latch = True
        pv2.annunciate = True
        pv2.delay = 5
        pv2.sortKey = 2

        pv2.add_filter(expr="A<3", replaceDict={"A": "test:ai1"})

        pv1 = self.alarmTree.create_alarm("test:ai1", parent=group1_1)
        pv1.desc = "First Alarm PV"
        pv1.enable = True
        pv1.latch = True
        pv1.annunciate = True
        pv1.sortKey = 1

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
        referenceTree = ET.parse(self.referenceXML)
        referenceXML = ET.tostring(referenceTree.getroot())
        self.maxDiff = None
        self.assertEqual(actualXML, referenceXML)

    def test_alh_write(self):
        with self.assertWarns(Warning):
            self.alarmTree.write_alh(outputPath=self.outFile)

        with open(self.outFile) as f:
            actualLines = f.readlines()

        with open(self.referenceALH) as f:
            refLines = f.readlines()

        cleanedRef = [line for line in refLines if line != "\n"]
        cleanedActual = [line for line in actualLines if line != "\n"]

        self.assertListEqual(cleanedActual, cleanedRef)

    def tearDown(self):
        os.remove(self.outFile)


if __name__ == "__main__":
    unittest.main()
