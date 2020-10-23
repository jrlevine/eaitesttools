#!/usr/local/bin/python3
#
# Do MTA tests

from testgroup import Testgroup, TestError
import smtplib
import paramiko
import re

class MTATestgroup(Testgroup):
    """
    tests for MTA
    """
    def __init__(self, product, config="config.txt", debug=False):
        super().__init__('MTA', product, config=config, debug=debug)

        #print(self.config)
        self.messages = {}
        self.msgtime =  self.pconfig.getint('msgtime',fallback=2) # how many mins to wait for a message to arrive
        # target address on server being tested
        self.testaddr = self.pconfig.get('fromaddr') or self.pconfig.get('asciifrom')

    def csend(self, msg, From=None, To=None, eaiflag=True):
        """
        send a message to the MX host
        as an SMTP client
        """

        if type(msg) != str:            # if it's a list of lines
            msg = "".join(msg)
        bmsg = msg.encode('utf8')
        sc = self.cconnect(starttls=True)
        if not sc:
            print("cconnect failed")
            return False
        print("after SMTP cconnect",sc)
        try:
            if eaiflag:
                self.csock.sendmail(From, To, bmsg, mail_options=('SMTPUTF8',))
            else:
                self.csock.sendmail(From, To, bmsg)
        except smtplib.SMTPException as err:
            self.submiterror = err
            return False
        return True

    def mta001(self):
        """
        test that SMTPUTF8 in banner
        """
        print("connect to", self.mailserver)
        if not self.cconnect():
            return (None, "Cannot connect to server")
        if not self.csock.has_extn('SMTPUTF8'):
            return ("Fail", f"Missing in server, EHLO response was {self.csock.ehlo_resp.decode()}")

        if not self.cconnect(starttls=True):
            return (None, "Cannot do STARTTLS")
        if not self.csock.has_extn('SMTPUTF8'):
            return ("Fail", f"Missing after STARTLS, EHLO response was {self.csock.ehlo_resp.decode()}")

        return ("Pass", "Capability is present")

    def mta002(self):
        """
        test that 8BITMIME in banner
        """
        print("connect to", self.mailserver)
        if not self.cconnect(starttls=False):
            return (None, "Cannot connect to server")
        if not self.csock.has_extn('8BITMIME'):
            return ("Fail", f"Missing in server, EHLO response was {self.csock.ehlo_resp.decode()}")

        if not self.cconnect(starttls=True):
            return (None, "Cannot do STARTTLS")
        if not self.csock.has_extn('8BITMIME'):
            return ("Fail", f"Missing after STARTLS, EHLO response was {self.csock.ehlo_resp.decode()}")

        return ("Pass", "Capability is present")

    def mta003(self):
        """
        test that EHLO arg is sent as ASCII
        """
        pmsg = self.domsg('plain', From=self.testaddr, To=self.pconfig.get('toaddr'), getrmt=True,
            eaiflag=True)
        if not pmsg:
            return ('Fail', f"Cannot send test message {self.submiterror}")

        rl = None
        (dhdrs, lhdrs, body) = pmsg
        
        for rx in dhdrs['received']:
            if 'mail1.iecc.com' in rx:
                rl = rx
                break
        if not rl:
            return ('Pending', 'Cannot find received header', dhdrs['received'])
        r = re.match(r'\s*from ([-a-zA-Z0-9.]+) ', rl)
        if r:
            if 'xn--' in r.group(1):
                return ('Pass', 'A-Label HELO '+r.group(1))
            return ('Pass', 'Non IDN HELO '+r.group(1))
        return ('Fail', 'Non-ASCII HELO '+rl)

    def mta004(self):
        """
        test that MAIL FROM includes SMTPUTF8
        """
        pmsg = self.domsg('plain', From=self.testaddr, To=self.pconfig.get('toaddr'), getrmt=True,
            eaiflag=True)
        if not pmsg:
            return ('Fail', f"Cannot send test message {self.submiterror}")

        rl = None
        (dhdrs, lhdrs, body) = pmsg
        
        for rx in dhdrs['received']:
            if 'mail1.iecc.com' in rx:
                rl = rx
                break
        if not rl:
            return ('Pending', 'Cannot find received header', dhdrs['received'])
        r = re.search(r'with ([a-zA-Z0-9.]+) via ', rl)
        if r:
            withparm = r.group(1)
            if withparm.upper().startswith('UTF8SMTP'):
                return ('Pass', 'UTF8 message send with '+withparm)
        return ('Fail', 'No UTF8SMTP parameter'+rl)

    def mta005(self):
        """
        check if hostname in added Received uses U-label
        send messgage in via SMTP from external address to local address
        """
        fromaddr = self.pconfig.get('srvfrom')
        toaddr = self.testaddr
        print("mta005",fromaddr,"->",toaddr)            
        pmsg = self.domsg('headerplain', From=fromaddr, To=toaddr,
            getrmt=False, eaiflag=True, sendmail=True)
        if not pmsg:
            return ('Fail', f"Cannot send test message {self.submiterror}")

        (dhdrs, lhdrs, body) = pmsg

        r = None
        for rx in dhdrs['received']:
            if 'by ' in rx and 'iecc.com' not in rx:
                r = rx
                break
        if not r:
            return ('Pending', 'No useful received: '+repr(dhdrs['received']))

        # strip nested comments, but stop if they're malformed
        for i in range(10):
            if '(' not in r:
                break
            r = re.sub(r'\([^()]*\)', ' ', r)

        # look for host's own name
        rm = re.search(r'by\s+(\S+)\s', r)
        if not rm:
            return ('Pending', 'No host name in received: '+repr(dhdrs['received']))
        host = rm.group(1).lower()
        if 'xn--' in host:
            return('Fail', 'A-labels in own host name '+host)
        return('Pass', 'No A-labels in own host name '+host)
                
    def mta006(self):
        """
        check if hostname in added Received says UTF8SMTP
        send messgage in via SMTP from external address to local address
        """
        fromaddr = self.pconfig.get('srvfrom')
        toaddr = self.testaddr
        print("mta006",fromaddr,"->",toaddr)            
        pmsg = self.domsg('headerplain', From=fromaddr, To=toaddr,
            getrmt=False, eaiflag=True, sendmail=True)
        if not pmsg:
            return ('Fail', f"Cannot send test message {self.submiterror}")

        (dhdrs, lhdrs, body) = pmsg

        r = None
        oldrx = None
        for rx in dhdrs['received']:
            if 'eaitest.local' in rx or 'gal.iecc.com' in rx:   # look for our own name
                r = rx
                break
            oldrx = rx
        if not r:
            return ('Pending', 'No useful received: '+repr(dhdrs['received']))

        # strip nested comments, but stop if they're malformed
        origr = r
        for i in range(10):
            if '(' not in r:
                break
            r = re.sub(r'\([^()]*\)', ' ', r)

        # look for proto own name
        rm = re.search(r'with\s+(\S+)\s', r)
        if not rm:
            return ('Pending', 'No protocol: '+r)
        proto = rm.group(1).upper()
        if proto.startswith('UTF8SMTP'):
            return('Pass', 'Protocol is '+proto)
        if proto.startswith('UTF8ESMTP'):
            return('Fail', 'Protocol is misspelled '+proto)
        return('Fail', f'Protocol {proto} in\nReceived: {origr}')

    def mta007(self):
        """
        check that MAIL FROM has U-labels
        submit locally, check on home server
        """
        pmsg = self.domsg('headerplain', From=self.testaddr, To=self.pconfig.get('toaddr'),
            eaiflag=True, getrmt=True)
        if not pmsg:
            return ('Fail', f"Cannot send test message {self.submiterror}")

        rl = None
        (dhdrs, lhdrs, body) = pmsg

        mailfrom = dhdrs['eai-from'][0].lower()
        if 'xn--' in mailfrom:
            return ('Fail', 'A-labels in MAIL FROM '+mailfrom)
        return ('Pass', 'EAI MAIL FROM '+mailfrom)
                
        
    def mta008(self):
        """
        check that RCPT TO has U-labels
        submit locally, check on home server
        """
        pmsg = self.domsg('headerplain', From=self.testaddr, To=self.pconfig.get('toaddr'),
            eaiflag=True, getrmt=True)
        if not pmsg:
            return ('Fail', f"Cannot send test message {self.submiterror}")

        rl = None
        (dhdrs, lhdrs, body) = pmsg

        rcptto = dhdrs['eai-rcpt'][0].lower()
        if 'xn--' in rcptto:
            return ('Fail', 'A-labels in RCPT TO '+rcptto)
        return ('Pass', 'EAI RCPT TO '+rcptto)

    def mta009(self):
        """
        check that From is U-labels
        submit locally, check on home server
        """
        pmsg = self.domsg('headerplain', From=self.testaddr, To=self.pconfig.get('toaddr'),
            eaiflag=True, getrmt=True)
        if not pmsg:
            return ('Fail', f"Cannot send test message {self.submiterror}")

        rl = None
        (dhdrs, lhdrs, body) = pmsg

        hfrom = dhdrs['from'][0].lower()
        if 'xn--' in hfrom:
            return ('Fail', 'A-labels in header From '+hfrom)
        return ('Pass', 'Header From '+hfrom)

    def mta010(self):
        """
        check that To is U-labels
        submit locally, check on home server
        """
        pmsg = self.domsg('headerplain', From=self.testaddr, To=self.pconfig.get('toaddr'),
            eaiflag=True, getrmt=True)
        if not pmsg:
            return ('Fail', f"Cannot send test message {self.submiterror}")

        rl = None
        (dhdrs, lhdrs, body) = pmsg

        hto = dhdrs['to'][0].lower()
        if 'xn--' in hto:
            return ('Fail', 'A-labels in header To '+hto)
        return ('Pass', 'Header To '+hto)

    def mta011(self):
        """
        check that Subject is Unicode
        submit locally, check on home server
        """
        pmsg = self.domsg('headerplain', From=self.testaddr, To=self.pconfig.get('toaddr'),
            eaiflag=True)
        if not pmsg:
            return ('Fail', f"Cannot send test message {self.submiterror}")

        rl = None
        (dhdrs, lhdrs, body) = pmsg

        hsubject = dhdrs['subject'][0].lower()
        if '=?' in hsubject:
            return ('Fail', 'Encoded Subject '+hsubject)
        if self.iseai(hsubject):
            return ('Pass', 'UTF-8 Subject '+hsubject)
        return ('Pending', 'Mystery Subject '+hsubject)

    def mta012(self):
        """
        check that ASCII message doesn't use SMTPUTF8
        submit locally, check on home server
        """
        fromaddr = self.pconfig['asciifrom']
        toaddr = self.pconfig['asciito']
        
        pmsg = self.domsg('plain', From=fromaddr, To=toaddr, submit=True, getrmt=True)
        if not pmsg:
            return ('Fail', f"Cannot send test message {self.submiterror}")

        (dhdrs, lhdrs, body) = pmsg
        r = None
        for rx in dhdrs['received']:
            if 'mail1.iecc.com' in rx:
                r = rx
                break
        if not r:
            return ('Pending', 'No useful received: '+repr(dhdrs['received']))

        # strip nested comments, but stop if they're malformed
        for i in range(10):
            if '(' not in r:
                break
            r = re.sub(r'\([^()]*\)', ' ', r)

        # look for proto own name
        rm = re.search(r'with\s+(\S+)\s', r)
        if not rm:
            return ('Pending', 'No protocol name in received: '+repr(dhdrs['received']))
        proto = rm.group(1).upper()

        if proto.startswith('UTF8SMTP'):
            return('Fail', 'Protocol is '+proto)
        return('Pass', 'Protocol is '+proto)

    def mta013(self):
        """
        check that EAI message to non-EAI server fails
        submit locally, check on home server, then check for local bounce
        """
        fromaddr = self.testaddr
        toaddr = self.pconfig.get( 'noeaito')

        pmsg = self.domsg('eaisubj', From=fromaddr, To=toaddr, submit=True, eaiflag=True, getrmt=True, maxcheck=3)
        if pmsg:
            return ('Fail', "Message sent anyway")
            
        # see if we have a bounce
        pmsg = self.getmori(maxcheck=1, maxage=180) # allow extra time for prior timeout
        if pmsg:
            (dhdrs, lhdrs, body) = self.parsemsg(pmsg)
            # see if there is a Diagnostic
            dl = tuple(l for l in body if 'Diagnostic' in l)
            if dl:
                bm = dl[0]
            else:
                bm = dhdrs['subject'][0]
            return ('Pass', "Test message not received, likely bounce "+bm)
        return ('Pass', "Test message not received")

################# main stub for debugging
if __name__=="__main__":
    import argparse

    parser = argparse.ArgumentParser(description='MTA test client')
    parser.add_argument('-d', action='store_true', help="Use debug server")
    parser.add_argument("-p", help="Product name")
    parser.add_argument("-n", type=int, help="Max number of tests")
    parser.add_argument("tests", nargs='*', help="optional list of tests")
    
    args = parser.parse_args()

    if not args.p:
        raise TestError("Need product name")
        

    t = MTATestgroup(args.p, debug=args.d)
    if args.tests:
        tl = args.tests
    else:
        tl = t.testlist(all=True)
        if args.n:
            tl = t[:args.n]
    
    t.dotests(tl)
