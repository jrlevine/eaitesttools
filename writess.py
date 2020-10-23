#!/usr/local/bin/python3
#
# Write out spreadsheets of completed tests

from tclient import TClient
import xlsxwriter

class WriteSS:
    def __init__(self, debug=False):
        self.tc = TClient(debug=debug)

    def alltests(self):
        """
        write out everything with tests
        """
        pl = self.tc.getproducts()
        for p in pl:
            print(self.writetest(p['name']))

    def writetest(self, product):
        """
        write out a spreadsheet for this test
        """
        # get the set of results
        self.tasks = self.tc.gettasks(product=product)
        if not self.tasks:
            print("no tasks for", product)
            return None
        realpn = self.tasks[0]['product']
        print(realpn)
        with  xlsxwriter.Workbook(f"{realpn}.xlsx") as self.wb:
            self.bold = self.wb.add_format( {'bold': True} )

            for t in self.tasks:
                ttype = t['testtype']
                print(ttype, t['state'])
                if t['state'] == 'done':
                    tdata = self.tc.getresults(realpn, ttype, done=True)
                    self.dosheet(realpn, t['testtype'], tdata)
        return realpn
            
    def dosheet(self, product, testtype, tdata):
        """"
        write out a sheet for a set of tests
        """
        # add new sheet with headers
        sh = self.wb.add_worksheet(testtype)
        sh.write_string(0, 0, 'Test ID', self.bold)
        sh.write_string(0, 1, 'Result', self.bold)
        sh.write_string(0, 2, 'Summary', self.bold)
        sh.write_string(0, 3, 'Comments', self.bold)
        # freeze first row
        sh.freeze_panes(1, 0)
        # make columns wider
        sh.set_column(0, 0, 11)
        sh.set_column(2, 3, 50)

        for row, d in enumerate(tdata, start=1):
            sh.write_string(row, 0, d['testid'])
            sh.write_string(row, 1, d['status'])
            sh.write_string(row, 2, d['summary'])
            sh.write_string(row, 3, d['comments'])
        print("sheet", testtype, len(tdata))
    
if __name__=="__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Write result spreadsheet')
    parser.add_argument('-d', action='store_true', help="Use debug server")
    parser.add_argument('-a', action='store_true', help="Dump all tasks")
    parser.add_argument("products", nargs='*', help="Product name")
    args = parser.parse_args()

    w = WriteSS(debug=args.d)

    if args.a:
        w.alltests()
    else:
        if not args.products:
            parser.print_help()
            exit(1)
        for p in args.products:
            print(p, w.writetest(p))

    
