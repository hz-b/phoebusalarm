# -*- coding: utf-8 -*-
"""
Test the individual alarm nodes
"""

import unittest
import xml.etree.ElementTree as ET

import context
from phoebusalarm.alarmnodes import (AlarmNode, AlarmPV, InclusionMarker)

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

    def test_display(self):
        macros = {"DEV":42,"A":"some thing"}

        with self.assertRaises(ValueError):
            self.alarmNode.add_display("blubb",
                                       "/path/not/url/display.bob",
                                       macros)

        self.alarmNode.add_display("title",
                                   r"file:///path/to/display.bob",
                                   macros)
        self.assertEqual(self.alarmNode.displays[0].details,
                         r"file:///path/to/display.bob?DEV=42?A=some+thing")


class TestAlarmNodeAlh(unittest.TestCase):
    """
    Alh export of the AlarmNode
    """
    name = "Name"
    parent = "parent"

    def setUp(self):
        self.alarmNode = AlarmNode(name=self.name)

    def assert_expected_alh(self, expectation):
        result = self.alarmNode.get_alh_lines(self.parent)
        self.assertEqual(result, expectation)

    def test_base(self):
        expectation = ["GROUP parent Name"]
        self.assert_expected_alh(expectation)


    def test_with_alias(self):
        expectation = ["GROUP parent alhName",
                       "$ALIAS Name"]
        self.alarmNode.tag = "alhName"
        self.assert_expected_alh(expectation)

    def test_command(self):
        self.alarmNode.add_command("irrelevant title","run.sh -o blubb.txt")
        expectation = ["GROUP parent Name",
                       "$COMMAND run.sh -o blubb.txt"]
        self.assert_expected_alh(expectation)

    def test_guidance(self):
        self.alarmNode.add_guidance("irrelevant title","important alarm")
        expectation = ["GROUP parent Name",
                       "$GUIDANCE",
                       "important alarm",
                       "$END"]
        self.assert_expected_alh(expectation)

    def test_display(self):
        self.alarmNode.add_display("irrelevant title",
                                   "file:///some/path/to/display.bob?MACRO=3")
        expectation = ["GROUP parent Name",
                       "$COMMAND run_edm.sh -m MACRO=3 display.edl"]
        self.assert_expected_alh(expectation)

    def test_action(self):
        expectation = ["GROUP parent Name",
                       "$SEVRCOMMAND UP_ANY do_something.sh blubb"]
        self.alarmNode.add_auto_action("title",0,"do_something.sh blubb")
        self.assert_expected_alh(expectation)

        with self.assertWarns(Warning):
            self.alarmNode.add_auto_action("title",1,"do_something.sh blubb")
            self.assert_expected_alh(expectation+[""])


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

if __name__ == '__main__':
    unittest.main()
