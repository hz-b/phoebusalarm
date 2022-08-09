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
A collection of functions to support alh export functionality of the alarmtree
"""

import os
import urllib.parse
import warnings

# module wide settings
EDM_COMMAND = "run_edm.sh"  # use this command to open .edl files


def format_action(action, delay):
    actionType, details = action.split(":", maxsplit=1)

    if actionType == "sevrpv":
        line = "$SEVRPV {pv}".format(pv=details)
    elif actionType == "mailto":
        warnings.warn("mailto action not possible in alh: {act}".format(act=details))
        line = ""
    elif actionType == "cmd":
        line = "$SEVRCOMMAND UP_ANY {cmd}".format(cmd=details)
    else:
        raise ValueError("unkown action type {act} used".format(act=actionType))

    if delay > 0:
        warnings.warn("delayed action not possible in alh; {act}".format(act=action))
        line = ""

    return line


def format_display(display):
    if ".bob" in display:
        parseResult = urllib.parse.urlparse(display)

        fileName = os.path.split(parseResult.path)[1]
        edlName = fileName.replace(".bob", ".edl")

        macroStr = ""
        if parseResult.query:
            macroDict = urllib.parse.parse_qs(parseResult.query)
            pairList = [key + "=" + macroDict[key][0] for key in sorted(macroDict)]
            macroStr = '-m "' + ",".join(pairList) + '"'

        cmd = " ".join(filter(None, [EDM_COMMAND, macroStr, edlName]))
        line = "$COMMAND {cmd}".format(cmd=cmd)
    else:
        line = "$GUIDANCE {url}".format(url=display)
    return line


def make_mask(enabled, latch):

    mask = ["-", "-", "-", "-", "-"]

    if not enabled:
        mask[0] = "C"
        mask[1] = "D"

    # always require ack (mask[2])

    if not latch:
        mask[3] = "T"

    # always log (mask[4])

    return "".join(mask)
