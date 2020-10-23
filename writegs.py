#!/usr/local/bin/python3
#
# Write out Google sheets of completed tests

from tclient import TClient
import pickle
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class WriteGS:
    def __init__(self, debug=False):
        self.tc = TClient(debug=debug)
        self.creds = None
        self.sheets = {}              # existing spreadsheets
        try:
            with open('gsheets.p', 'rb') as sheets:
                self.sheets = pickle.load(sheets)
        except:
            pass
        
    def getsheets(self):
        """
        get known sheets
        """
        return list(self.sheets)

    def getcreds(self):
        """
        get Google credentials
        """
        if self.creds:
            return self.creds
            
        try:
            with open('gstoken.p', 'rb') as token:
                self.creds = pickle.load(token)
        except:
            pass

        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('gstoken.p', 'wb') as token:
            pickle.dump(self.creds, token)

        return self.creds

    def writetest(self, product):
        """
        write out a spreadsheet for this test
        """
        # get the set of results
        self.tasks = self.tc.gettasks(product=product)
        if not self.tasks:
            return None
        realpn = self.tasks[0]['product']
        print(realpn)
        
        self.service = build('sheets', 'v4', credentials=self.getcreds())

        ssobj = self.service.spreadsheets()
        if realpn in self.sheets:
            sheetid = self.sheets[realpn]
            print("old sheetid", sheetid)
        else:
            spreadsheet = {
                'properties': {
                    'title': realpn
                }
            }
            r = ssobj.create(body=spreadsheet,
                fields='spreadsheetId').execute()
            print("new sheet", r)
            sheetid = r['spreadsheetId']
            print("new sheetid", sheetid)
            self.sheets[realpn] = sheetid
            with open('gsheets.p', 'wb') as sheetf:
                pickle.dump(self.sheets, sheetf)

        for seq, t in enumerate(self.tasks, start=1):
            ttype = t['testtype']
            print(ttype, t['state'])
            if t['state'] == 'done':
                tdata = self.tc.getresults(realpn, ttype, done=True)
                self.dosheet(ssobj, sheetid, t['testtype'], seq, tdata)

        # delete default sheet 0
        req = {
            "requests": [
                {
                    "deleteSheet": { "sheetId": 0 }
                }
            ]
        }
        try:
            r = ssobj.batchUpdate(
                spreadsheetId=sheetid,
                body=req).execute()
        except HttpError as err:
            if "No sheet with id" in str(err):
                print("default sheet already deleted")
            else:
                print("delete failed", err)
                exit(1)


    def dosheet(self, ssobj, sheetid, testtype, seq, tdata):
        """
        add or update a sheet to a spreadsheet object
        """
        print("sheet", sheetid, testtype, len(tdata))
        values = [ ( 'Test ID', 'Result', 'Summary', 'Comments')]
        for row, d in enumerate(tdata, start=1):
            values.append((d['testid'], d['status'], d['summary'], d['comments']))

        req = {
            "requests": [
                {
                    "addSheet": {
                        "properties": { "sheetId": seq, "title": testtype }
                    }
                }
            ]
        }

        try:
            r = ssobj.batchUpdate(
                spreadsheetId=sheetid,
                body=req).execute()
            print("added sheet", r)
        except HttpError as err:
            if "already exists" in str(err):
                print("sheet exists")
            else:
                print("add failed", err)
                exit(1)
        # now add contents to sheet
        r = ssobj.values().update(spreadsheetId=sheetid,
            range=f"{testtype}!A1",
            valueInputOption="RAW",
            body={ "values": values,
                "majorDimension": "ROWS",
                }).execute()

        return r

if __name__=="__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Write result google sheet')
    parser.add_argument('-d', action='store_true', help="Use debug server")
    parser.add_argument('-a', action='store_true', help="Update all sheets")
    parser.add_argument("products", nargs='*', help="Product name")
    args = parser.parse_args()

    w = WriteGS(debug=args.d)

    if args.a:
        prods = w.getsheets()
    else:
        prods = args.products

    if not prods:
        parser.print_help()
        exit(1)

    for p in prods:
        print(p, w.writetest(p))
