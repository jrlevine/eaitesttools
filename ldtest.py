#!/usr/local/bin/python3
#
# load in tests

from eaidb import EAIdb
import csv
import re, sys




################################################################
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Load test descriptions')
    parser.add_argument('-t', type=str, help="Test type");
    parser.add_argument('-d', action='store_true', help="Debug");
    parser.add_argument('tests', type=str, help="CSV file of tests");
    args = parser.parse_args();

    db = EAIdb(None)

    testtype = args.t
    flds = ('testid', 'summary', 'description', 'action', 'expected', 'class', 'phase', 'refs')
    with open(args.tests, "r", newline='') as f:
        crd = csv.reader(f)
        first = True
        for l in crd:
            if first:                   # skip headers on the first line
                first = False
                continue

            tstdict = dict(zip(flds, l)) # seven fields into 
            tstdict['testtype'] = testtype
            if args.d:
                print(tstdict)
            r = db.addtest(tstdict)
            print(r, tstdict['testid'])
