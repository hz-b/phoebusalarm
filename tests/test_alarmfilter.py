# -*- coding: utf-8 -*-
"""
Test for the AlarmFilter
"""

import unittest

import context
from phoebusalarm.alarmfilter import AlarmFilter

class TestAlarmFilter(unittest.TestCase):

    def assert_filters(self, filterObj, expectedAlh, expectedPhoebus):
        alh = filterObj.get_alh_force()
        phoebus = filterObj.get_phoebus_filter()

        self.assertEqual(alh, expectedAlh)
        self.assertEqual(phoebus, expectedPhoebus)


    def test_simple_pv(self):
        filterObj = AlarmFilter(expr="test:ai1", value=5)

        expectedAlh = ["$FORCEPV test:ai1 ----- 5 NE"]
        expectedPhoebus = "(test:ai1) == 5"

        self.assert_filters(filterObj, expectedAlh, expectedPhoebus)

    def test_negation(self):
        filterObj = AlarmFilter(expr="test:ai1", value=5, enabling=False)

        expectedAlh = ["$FORCEPV test:ai1 CD--- 5 NE"]
        expectedPhoebus = "(test:ai1) != 5"

        self.assert_filters(filterObj, expectedAlh, expectedPhoebus)

    def test_calc_1(self):
        filterObj = AlarmFilter(expr="A+B", A="test:ai2", B="test:ai1")

        expectedAlh = ["$FORCEPV CALC ----- 1 NE",
                       "$FORCEPV_CALC A+B",
                       "$FORCEPV_CALC_A test:ai2",
                       "$FORCEPV_CALC_B test:ai1"]

        expectedPhoebus = "(test:ai2+test:ai1) == 1"

        self.assert_filters(filterObj, expectedAlh, expectedPhoebus)

    def test_calc_2(self):
        filterObj = AlarmFilter(expr="A==2&B<7|C", A="test:ai1", B="test:ai2",
                                C="test:ai3", enabling=False)

        expectedAlh = ["$FORCEPV CALC CD--- 1 NE",
                       "$FORCEPV_CALC A==2&B<7|C",
                       "$FORCEPV_CALC_A test:ai1",
                       "$FORCEPV_CALC_B test:ai2",
                       "$FORCEPV_CALC_C test:ai3"]

        expectedPhoebus = "(test:ai1==2&test:ai2<7|test:ai3) != 1"

        self.assert_filters(filterObj, expectedAlh, expectedPhoebus)

    def test_calc_with_value(self):
        filterObj = AlarmFilter(expr="A*B", value=2, A="test:ai1", B="test:ai2",
                                enabling=False)

        expectedAlh = ["$FORCEPV CALC CD--- 2 NE",
                       "$FORCEPV_CALC A*B",
                       "$FORCEPV_CALC_A test:ai1",
                       "$FORCEPV_CALC_B test:ai2"]

        expectedPhoebus = "(test:ai1*test:ai2) != 2"

        self.assert_filters(filterObj, expectedAlh, expectedPhoebus)

    def test_calc_unequal(self):
        filterObj = AlarmFilter(expr="A#B", A="test:ai1", B="test:ai2",
                                enabling=False)

        expectedAlh = ["$FORCEPV CALC CD--- 1 NE",
                       "$FORCEPV_CALC A#B",
                       "$FORCEPV_CALC_A test:ai1",
                       "$FORCEPV_CALC_B test:ai2"]

        expectedPhoebus = "(test:ai1 != test:ai2) != 1"

        self.assert_filters(filterObj, expectedAlh, expectedPhoebus)

    def test_calc_equal(self):
        filterObj = AlarmFilter(expr="A=B", A="test:ai1", B="test:ai2",
                                enabling=False)

        expectedAlh = ["$FORCEPV CALC CD--- 1 NE",
                       "$FORCEPV_CALC A=B",
                       "$FORCEPV_CALC_A test:ai1",
                       "$FORCEPV_CALC_B test:ai2"]

        expectedPhoebus = "(test:ai1 == test:ai2) != 1"

        self.assert_filters(filterObj, expectedAlh, expectedPhoebus)

    def test_true(self):
        filterObj = AlarmFilter(expr="A=B", value=True,
                                A="test:ai1", B="test:ai2",
                                enabling=False)

        expectedAlh = ["$FORCEPV CALC CD--- 1 NE",
                       "$FORCEPV_CALC A=B",
                       "$FORCEPV_CALC_A test:ai1",
                       "$FORCEPV_CALC_B test:ai2"]

        expectedPhoebus = "!(test:ai1 == test:ai2)"

        self.assert_filters(filterObj, expectedAlh, expectedPhoebus)

if __name__ == '__main__':
    unittest.main()
