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

import re

from . import alh_export


class AlarmFilter:
    """Abstraction for the filter to ease conversion from and to alh FORCEPV"""

    def __init__(
        self, expr, value=1, A="", B="", C="", D="", E="", F="", enabling=True
    ):
        """
        Create a new alarm filter object.

        Parameters
        ----------
        expr : str
            a PV or an EPICS CALC like expression, such as A>B or A+B=C.
            It must not contain constants for alh compatibility. The
            expression is compared to the value, with the default 1, i.e. true.
            If neither A through F are given, expr is assumed to simply be a PV.
        value : numeric or True, optional
            give the value of expression to activate the filter at.
            The default is 1. Use True if the expression is directly True/False,
            i.e. 0 or 1. This will create a simpler Phoebus filter than using
            1.
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
        self.replacements = {"A": A, "B": B, "C": C, "D": D, "E": E, "F": F}

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

        value = int(self.value) if isinstance(self.value, bool) else self.value

        if any(self.replacements.values()):
            lines = [
                "$FORCEPV CALC {mask} {val} NE".format(mask=forceMask, val=value),
                "$FORCEPV_CALC {expr}".format(expr=self.expr),
            ]
            for key, pv in sorted(self.replacements.items()):
                if pv:
                    line = "$FORCEPV_CALC_{key} {pv}".format(key=key, pv=pv)
                    lines.append(line)

        else:
            lines = [
                "$FORCEPV {expr} {mask} {val} NE".format(
                    expr=self.expr, mask=forceMask, val=value
                )
            ]

        return lines

    def get_phoebus_filter(self):
        """
        Get the filter in a phoebus compatible string
        """
        expr = self.expr

        # fix differences between calc and phoebus comparisons
        expr = re.sub(r"([^=!])=([^=])", r"\1 == \2", expr)
        expr = expr.replace("#", " != ")

        if self.enabling:
            fmtString = "({expr}) == {val}"
        else:
            fmtString = "({expr}) != {val}"

        if self.value is True:  # important, don't just check if self.value
            if self.enabling:
                fmtString = "{expr}"
            else:
                fmtString = "!({expr})"

        if any(self.replacements.values()):  # replace letters if any are given
            for letter in ["A", "B", "C", "D", "E", "F"]:
                expr = expr.replace(letter, "{{{letter}}}".format(letter=letter))

            expr = expr.format(**self.replacements)
        else:  # if no replacements are given, no need for ()
            fmtString = fmtString.replace("(", "")
            fmtString = fmtString.replace(")", "")

        filterStr = fmtString.format(expr=expr, val=self.value)

        return filterStr
