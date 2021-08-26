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
AlarmFilter class represent the filter/forcePV to support export to xml and alh
"""

from . import alh_export

class AlarmFilter():
    """Abstraction for the filter to ease conversion from and to alh FORCEPV"""
    def __init__(self, expr, value=None, A="", B="", C="", D="", E="", F="",
                 enabling=True):
        """
        Create a new alarm filter object.

        Parameters
        ----------
        expr : str
            a PV or an EPICS CALC like expression, such as A>2 or A+B=C. Any
            expression must evaluate to a true or false. If given only a PV,
            you must also provide a value. Otherwise value must be None.
        value : float, optional
            If a PV was given in expr, give the value for the PV to activate
            the filter at. The default is None.
        A : str, optional
            PV to use vor A. The default is "".
        B : str, optional
            PV to use vor B. The default is "".
        C : str, optional
            PV to use vor C. The default is "".
        D : str, optional
            PV to use vor D. The default is "".
        E : str, optional
            PV to use vor E. The default is "".
        F : str, optional
            PV to use vor F. The default is "".
        enabling : bool, optional
            Toggle if the expression should enable or diable the alarm.
            The default is True, which means expr=True -> alarm on. This is
            the default behavior of phoebus and corresponds to a force maks
            of ----- in alh. Otherwise the expression in negated for phoebus
            and the force mask in alh is set as CD---

        """

        self.expr = expr
        self.value = value
        self.enabling = enabling
        self.replacements = {"A":A,
                             "B":B,
                             "C":C,
                             "D":D,
                             "E":E,
                             "F":F}

    def get_alh_force(self, latch=True):
        """
        get a list of line representing the filter in alh ForcePV notation

        Parameters
        ----------
        latch : bool, optional
            If the alarm is latching, i.e. transient alarms must be
            acknoledged. The default is True.

        Returns
        -------
        lines : list
            Each item is a line for the alh file.

        """
        forceMask = alh_export.make_mask(self.enabling, latch)

        if self.value is None:
            lines = ["$FORCEPV CALC {mask} {val} NE".format(mask=forceMask, val=1),
                     "$FORCEPV_CALC {expr}".format(expr=self.expr)]
            for key, pv in self.replacements.items():
                if pv:
                    line = "$FORCEPV_CALC_{key} {pv}".format(key=key, pv=pv)
                    lines.append(line)

        else:
            lines = ["$FORCEPV {expr} {mask} {val} NE".format(expr=self.expr,
                                                              mask=forceMask,
                                                              val=self.value)]

        return lines


    def get_phoebus_filter(self):
        """
        Get the filter in a phoebus compatible string
        """
        expr = self.expr

        if self.value is None:
            if self.enabling:
                fmtString = "{expr}"
            else:
                fmtString = "!({expr})"

            for letter in ["A", "B", "C", "D", "E", "F"]:
                expr = expr.replace(letter, "{{{letter}}}".format(letter=letter))

            expr = expr.format(**self.replacements)

        else:
            if self.enabling:
                fmtString = "{expr} == {val}"
            else:
                fmtString = "{expr} != {val}"

        filterStr = fmtString.format(expr=expr, val=self.value)

        return filterStr
