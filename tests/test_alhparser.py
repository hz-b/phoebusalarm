# -*- coding: utf-8 -*-
"""
Test the alarm handler parser

add more tests
"""

import copy
import os
import unittest
from treelib.exceptions import DuplicatedNodeIdError

import context
import phoebusalarm.alhparser as alh
from phoebusalarm.alarmtree import AlarmTree
from phoebusalarm.alarmnodes import AlarmPV
from phoebusalarm.alarmfilter import AlarmFilter


class TestGuidance(unittest.TestCase):
    def setUp(self):
        self.tree = AlarmTree("test")
        self.node = self.tree.create_node("Group1")

    def test_with_params(self):
        line = "some link"
        testNode, contData = alh.process_guidance(line, self.tree, self.node,
                                                  data=None)
        self.assertIsNone(contData)
        self.assertEqual(testNode.displays[0].details, line)

    def test_empty_params(self):
        line = " "
        testNode, contData = alh.process_guidance(line, self.tree, self.node,
                                                  data=None)
        self.assertIsNotNone(contData)

    def test_continuation(self):
        data = "bla\n"
        line = "blubb\n"
        testNode, contData = alh.process_guidance(line, self.tree, self.node,
                                                  data=data)

        self.assertEqual(contData, data+line)

    def test_continuation_end(self):
        data = "blua\nblubb"
        line = "$END  \n"
        testNode, contData = alh.process_guidance(line, self.tree, self.node,
                                                  data=data)
        self.assertIsNone(contData)
        self.assertEqual(testNode.guidances[0].details, data)


class TestAlias(unittest.TestCase):
    line = "Alias   "

    def setUp(self):
        self.tree = AlarmTree("test")
        self.node = self.tree.create_node("Group1")

    def test_group(self):
        currentNode, data = alh.process_alias(self.line, self.tree, self.node)
        self.assertEqual(currentNode._name, "Alias")

    def test_children_removal(self):
        self.tree.create_alarm("test:ai1", parent=self.node)
        nodeDict = copy.copy(self.tree.nodes)
        oldNode = copy.deepcopy(self.node)
        with self.assertLogs(level="ERROR"):
            newNode, tmp = alh.process_alias(self.line, self.tree, self.node)

        # assures nothing changed. Couldn't find a way to do this more directly
        self.assertEqual(nodeDict, self.tree.nodes)
        self.assertEqual(oldNode.tag, newNode.tag)
        self.assertEqual(oldNode.identifier, newNode.identifier)
        self.assertEqual(newNode, self.node)

    def test_duplicate_names(self):
        otherNode = self.tree.create_node("Group2")
        self.assertRaises(DuplicatedNodeIdError, alh.process_alias,
                          "Group1", self.tree, otherNode)

    def test_alarm(self):
        alarm = self.tree.create_alarm("test:ai1", parent=self.node)
        alh.process_alias(self.line, self.tree, alarm)
        self.assertEqual(alarm.desc, "Alias")


class TestParents(unittest.TestCase):
    """Test function to find parentId"""

    def setUp(self):
        self.tree = AlarmTree("test")

    def test_null(self):
        parentID = alh.find_parent(self.tree, None, "NULL")
        self.assertIsNone(parentID)

    def test_simple(self):
        self.node = self.tree.create_node("Group1")
        parentID = alh.find_parent(self.tree, self.node, "Group1")
        self.assertEqual(parentID, self.node.identifier)

    def test_deep(self):
        self.node0 = self.tree.create_node(name="Group1")
        self.node1 = self.tree.create_node(name="Group2", parent=self.node0)
        self.node2 = self.tree.create_node(name="Group3", parent=self.node1)
        self.node3 = self.tree.create_node(name="Group4", parent=self.node2)
        parentID = alh.find_parent(self.tree, self.node3, "Group2")
        self.assertEqual(parentID, self.node1.identifier)


class TestFilterPropagation(unittest.TestCase):
    filterStr = "test>5"

    def setUp(self):
        self.tree = AlarmTree("test")
        self.node = self.tree.create_node("Group1")
        self.pv = self.tree.create_alarm("PV1")

    def test_no_filter(self):
        alh.propagate_filter(self.tree, self.node.identifier, self.pv)
        self.assertEqual(self.pv.filter, "")

    def test_filter(self):
        self.node.filter = self.filterStr
        alh.propagate_filter(self.tree, self.node.identifier, self.pv)
        self.assertEqual(self.pv.filter, self.filterStr)


class TestGroupFilter(unittest.TestCase):
    inPath = "temp.alh"
    alhConfig = ("GROUP NULL Group\n"
                 "$ALIAS Group Name\n"
                 "$FORCEPV CALC   -D-T-   1       NE\n"
                 "$FORCEPV_CALC A<B\n"
                 "$FORCEPV_CALC_A test:ai3\n"
                 "$FORCEPV_CALC_B 4\n"
                 "\n"
                 "CHANNEL Group test:ai1	---T-\n"
                 "$ALIAS OFF\n"
                 "\n"
                 "CHANNEL Group tets:ai2	---T-\n"
                 "$ALIAS Sum Error\n")

    def setUp(self):
        with open(self.inPath, "w") as alhFile:
            alhFile.write(self.alhConfig)

    def test_end_to_end(self):
        tree = alh.parse_alh(self.inPath, configName="Accelerator")
        alarms = [node for node in tree.all_nodes() if isinstance(node, AlarmPV)]
        for alarm in alarms:
            self.assertEqual(alarm.filter.get_phoebus_filter(), "!(test:ai3<4)")

    def tearDown(self):
        os.remove(self.inPath)


class TestForcePVCalc(unittest.TestCase):
    """Test the filter update function used for FORCEPV_CALC"""

    def setUp(self):
        self.tree = AlarmTree("test")
        self.node = self.tree.create_alarm("test:ai1")
        self.node.filter = AlarmFilter(expr = "")

    def test_calc(self):
        alhFragment = "CALC A+B<3"
        alh.process_forcepvcalc(alhFragment, self.tree, self.node)
        self.assertEqual(self.node.filter.expr, "A+B<3")

    def test_letters(self):
        argList = ["CALC_A test:ai1", "CALC_B test:ai2", "CALC_C test:ai3"]
        for arg in argList:
            alh.process_forcepvcalc(arg, self.tree, self.node)

        expectation = {"A":"test:ai1",
                       "B":"test:ai2",
                       "C":"test:ai3",
                       "D":"",
                       "E":"",
                       "F":""}
        self.assertDictEqual(self.node.filter.replacements, expectation)

#    baseStr = "({CALC})==1"  # first call should feed something like this
#    formulaStr = "({A}+{B}+{C})==1"  # after call with _CALC
#    argList = ["_CALC_A test:ai1", "_CALC_B test:ai2", "_CALC_C test:ai3"]
#
#    def test_calc(self):
#        newStr = alh.update_filter(self.baseStr, "_CALC A+B+C")
#        self.assertEqual(newStr, self.formulaStr)
#
#    def test_single_subst(self):
#        newStr = alh.update_filter(self.formulaStr, "_CALC_A test:ai1")
#        self.assertEqual(newStr, "(test:ai1+{B}+{C})==1")
#
#    def test_multiple_subst(self):
#
#        for arg in self.argList:
#            self.formulaStr = alh.update_filter(self.formulaStr, arg)
#
#        self.assertEqual(self.formulaStr, "(test:ai1+test:ai2+test:ai3)==1")


if __name__ == '__main__':
    unittest.main()
