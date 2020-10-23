#!/usr/local/bin/python3
#
# Do MDA tests

from testgroup import Testgroup, TestError
import re
import imapclient
import imaplib
import poplib
import ssl
import time

class MDATestgroup(Testgroup):
    """
    tests for MDA
    """
    def __init__(self, product, config="config.txt", debug=False):
        super().__init__('MDA', product, config=config, debug=debug)
        self.msgtime =  self.pconfig.getint('msgtime',fallback=2) # how many mins to wait for a message to arrive
        self.user = self.pconfig.get('submituser')
        self.passwd = self.pconfig.get('submitpass')
        self.messages = {}
        self.downgrade = self.pconfig.getboolean('downgrade')
        self.doesutf8 = self.pconfig.getboolean('doesutf8', fallback=True)
        self.thost = self.pconfig.get('imaphost')
        self.tport = self.pconfig.getint('imapport', fallback=993)
        self.tpport = self.pconfig.getint('popport', fallback=995)
        self.tuser = self.pconfig.get('imapuser')
        self.tpwd = self.pconfig.get('imappw')
        self.imap = None
        self.imaplogin = None
        self.appmsg = None
        self.fname = None
        self.pophost = self.pconfig.get('pophost', fallback=self.thost)
        self.pop = None
        self.poplogin = None
        self.popmsg = None
        self.appresult = None
        self.didenable = None
        # target address on server being tested
        self.testaddr = self.pconfig.get('fromaddr') or self.pconfig.get('asciifrom')
        self.eaimtaflag = None
        
        # shared routines
    def eaimta(self):
        """
        does this MTA do EAI
        """
        if self.eaimtaflag is None:
            print("connect to", self.mailserver)
            if not self.cconnect():
                raise TestError("Cannot connect to mail server")
            if self.csock.has_extn('SMTPUTF8'):
                self.eaimtaflag = True
            else:
                self.eaimtaflag = False

        return self.eaimtaflag

    def connimap(self, login=False, new=False):
        """
        get an IMAP connection
        optionally log in
        """

        # are we already logged in
        if not new and self.imap and self.imaplogin == login:
            return self.imap

        self.didenable = None
        # HACK don't verify ssl cert because Coremail's
        sslcx = ssl.create_default_context()
        if not self.pconfig.getboolean('checkssl', fallback=True):
            print("turn off ssl check")
            sslcx.check_hostname = False
            sslcx.verify_mode = ssl.CERT_NONE
        sslcx.load_default_certs()

        try:
            print("try imap",self.thost,self.tport)
            i = imapclient.IMAPClient(self.thost, port=self.tport, ssl_context=sslcx)
        except Exception as err:
            print("no IMAP", err)
            return None

        if login:
            i._imap._mode_utf8()            # HACK allow UTF-8 login

            if b'AUTH=PLAIN' in i.capabilities():
                print("try auth", self.tuser)
                try:
                    r = i.plain_login(self.tuser, self.tpwd)
                except imapclient.Error as err:
                    return None
            else:
                print("try login", self.tuser)
                try:
                    r = i.login(self.tuser, self.tpwd)
                except imapclient.Error as err:
                    return None
        self.imap = i
        self.imaplogin = login
        return i


    def connpop(self, login=False, new=False):
        """
        get a POP connection
        optionally log in
        """

        # are we already logged in
        if not new and self.pop and self.poplogin == login:
            return self.pop

        # HACK don't verify ssl cert because Coremail's
        sslcx = ssl.create_default_context()
        if not self.pconfig.getboolean('checkssl', fallback=True):
            print("turn off ssl check")
            sslcx.check_hostname = False
            sslcx.verify_mode = ssl.CERT_NONE
        sslcx.load_default_certs()

        try:
            print("try pop",self.pophost,self.tpport)
            if self.tpport == 995:
                i = poplib.POP3_SSL(self.pophost, port=self.tpport, context=sslcx)
            else:
                i = poplib.POP3(self.pophost, port=self.tpport)
                r = i.stls(context=sslcx)
                print("stls", r)
        except Exception as err:
            print("no POP", err)
            return None

        if login:
            if self.doesutf8:   # skip where it kills the session
                try:
                    r = i.utf8()
                except:
                    print("POP UTF8 failed")
            print("try login", self.tuser)
            try:
                r = i.user(self.tuser)
            except Exception as err:
                print("user fail", err)
                return None
            if not r.startswith(b'+OK'):
                print("user fail", r)
                return None
            try:
                r = i.pass_(self.tpwd)
            except Exception as err:
                print("pass fail", err)
                return None
            if not r.startswith(b'+OK'):
                print("pass fail", r)
                return None
        self.pop = i
        self.poplogin = login
        return i

    # specific tests
    # return tuple of True (Pass) / False (Fail) / None (Pending),
    # and comment

    def mda001(self):
        """
        Send in a message, see if Received has its own name as U-labels
        send from my host to test address
        """
        if not self.eaimta():
            return("Fail", "Does not accept EAI mail")

        if not self.idnhost:
            return("NA", "Host name is ASCII")

        r = self.domsg('eaisubj', From=self.pconfig.get('srvfrom'), To=self.testaddr, sendmail=True, getrmt=False)
        if not r:
            return("Pending", "message not received")
        (dhdrs, lhdrs, body) = r
        rh = dhdrs['received'][0]
        rm = re.search(r'\sby\s+([^\s(]+)', rh)
        if not rm:
            print("funky received", rh)
            return("Pending", "cannot find header")
        myname = rm.group(1).lower()
        print("i am", myname)
        if self.iseai(myname):
            return('Pass', "UTF-8 host name "+myname)
        if 'xn--' in myname:
            return('Fail', "A-label in host name "+myname)
        return("NA", "Host name is ASCII "+myname)

    def mda002(self):
        """
        Send in a message, see if Received with UTF8
        send from my host to test address
        """
        if not self.eaimta():
            return("Fail", "Does not accept EAI mail")
        r = self.domsg('eaisubj', From=self.pconfig.get('srvfrom'), To=self.testaddr, sendmail=True, getrmt=False)
        if not r:
            return("Pending", "message not received")
        (dhdrs, lhdrs, body) = r
        rh = dhdrs['received'][0]
        rm = re.search(r'\swith\s+([^\s(]+)', rh)
        if not rm:
            print("funky received", rm)
            return("Pending", "cannot find header")
        mywith = rm.group(1).upper()
        if mywith.startswith('UTF8'):
            return("Pass", "received with "+mywith)
        return("Fail", "received with "+mywith)
        
    def mda003(self):
        """
        Send in a message, see if From is UTF8
        send from my host to test address
        """
        if not self.eaimta():
            return("Fail", "Does not accept EAI mail")
        r = self.domsg('eaisubj', From=self.pconfig.get('srvfrom'), To=self.testaddr, sendmail=True, getrmt=False)
        if not r:
            return("Pending", "message not received")
        (dhdrs, lhdrs, body) = r
        rh = dhdrs['from'][0]
        if self.iseai(rh):
            return("Pass", "UTF-8 From "+rh)
        return("Fail", "ASCII From "+rh)

    def mda004(self):
        """
        Send in a message, see if To is UTF8
        send from my host to test address
        """
        if not self.eaimta():
            return("Fail", "Does not accept EAI mail")
        r = self.domsg('eaisubj', From=self.pconfig.get('srvfrom'), To=self.testaddr, sendmail=True, getrmt=False)
        if not r:
            return("Pending", "message not received")
        (dhdrs, lhdrs, body) = r
        rh = dhdrs['to'][0]
        if self.iseai(rh):
            return("Pass", "UTF-8 To "+rh)
        return("Fail", "ASCII To "+rh)

    def mda005(self):
        """
        Send in a message, see if To is UTF8
        send from my host to test address
        """
        if not self.eaimta():
            return("Fail", "Does not accept EAI mail")
        r = self.domsg('eaisubj', From=self.pconfig.get('srvfrom'), To=self.testaddr, sendmail=True, getrmt=False)
        if not r:
            return("Pending", "message not received")
        (dhdrs, lhdrs, body) = r
        rh = dhdrs['subject'][0]
        if self.iseai(rh):
            return("Pass", "UTF-8 subject "+rh)
        return("Fail", "ASCII subject "+rh)

    def mda006(self):
        """
        Send in a message, see if it's delivered
        send from my host to test address
        """
        if not self.eaimta():
            return("Fail", "Does not accept EAI mail")
        r = self.domsg('eaisubj', From=self.pconfig.get('srvfrom'), To=self.testaddr, sendmail=True, getrmt=False)
        if not r:
            return("Fail", "message not received")
        return("Pass", "EAI message delivered")

    def mda007(self):
        """
        Log in for IMAP with unicode address
        """
        if not self.iseai(self.tuser):
            return("NA", "No UTF-8 userid available")
            
        i = self.connimap()
        if not i:
            return("Pending", "IMAP not available")
        i.folder_encode = False         # don't use UTF7
        i._imap._mode_utf8()            # HACK allow UTF-8 login

        if b'AUTH=PLAIN' in i.capabilities():
            print("try auth", self.tuser)
            try:
                r = i.plain_login(self.tuser, self.tpwd)
                return("Pass", f"Login as {self.tuser} worked")
            except imapclient.Error as err:
                return("Fail", f"AUTH Login as {self.tuser} failed {err}")
        else:
            print("try login", self.tuser)
            try:
                r = i.login(self.tuser, self.tpwd)
                return("Pass", f"Login as {self.tuser} worked but AUTH not available")
            except imapclient.Error as err:
                return("Fail", f"Login as {self.tuser} failed {err}")

    def mda008(self):
        """
        UTF8=ACCEPT or UTF8=ONLY capability is advertised
        """
        i = self.connimap()
        if not i:
            return("Pending", "IMAP not available")
        ic = i.capabilities()
        for tc in (b'UTF8=ACCEPT', b'UTF8=ONLY'):
            if tc in ic:
                return("Pass", f"Has {tc.decode} capability")
        return("Fail", f"Does not have capability {tuple(c.decode() for c in ic)}")

    def mda009(self):
        """
        IMAP AUTHENTICATE command is supported
        """
        i = self.connimap(new=True)
        if not i:
            return("Pending", "IMAP not available")
        i.folder_encode = False         # don't use UTF7
        i._imap._mode_utf8()            # HACK allow UTF-8 login

        try:
            r = i.plain_login(self.tuser, self.tpwd)
        except imapclient.exceptions.LoginError as err:
            return("Fail", f"Authenticate failed {err}")
        return("Pass", f"Authenticate available")
        
    def doenable(self, i):
        """
        enable UTF8=ACCEPT
        """
        if self.didenable:
            return self.didenable
            
        if self.pconfig.getboolean('badenable', fallback=False):
            ### bogus enable at Coremail
            tag = i._imap._command('ENABLE', 'UTF8=ACCEPT')
            print("tag", tag)
            for n in range(4):
                l = i._imap._get_line()
                print(n, l)
                if l.startswith(b'* OK'):
                    self.didenable = ("Fail", "Enable does not return a result")
                    return self.didenable

        try:
            r = i.enable('UTF8=ACCEPT')
        except imapclient.exceptions.CapabilityError as err:
            self.didenable = ("Fail", f"Enable failed {err}")
            return self.didenable

        if r:
            self.didenable = ("Pass", f"Enabled {r}")
        else:
            self.didenable = ("Fail", "Enable failed")
        return self.didenable


    def mda010(self):
        """
        IMAP ENABLE UTF8=ACCEPT
        Coremail doesnt return ack, just * OK
        """
        i = self.connimap(login=True)
        if not i:
            return("Pending", "IMAP not available")
        print("try enable")
        r = self.doenable(i)
        return r

    def mda011(self):
        """
        SEARCH with charset fails
        """
        i = self.connimap(login=True)
        if not i:
            return("Pending", "IMAP not available")
        r = self.doenable(i)
        if r[0] != 'Pass':
            return("Fail", "UTF8 enabled not available")
        try:
            r = i.select_folder('INBOX')
        except imapclient.exceptions.IMAPClientError as err:
            return("Pending", f"Folder does not exist {err}")
        print("try search")
        try:
            r = i.search('ALL', charset='US-ASCII')
            return("Fail", "Search accepted")
        except imapclient.exceptions.IMAPClientError as err:
            return("Pass", f"Search failed {err}")
            
    # APPEND for 012 and 013
    def doappend(self, i):
        """
        create a test message and append it
        """
        if self.appresult:
            return self.appresult       # already did it

        # get cookie for subject
        self.msgseq = self.genseq('eaisubj')

        # create EAI message 
        # fake TO if not an EAI test address
        faketo = self.pconfig.get('faketo') or self.testaddr
        
        msg = self.genmsg('eaisubj', From=self.pconfig.get('srvfrom'), To=faketo, msgseq=self.msgseq)
        msg = ("".join(msg)).replace('\n','\r\n').encode('utf8')
        self.appmsg = msg
        try:
            r = i._imap.append(None, None, None, msg)
            #print("append", r)
            if r[0] == 'OK':
                self.appresult = ("Pass", "APPEND worked")
                return self.appresult
            self.appresult = ("Fail", f"APPEND failed {r[1]}")
            return self.appresult
        except imaplib.IMAP4.error as err:
            self.appresult = ("Fail", f"APPEND failed {err}")
            return self.appresult

    def mda012(self):
        """
        APPEND UTF-8 works
        use imaplib append because it does utf8
        """
        i = self.connimap(login=True)
        if not i:
            return("Pending", "IMAP not available")
        r = self.doenable(i)
        if r[0] != 'Pass':
            return("Fail", "UTF8 enabled not available")
        r = self.doappend(i)
        return r
        
    def mda013(self):
        """
        Check that appended message is OK
        """
        i = self.connimap(login=True)
        if not i:
            return("Pending", "IMAP not available")
        r = self.doenable(i)
        if r[0] != 'Pass':
            return("Fail", "UTF8 enabled not available")
        r = self.doappend(i)
        if r[0] != "Pass":
            return("Pending", r[1])

        # now try and retrieve it
        msg = self.getimap(subject=self.msgseq)
        if not msg:
            return("Pending", "Cannot get message")
        (hdrs, mout, msgtxt) = self.parsemsg(msg)

        for h in ('from','to','subject'):
            if h not in hdrs:
                return("Fail", f"Damaged or missing {h} header")
            if not self.iseai(hdrs[h][0]):
                return("Fail", f"Bad {hdrs[h][0]}")
        return("Pass", "Message retrieved")
                
    # for folder tests
    def dofolder(self, i, new=False, cheat=False):
        if not new and self.fname:
            return True
        # HACK turn off folder encoding
        self.doenable(i)
        i._imap._mode_utf8()
        # to make Coremail creates work
        i.folder_encode = cheat
        self.fname = f"测试{int(time.time())}"
        try:
            r = i.create_folder(self.fname)
        except imapclient.exceptions.IMAPClientError as err:
            return("Fail", f"Create failed {err}")

        i.folder_encode = False

        if type(r) is bytes:
            r = r.decode()
        print("folder created", self.fname, r)
        return('Pass', f"Create {self.fname} worked {r}") 

    def mda014(self):
        """
        Check that UTF-8 CREATE works
        """
        i = self.connimap(login=True, new=True)
        r = self.doenable(i)
        if r[0] != 'Pass':
            return("Fail", "UTF8 enabled not available")
        r = self.dofolder(i, new=True)
        print("first", r)
        if r[0] == "Pass":
            return r
        r = self.dofolder(i, cheat=True)
        print("retry", r)
        return ("Fail", r[1]+" with wrong encoding")
            

    def mda015(self):
        """
        check that select folder works
        """
        i = self.connimap(login=True)
        r = self.doenable(i)
        if r[0] != 'Pass':
            return("Fail", "UTF8 enabled not available")
        self.dofolder(i)
        try:
            r = i._imap.select(self.fname, readonly=False)
        except imaplib.IMAP4.error as err:
            return("Fail", f"Select failed {err}")

        if r[0] == "YES":
            return("Pass", f"Select worked {r[1]}")
        return("Fail", f"Select failed {r[1]}")

    def mda016(self):
        """
        check that examine folder works
        need to use imaplib select readonly
        """
        i = self.connimap(login=True)
        r = self.doenable(i)
        if r[0] != 'Pass':
            return("Fail", "UTF8 enabled not available")
        self.dofolder(i)
        try:
            r = i._imap.select(self.fname, readonly=True)
        except imaplib.IMAP4.error as err:
            return("Fail", f"Examine {self.fname} failed {err}")

        if r[0] == "YES":
            return("Pass", f"Examine worked {r[1]}")
        return("Fail", f"Examine failed {r[1]}")

    def mda017(self):
        """
        check that subscribe folder works
        need to use imaplib
        """
        i = self.connimap(login=True)
        r = self.doenable(i)
        if r[0] != 'Pass':
            return("Fail", "UTF8 enabled not available")
        self.dofolder(i, cheat=True)
        try:
            r = i.subscribe_folder(self.fname)
        except imaplib.IMAP4.error as err:
            return("Fail", f"Subscribe failed {err}")
        print("sub", r)

        if r:
            return("Pass", f"Subscribe worked {r[0].decode()}")
        return("Fail", f"Subscribe failed")

    def mda018(self):
        """
        check that list folder works
        need to use imaplib
        """
        i = self.connimap(login=True)
        r = self.doenable(i)
        if r[0] != 'Pass':
            return("Fail", "UTF8 enabled not available")
        r = self.dofolder(i)
        print("dofolder", r)
        try:
            r = i.list_folders()
        except imaplib.IMAP4.error as err:
            return("Fail", f"List failed {err}")
        fl = [ x[2].decode() for x in r]
        if self.fname in fl:
            return("Pass", "Folder found")
        print("fname", self.fname, "fl", fl)
        return("Fail", "Folder not found")

    def mda019(self):
        """
        check that LSUB works
        """
        i = self.connimap(login=True)
        r = self.doenable(i)
        if r[0] != 'Pass':
            return("Fail", "UTF8 enabled not available")
        self.dofolder(i, cheat=True)
        try:
            r = i.list_sub_folders()
        except imaplib.IMAP4.error as err:
            return("Fail", f"Subscribe failed {err}")
        fl = [ x[2].decode() for x in r]
        if self.fname in fl:
            return("Pass", "Folder found")
        print("lsub", fl)
        return("Fail", "Folder not found")

    def mda020(self):
        """
        create IMAP mailbox name
        """
        i = self.connimap(login=True)
        r = self.doenable(i)
        if r[0] != 'Pass':
            return("Fail", "UTF8 enabled not available")
        r = self.dofolder(i, new=True)
        print("first", r)
        return ("Fail", r[1])

    def mda021(self):
        """
        subscribe to Unicode works
        """
        return self.mda017()

    def mda022(self):
        """
        open Unicode IMAP folder
        same as SELECT
        """
        return self.mda015()
        
    def imretrieve(self, header):
        """
        check retrieve of a particular header
        """
        i = self.connimap(login=True)
        if not i:
            return("Pending", "IMAP not available")
        r = self.doappend(i)
        if r[0] != "Pass":
            return("Pending", r[1])

        # now try and retrieve it
        msg = self.getimap(subject=self.msgseq)
        if not msg:
            return("Pending", "Cannot get message")
        (hdrs, mout, msgtxt) = self.parsemsg(msg)

        if header not in hdrs:
            return("Fail", f"Damaged or missing {header} header")
        if not self.iseai(hdrs[header][0]):
            return("Fail", f"Bad {hdrs[header][0]}")
        return("Pass", f"Message with {header} header")

    def mda023(self):
        """
        store message with EAI From
        """
        return self.imretrieve('from')
        
    def mda024(self):
        """
        store message with EAI To
        """
        return self.imretrieve('to')

    def mda025(self):
        """
        store message with EAI Subject
        """
        return self.imretrieve('subject')
   
    def mda026(self):
        """
        retrieve message with EAI From
        """
        return self.imretrieve('from')
        
    def mda027(self):
        """
        retrieve message with EAI To
        """
        return self.imretrieve('to')

    def mda028(self):
        """
        retrieve message with EAI Subject
        """
        return self.imretrieve('subject')

    # POP tests
        
    def mda029(self):
        """
        check POP UTF8 capability
        """
        p = self.connpop()
        r = p.capa()
        if 'UTF8' in r or 'utf8' in r:
            return("Pass", "UTF8 available")
        return("Fail", "UTF8 not available")
        
    def mda030(self):
        """
        check that UTF8 works
        """
        p = self.connpop()
        try:
            r = p.utf8()
        except poplib.error_proto as err:
            return("Fail", f"UTF8 failed {err}")

        if r.startswith(b'+OK'):
            return("Pass", "UTF8 works")
        return("Fail", f"UTF8 fails (r)")
        
    def mda031(self):
        """
        check that UTF8 USER works
        """
        p = self.connpop()
        try:
            r = p.user(self.tuser)
        except poplib.error_proto as err:
            return("Fail", f"USER fails {err}")
        if not r.startswith(b'+OK'):
            return("Fail", f"USER fails (r)")
        try:
            r = p.pass_(self.tpwd)
        except Exception as err:
            return("Fail", f"PASS fails {err}")
        if not r.startswith(b'+OK'):
            return("Fail", f"PASS fails (r)")
        return("Pass", "UTF8 USER works")

    def mda032(self):
        """
        check that UTF8 LANG exists
        """
        p = self.connpop(login=True)
        if not p:
            return("Pending", "Cannot log in for POP")
        r = p.capa()
        if 'LANG' in r or 'lang' in r:
            return("Pass", "LANG available")
        return("Fail", "LANG not available")
        
    def mda033(self):
        """
        check that UTF8 LANG works
        """
        poplang = self.pconfig.get('poplang', fallback='en')
        p = self.connpop(login=True)
        # fake LANG command
        try:
            r = p._shortcmd('LANG '+poplang)
        except poplib.error_proto as err:
            return ("Fail", f"LANG failed {err}")

        if r.startswith(b'+OK'):
            return("Pass", f"LANG works {r[3:].decode()}")
        return("Fail", f"LANG failed {r[3:].decode()}")

    def mda034(self):
        """
        check that late STLS fails
        """
        p = self.connpop(login=True)
        try:
            r = p.stls()
        except poplib.error_proto as err:
            return("Pass", f"STLS rejected {err}")
        return("Fail", f"STLS not rejected {r}")

    def mda035(self):
        """
        check that LIST reports octets
        """
        p = self.connpop(login=True)
        (rcmd, rl, rlen) = p.list()
        # try the first message
        msgno, msglen = rl[0].decode().split(maxsplit=1)
        print("msgno",msgno,"msglen",msglen)
        (mcmd, ml, mlen) = p.retr(msgno)
        # length + CRLF for each line
        l1 = sum(map(len,ml))
        lx = 2*len(ml) + l1
        if mlen == lx:
            return("Pass", "Length in octets")
        return("Fail", f"Bad length {mlen} {lx} {l1} {len(ml)}")
            
    def mda036(self):
        """
        check UTF8 USER
        """
        if self.iseai(self.tuser):
            if self.connpop(login=True):
                return("Pass", "UTF8 USER works")
            return("Fail", f"UTF8 USER failes {self.tuser}")
        return("NA", "No UTF8 user")
            
    def getpopmsg(self, hdr=None):
        """
        get and parse a POP message
        look for one with an EAI header
        """
        if self.popmsg and not hdr:
            return self.popmsg

        p = self.connpop(login=True)
        (rcmd, rl, rlen) = p.list()
        pn = self.pconfig.getint('popno', fallback=0)  # use fixed message number
        if pn:
            rl = [ f"{pn} 999".encode() ]
        for rm in rl:
            msgno, msglen = rm.decode().split(maxsplit=1)
            print("msgno",msgno,"msglen",msglen)
            (mcmd, ml, mlen) = p.retr(msgno)

            msg = [ l.decode('utf8', errors='replace') for l in ml ]
            self.popmsg = self.parsemsg(msg)
            if not hdr:
                break
            if self.iseai(self.popmsg[0][hdr][0]):
                break
            print(f"try another {self.popmsg[0][hdr][0]}")

        return self.popmsg

    def mda037(self):
        """
        check From header
        """
        (hdrs, mout, msg) = self.getpopmsg(hdr='from')
        h = hdrs['from'][0]
        if self.iseai(h):
            return("Pass", f"UTF8 From {h}")
        return("Fail", f"ASCII From {h}")

    def mda038(self):
        """
        check To header
        """
        (hdrs, mout, msg) = self.getpopmsg(hdr='to')
        h = hdrs['to'][0]
        if self.iseai(h):
            return("Pass", f"UTF8 To {h}")
        return("Fail", f"ASCII To {h}")

    def mda039(self):
        """
        check Subject header
        """
        (hdrs, mout, msg) = self.getpopmsg(hdr='subject')
        h = hdrs['subject'][0]
        if self.iseai(h):
            return("Pass", f"UTF8 Subject {h}")
        return("Fail", f"ASCII Subject {h}")
        


            ################# main stub
if __name__=="__main__":
    import argparse

    parser = argparse.ArgumentParser(description='MDA test client')
    parser.add_argument('-d', action='store_true', help="Use debug server")
    parser.add_argument("-p", help="Product name")
    parser.add_argument("-n", type=int, help="Max number of tests")
    parser.add_argument("tests", nargs='*', help="optional list of tests")
    
    args = parser.parse_args()

    if not args.p:
        print("Need product name")
        exit()

    t = MDATestgroup(args.p, debug=args.d)
    if args.tests:
        tl = args.tests
    else:
        tl = t.testlist(all=True)
        if args.n:
            tl = tl[:args.n]
    
    t.dotests(tl)
