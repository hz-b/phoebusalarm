# -*- coding: utf-8 -*-
"""
Test for the AlarmFilter
"""

import unittest

import context
from phoebusalarm.alarmfilter import AlarmFilter

class TestAlarmFilter(unittest.TestCase):

    def assertFilters(self, filterObj, expectedAlh, expectedPhoebus):
        alh = filterObj.get_alh_force()
        phoebus = filterObj.get_phoebus_filter()

        self.assertEqual(alh, expectedAlh)
        self.assertEqual(phoebus,expectedPhoebus)


    def testSimplePV(self):
        filterObj = AlarmFilter(expr="test:ai1",value=5)

        expectedAlh = ["$FORCEPV test:ai1 ----- 5 NE"]
        expectedPhoebus = "test:ai1 == 5"

        self.assertFilters(filterObj, expectedAlh, expectedPhoebus)

    def testNegation(self):
        filterObj = AlarmFilter(expr="test:ai1",value=5, enabling=False)

        expectedAlh = ["$FORCEPV test:ai1 CD--- 5 NE"]
        expectedPhoebus = "test:ai1 != 5"

        self.assertFilters(filterObj, expectedAlh, expectedPhoebus)

    def testCalc1(self):
        filterObj = AlarmFilter(expr="A+B", A="test:ai1", B="test:ai2")

        expectedAlh = ["$FORCEPV CALC ----- 1 NE",
                       "$FORCEPV_CALC A+B",
                       "$FORCEPV_CALC_A test:ai1",
                       "$FORCEPV_CALC_B test:ai2"]

        expectedPhoebus = "test:ai1+test:ai2"

        self.assertFilters(filterObj, expectedAlh, expectedPhoebus)

    def testCalc2(self):
        filterObj = AlarmFilter(expr="A==2&B<7|C", A="test:ai1", B="test:ai2",
                                C="test:ai3", enabling=False)

        expectedAlh = ["$FORCEPV CALC CD--- 1 NE",
                       "$FORCEPV_CALC A==2&B<7|C",
                       "$FORCEPV_CALC_A test:ai1",
                       "$FORCEPV_CALC_B test:ai2",
                       "$FORCEPV_CALC_C test:ai3"]

        expectedPhoebus = "!(test:ai1==2&test:ai2<7|test:ai3)"

        self.assertFilters(filterObj, expectedAlh, expectedPhoebus)

if __name__ == '__main__':
    unittest.main()