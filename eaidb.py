#!/usr/local/bin/python3
# EAI test database

import pymysql
import pymysql.cursors
from html import escape
import csv
import hashlib
import re

pymysql.paramstyle='format'

def mses(s):                            # mysql unicode escape
    return s.replace('\\','\\\\').replace("'","\\'")

class EAIdb:
    def __init__(self,user, debug=False):

        self.user = user
        self.db = pymysql.connect(unix_socket="/tmp/mysql.sock", user='eaitest',passwd='x',db='eaitest',
            charset='utf8', cursorclass=pymysql.cursors.DictCursor)
        self.debug = debug
        
    def getuser(self, user=None):
        """
        get user info, mostly for API
        defaults to self.user
        """
        sql = "SELECT user, name, ttid, email from testers where user=%s"

        cdict = None
        with self.db.cursor() as cur:
            cur.execute(sql, (user or self.user,))
            cdict = cur.fetchone()
            return cdict
        
    def userlogin(self, pw=None):
        """
        Log in and get the account record for a user name
        Should be more careful about passwords, someday.
        password in DB is unsalted MD5 hash of text pw
        """
        if not pw:
            return None
    
        #print "user", self.user
        sql = "SELECT user, name, ttid, email, hex(password) as pw from testers where user=%s"

        cdict = None
        with self.db.cursor() as cur:
            cur.execute(sql, (self.user,))
            cdict = cur.fetchone()
            if cdict and hashlib.md5(pw.encode()).hexdigest() == cdict['pw'].lower():
                cur.execute("UPDATE testers SET lastlogin=now() WHERE user=%s", (self.user,))
                self.db.commit()
                return cdict
        return None
        
    def testerselect(self, name="tester", addall=False):
        """
        return an HTML select of testers
        """

        sel = f"""<select name="{name}">\n"""

        sql = "SELECT ttid, user, name FROM testers ORDER BY name"
        with self.db.cursor() as cur:
            cur.execute(sql)

            for tester in cur:
                if tester['user'] == self.user:
                    opt = f"""<option selected value="{tester['ttid']}">{tester['name']}</option>\n"""
                else:
                    opt = f"""<option value="{tester['ttid']}">{tester['name']}</option>\n"""
                sel += opt

        if addall:
            sel += """<option value="-1">ALL</option>\n"""

        sel += "</select>\n"
        return sel

    def addproduct(self, product, update=False):
        """
        product is a hash
        """
        sql = """INSERT INTO products(pid, name, vendor, email, types) VALUES(%s,%s,%s,%s,%s)"""
        upsql = """UPDATE products SET name=%s, vendor=%s, email=%s, types=%s WHERE PID=%s"""

#        types = { 'MUA':1, 'MSA':2, 'MTA':4, 'MDA':8, 'MSP':16, 'WEB':32 }

        args = list(product.get(i, None) for i in ('pid', 'name','vendor','email','types'))
        upargs = list(product.get(i, None) for i in ('name','vendor','email','types', 'pid'))

        # parse the set ourselves
