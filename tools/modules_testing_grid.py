#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to format XUNIT output from unittests as a JSON string ready to be sent
to a [Weboob-CI](https://github.com/Phyks/weboob-ci) instance.

* `XUNIT` is the XUNIT file to handle.
* `ORIGIN` is an origin string as described in the Weboob-CI documentation
(basically just a string to identify the source of the unittests results).
"""
from __future__ import print_function

import json
import sys
import xunitparser


def main(xunit, origin):
    with open(xunit, "r") as fh:
        ts, tr = xunitparser.parse(fh)

    # Get test results for each module
    modules = {}
    other_testcases = []
    for tc in ts:
        if tc.classname.startswith("weboob."):
            other_testcases.append(repr(tc))
            continue
        module = tc.classname.split(".")[0]
        # In the following, we consider
        # bad > skipped > good
        # and only make update of a module status according to this order
        if tc.good:
            if tc.skipped:
                # Set to skipped only if previous test was good
                if module not in modules or modules[module] == "good":
                    modules[module] = "skipped"
            else:
                # Set to good only if no previous result
                if module not in modules:
                    modules[module] = "good"
        else:
            # Always set to bad on failed test
            modules[module] = "bad"
    # Agregate results by test result rather than module
    results = {
        "good": [],
        "bad": [],
        "skipped": []
    }
    for module in modules:
        results[modules[module]].append(module)
    return {
        "origin": origin,
        "modules": results,
        "others": other_testcases
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Usage: %s XUNIT_FILE ORIGIN" % (sys.argv[0]))

    print(
        json.dumps(
            main(sys.argv[1], sys.argv[2]),
            sort_keys=True, indent=4, separators=(',', ': ')
        )
    )
