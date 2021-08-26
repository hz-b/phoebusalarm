# -*- coding: utf-8 -*-
"""
Test for the phoebus alarm tree
ToDo:
    Inclusion Marker test (against config working with phoebus)
"""

import os
import unittest
import xml.etree.ElementTree as ET

from treelib.exceptions import DuplicatedNodeIdError

import context
from phoebusalarm.alarmtree import AlarmTree




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
        with self.assertRaises(DuplicatedNodeIdError):
            tree.create_node("SubGroup", parent=node2)

    def test_alhWarning(self):
        tree = AlarmTree(configName="Test")
        tree.create_node("Group1")
        tree.create_node("Group2")
        with self.assertWarns(Warning):
            tree.get_alh_lines()


class TestEndToEnd(unittest.TestCase):
    """
    Test building of an entire tree and compare to xml exported from phoebus
    """
    outFile = "unittest_output"
    referenceXML = os.path.join(os.path.dirname(__file__),
                                "reference_phoebus.xml")
    referenceALH = os.path.join(os.path.dirname(__file__),
                                "reference_alh.alh")

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

        pv2.add_filter(expr="A<3", replaceDict={"A":"test:ai1"})


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

        cleanedRef = [l for l in refLines if l != "\n"]
        cleanedActual = [l for l in actualLines if l != "\n"]

        self.assertListEqual(cleanedActual, cleanedRef)


    def tearDown(self):
        os.remove(self.outFile)


if __name__ == '__main__':
    unittest.main()
