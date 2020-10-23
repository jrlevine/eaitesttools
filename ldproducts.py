#!/usr/local/bin/python3
#
# load in products

from eaidb import EAIdb
import csv
import re, sys




################################################################
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Load test descriptions')
    parser.add_argument('-d', action='store_true', help="Debug");
    parser.add_argument('products', type=str, help="CSV file of products");
    args = parser.parse_args();

    db = EAIdb(None, debug=args.d)

    flds = ('pid', 'name', 'vendor', 'email', 'types')
    with open(args.products, "r", newline='') as f:
        crd = csv.reader(f,delimiter=';')
        first = True
        for l in crd:
            if first:                   # skip headers on the first line
                first = False
                continue

            proddict = dict(zip(flds, l)) # seven fields into 
            if args.d:
                print(proddict)
            r = db.addproduct(proddict, update=True)
            print(r, proddict['name'])