#        tl = product['types'].upper().split(',')
#        tnum = sum(types[x] for x in tl)
#        args.append(tnum)
#        if self.debug:
#            print(sql, args)
        with self.db.cursor() as cur:
            try:
                cur.execute(sql, args)
            except pymysql.err.IntegrityError as err:
                if self.debug:
                    print("addproduct retry", err.args)
                if update and err.args[0] == 1062:
                    cur.execute(upsql, upargs)
                else:
                    raise
            rowid = cur.lastrowid
        self.db.commit()
        return rowid

    def getproduct(self, pid=None, name=None):
        """
        get a product by tid or name
        """
        sql = "SELECT pid, name, vendor, email, types from products"

        if pid:
            sql += " WHERE pid=%s"
            arg = pid
        elif name:
            sql += " WHERE name=%s"
            arg = name
        else:
            return None
        with self.db.cursor() as cur:
            cur.execute(sql, (arg,))
            cdict = cur.fetchone()
        return cdict                    # dict or None

    def getproducts(self):
        """
        get all products
        """
        sql = "SELECT pid, name, vendor, email, types from products ORDER BY pid"

        with self.db.cursor() as cur:
            cur.execute(sql)
            cdicts = cur.fetchall()
        return cdicts                    # list or None

    def productselect(self, name="product", default=None):
        """
        return an HTML select of products
        """

        prods = self.getproducts()
        sel = f"""<select name="{name}">\n"""
        for prod in prods:
            if prod['pid'] == default:
                opt = f"""<option selected value="{prod['pid']}">{prod['name']}</option>\n"""
            else:
                opt = f"""<option value="{prod['pid']}">{prod['name']}</option>\n"""
            sel += opt
        sel += "</select>\n"
        return sel

    def addtest(self, test):
        """
        test is a hash
        """
        sql = """INSERT INTO tests(tid, testid, testtype, summary, description, action, expected, class, phase, refs)
            VALUES(NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        # select fields out of the dict
        args = tuple(test[i] for i in ('testid', 'testtype', 'summary', 'description', 'action', 'expected', 'class', 'phase', 'refs'))
        with self.db.cursor() as cur:
            cur.execute(sql, args)
            rowid = cur.lastrowid
        self.db.commit()
        return rowid

    def gettest(self, tid=None, testid=None):
        """
        get a test by tid or id
        """
        sql = """SELECT tid, testid, testtype, summary, description, action, expected,
            class, phase, refs FROM tests"""
        if tid:
            sql += " WHERE tid=%s"
            arg = tid
        elif testid:
            sql += " WHERE testid=%s"
            arg = testid
        else:
            return None
        
        with self.db.cursor() as cur:
            cur.execute(sql, (arg,))
            cdict = cur.fetchone()
        return cdict                    # dict or None

    def gettests(self, testtype=None):
        """
        get all tests or limit by type
        """
        sql = """SELECT tid, testid, testtype, summary, description, action, expected, class, phase, refs
            FROM tests {0} ORDER BY testid""".format("WHERE testtype=%s" if testtype else "")

        with self.db.cursor() as cur:
            if testtype:
                cur.execute(sql, (testtype,))
            else:
                cur.execute(sql)
            cdicts = cur.fetchall()
        return cdicts                    # list or None

    def addtask(self, args, update=False):
        """
        args are a dict of ttid, pid, testtype, state
        """

        largs = list(args[x] for x in ('ttid','pid','testtype','state'))

        sql = """{0} INTO tasks(ttid, pid, testtype, state) 
                VALUES(%s, %s, %s, %s)""".format("REPLACE" if update else "INSERT")
        with self.db.cursor() as cur:
            try:
                cur.execute(sql, largs)
            except pymysql.err.IntegrityError as e:
                if e.args[0] == 1062:
                    return(False, "Duplicate entry")
        self.db.commit()
        return (True, largs)

    def gettasks(self, testtype=None, stats=False, pid=None):
        """
        get all tasks
        """
        if stats:
            sql = """SELECT tasks.ttid as ttid, user, tasks.pid as pid, products.name as `product`, vendor,
                tasks.testtype, state,ntests, ndone, ntests-ndone as nleft
                FROM tasks JOIN testers USING (ttid) JOIN products USING (pid)
                LEFT JOIN ndone USING (ttid, pid, testtype) JOIN ntests USING (testtype)"""
        else:
            sql = """SELECT tasks.ttid as ttid, user, tasks.pid as pid, products.name as `product`,
                vendor, tasks.testtype, state, NULL as ntests, NULL as ndone, NULL as nleft
                FROM tasks JOIN testers USING(ttid) JOIN products USING(pid)"""
        if testtype:
            sql += " WHERE tasks.testtype=%s"
        elif pid:
            sql += " WHERE products.pid=%s"

        with self.db.cursor() as cur:
            if stats:
                # make temp tables
                nsql = """CREATE TEMPORARY TABLE ndone
                    (SELECT count(*) as ndone,results.ttid, results.pid, testtype FROM tests JOIN results
                    USING (tid) group by pid, testtype,ttid)"""
                cur.execute(nsql)
                tsql = """CREATE TEMPORARY TABLE ntests
                    (select count(*) AS ntests,testtype FROM tests GROUP BY testtype)"""
                cur.execute(tsql)

            if testtype:
                cur.execute(sql, (testtype,))
            elif pid:
                cur.execute(sql, (pid,))
            else:
                cur.execute(sql)
            cdicts = cur.fetchall()
#        if self.debug:
#            print("tasks",cdicts)
        return cdicts                    # list or None

    def getresults(self, ttid, pid, testtype, done=False):
        """
        get test results (done=True) or tests not done yet (done=False)
        for (tester, product, type)
        """

        if ttid:
            args = (ttid, pid, testtype)
        else:
            args = (pid, testtype)
        if done:
            if ttid:
                sql = """SELECT results.tid AS tid, status, comments,
                    testid, summary, description, action, expected, class, phase FROM
                    results JOIN tests on results.tid=tests.tid WHERE ttid=%s AND pid=%s AND testtype=%s ORDER BY testid"""
            else:
                sql = """SELECT results.tid AS tid, status, comments,
                    testid, summary, description, action, expected, class, phase FROM
                    results JOIN tests on results.tid=tests.tid WHERE pid=%s AND testtype=%s ORDER BY testid"""
        else:
            if ttid:
                sql = """SELECT tid, NULL as status, NULL as comments,
                    testid, summary, description, action, expected, class, phase FROM
                    tests WHERE tid NOT IN (SELECT tid from results WHERE ttid=%s AND pid=%s) AND testtype=%s ORDER BY testid"""
            else:
                sql = """SELECT tid, NULL as status, NULL as comments,
                    testid, summary, description, action, expected, class, phase FROM
                    tests WHERE tid NOT IN (SELECT tid from results WHERE pid=%s) AND testtype=%s ORDER BY testid"""
        if self.debug:
            print("getresults", ttid, pid, testtype, done)

        with self.db.cursor() as cur:
            cur.execute(sql, args)
            cdicts = cur.fetchall()
        return cdicts                    # list or None

    def getoneresult(self, tid, pid, ttid=None):
        """
        retrieve one result or empty
        """
        if ttid is not None and int(ttid) < 0:
            ttid = None
        sql = """SELECT tid, pid, ttid, status, comments, picture FROM results WHERE tid=%s AND pid=%s"""
        if ttid:
            sql += " AND ttid=%s"
            args = (tid,pid, ttid)
        else:
            args = (tid,pid)
        with self.db.cursor() as cur:
            cur.execute(sql, args)
            cdict = cur.fetchone()
        return cdict

    def addresult(self, tid, ttid, pid, status, comments=None, picture=None):
        """
        add or update a test result
        replace record if there's a picture
        try to update it otherwise
        """
        if not ttid or int(ttid) < 0:
            return (False, "Need to select a tester")

        if picture:
            sql = """REPLACE INTO results(tid, pid, ttid, status, comments, picture) VALUES (%s, %s, %s, %s, %s, %s)"""
            with self.db.cursor() as cur:
                try:
                    cur.execute(sql, (tid, pid, ttid, status, comments, picture))
                except pymysql.err.IntegrityError as e:
                    if e.args[0] == 1452:
                        self.db.rollback()
                        return (False, "Not your test "+e.args[1])
        else:
            sql = """UPDATE results SET status=%s, comments=%s WHERE tid=%s AND pid=%s AND ttid=%s"""
            with self.db.cursor() as cur:
                try:
                    n = cur.execute(sql, (status, comments, tid, pid, ttid))
                except pymysql.err.IntegrityError as e:
                    if self.debug:
                        print("update error",e.args)
                    self.db.rollback() # try not to hang
                    return (False, "Update error "+e.args[1])
                
                if not n:   # doesn't exist or unchanged
                    try:
                        sql = """INSERT INTO results(tid, pid, ttid, status, comments) VALUES (%s, %s, %s, %s, %s)"""
                        cur.execute(sql, (tid, pid, ttid, status, comments))
                    except pymysql.err.IntegrityError as e:
                        if self.debug:
                            print("insert error", e.args)
                        if e.args[0] != 1062: # dup record OK
                            self.db.rollback() # try not to hang
                            raise       # something else
                    
        self.db.commit()
        return (True, None)

    def getsummary(self, ttid, testtype='MUA'):
        """
        get summary of test results for a tester
        ttid -1 means everyone
        """
        if int(ttid) >= 0:
            sql = """SELECT results.tid,results.pid,status,testtype,testid,products.name
            FROM results JOIN tests USING (tid) JOIN products USING (pid)
            WHERE ttid=%s AND  testtype=%s ORDER BY testid,name"""
        else:
            sql = """SELECT results.tid,results.pid,status,testtype,testid,products.name
            FROM results JOIN tests USING (tid) JOIN products USING (pid)
            WHERE testtype=%s ORDER BY testid,name"""
        
        with self.db.cursor() as cur:
            if int(ttid) >= 0:
                cur.execute(sql, (ttid, testtype, ))
            else:
                cur.execute(sql, (testtype, ))
            cdicts = cur.fetchall()
        # get list of products and of tests
        if cdicts:
            products = list(set( (x['name'],x['pid']) for x in cdicts ))
            products.sort(key=lambda x:x[0])
            tests = list(set( (x['testid'],x['tid']) for x in cdicts ))
            tests.sort(key=lambda x:x[0])
            cross = { f"{x['pid']}-{x['tid']}": x['status'] for x in cdicts }
            return (products, tests, cross)
        # nothing matched
        return None

    def dhash(self, d):
        """
        make a hash of a dict's values so we can see if anything has changed
        """
        if d == None:
            return 'None'

        h = hashlib.sha256()
        for i in d.values():
            if type(i) in (bytes, bytearray):
                h.update(i)
            else:
                h.update(str(i).encode('utf8', errors='ignore'))
        return h.hexdigest()
