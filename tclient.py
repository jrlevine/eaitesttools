#!/usr/local/bin/python3
#
# talk to remote client of eaitest

import json
import requests
import configparser

# hack a doodle
products = {
    "Hotmail": "MS Outlook.com",
    "Exchange": "MS Exchange Server (hosted)",
    "Yandex": "Yandex Mail"
    }

class TClient:
    def __init__(self, config="config.txt", debug=False):
        """
        pass config file or dict if it's already been read
        """

        if type(config) is configparser.ConfigParser:
            self.config = config
        else:
            self.config = configparser.ConfigParser()
            self.config.read_file(open(config, "r"))

        if debug:
            self.debug = True
            self.dbconfig = self.config['DebugDatabase']
        else:
            self.debug = False
            self.dbconfig = self.config['Database']

    def deprod(self, product):
        """
        translate product hack
        """
        if product in products:
            return products[product]
        return product

    def getresult(self, product, testid):
        """
        returns tid, pid, ttid, status, comments
        """

        product = self.deprod(product)
        d = { "apikey": self.dbconfig.get('apikey'), "request": "getresult", "product": product, "testid": testid }

        try:
            r = requests.post(self.dbconfig.get('url'), json=d)
        except requests.exceptions.ConnectionError as err:
            print("cannot contact server", err)
            return None

        if r.status_code != 200:
            print("failed code ",r.status_code)
            return None

        js = r.json()
        if js and js['answer'] == "yes":
            return js['result']
        else:
            return None

    def setresult(self, product, testid, status, comments=None):
        """
        returns (True, None) or (False, reason)
        """

        if status.upper() == "N/A":
            status = "NA"
        
        if status.upper() not in ("NA","PASS","FAIL","PENDING"):
            return (False, "Bad status")

        product = self.deprod(product)
        d = { "apikey": self.dbconfig.get('apikey'),  "request": "setresult", "product": product, "testid": testid,
            "status": status, "comments": comments }
        
        try:
            r = requests.post(self.dbconfig.get('url'), json=d)
        except requests.exceptions.ConnectionError as err:
            print("cannot contact server", err)
            return None

        if r.status_code != 200:
            print("failed code ",r.status_code)
            return (False, f"Request failed {r.status_code}")

        js = r.json()
        if js and js['answer'] == "yes":
            return js['result']
        else:
            return (False, "No answer")

    def getresults(self, product, testtype, tester=None, done=False):
        """
        returns list of [(tid, status, comments, testid, summary, description, action, expected, class, phase), ...]
        tester defaults to current user
        """
        
        product = self.deprod(product)
        d = { "apikey": self.dbconfig.get('apikey'), "request": "getresults",
            "product": product, "testtype": testtype, "done": done, "ttid": None }
        if tester:
            d['ttid'] = tester
    
        try:
            r = requests.post(self.dbconfig.get('url'), json=d)
        except requests.exceptions.ConnectionError as err:
            print("cannot contact server", err)
            return None
        if r.status_code != 200:
            print("failed code ",r.status_code)
            return None

        js = r.json()
        if js and js['answer'] == 'yes':
            return js['result']
        else:
            return None

    def gettasks(self, product=None, testtype=None):
        """
        get tasks for a product
        """
        if not product:
            return None
        product = self.deprod(product)
        d = { "apikey": self.dbconfig.get('apikey'), "request": "tasks",
            "product": product, "testtype": testtype }
        try:
            r = requests.post(self.dbconfig.get('url'), json=d)
        except requests.exceptions.ConnectionError as err:
            print("cannot contact server", err)
            return None
        if r.status_code != 200:
            print("failed code ",r.status_code)
            return None

        js = r.json()
        if js and js['answer'] == 'yes':
            return js['result']
        else:
            return None

    def getproducts(self):
        """
        get list of products with active tasks
        """
        d = { "apikey": self.dbconfig.get('apikey'), "request": "products" }
        try:
            r = requests.post(self.dbconfig.get('url'), json=d)
        except requests.exceptions.ConnectionError as err:
            print("cannot contact server", err)
            return None
        if r.status_code != 200:
            print("failed code ",r.status_code)
            return None

        js = r.json()
        if js and js['answer'] == 'yes':
            return js['result']
        else:
            return None

if __name__=="__main__":
    import argparse

    parser = argparse.ArgumentParser(description='EAI test client')
    parser.add_argument('-d', action='store_true', help="Use debug server")
    parser.add_argument("-p", help="Product name")
    parser.add_argument("-t", help="Test type")
    parser.add_argument("-i", help="Test ID")    
    parser.add_argument("-s", help="Status")    
    parser.add_argument("-c", help="Comment")
    parser.add_argument("-a", action='store_true', help="tAsks")
    parser.add_argument('-q', action='store_true', help="Get list of products")
    parser.add_argument('-r', action='store_true', help="Get one result")
    parser.add_argument('-u', action='store_true', help="Set one result")
    parser.add_argument('-z', help="Tester ID")
    parser.add_argument('-l', action='store_true', help="get list of results")
    parser.add_argument('-f', action='store_true', help="finished tests in list of results")
    args = parser.parse_args()

    t = TClient("config.txt", debug=args.d)
    
    if args.q:
        r = t.getproducts()
        for l in r:
            print(l)

    if args.l or args.f:
        if not args.p:
            print("Need -p product")
        elif not args.t:
            print("Need -t testtype")
        else:
            r = t.getresults(args.p, args.t, args.z, done=args.f)
            for l in r:
                print(l)

    if args.s:
        if not args.p:
            print("Need -p product")
        elif not args.i:
            print("Need -i TestID")
        elif not args.s:
            print("Need -s Status")
        else:
            r = t.setresult(args.p, args.i, args.s, args.c)
            print(r)

    if args.r:
        if not args.p:
            print("Need -p product")
        elif not args.i:
            print("Need -i TestID")
            print("Need -s Status")
        else:
            r = t.getresult(args.p, args.i)
            print(r)

    if args.a:
        if not args.p:
            print("Need -p product")
        r = t.gettasks(product=args.p, testtype=args.t)
        print(r)
