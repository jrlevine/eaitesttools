#!/usr/local/bin/python3
#
# Do MSA tests

from testgroup import Testgroup, TestError
import time

class MSATestgroup(Testgroup):
    """
    tests for MSA
    """
    def __init__(self, product, config="config.txt", debug=False):
        super().__init__('MSA', product, config=config, debug=debug)

        self.msgtime =  self.pconfig.getint('msgtime',fallback=2) # how many mins to wait for a message to arrive
        self.user = self.pconfig.get('submituser')
        self.passwd = self.pconfig.get('submitpass')
        self.messages = {}
        self.standalone = self.pconfig.getboolean('standalone')
        self.downgrade = self.pconfig.getboolean('downgrade')
        self.nosubeai = self.pconfig.getboolean('nosubeai')

    # specific tests
    # return tuple of True (Pass) / False (Fail) / None (Pending),
    # and comment


    def msa001(self):
        """
        test that SMTPUTF8 in banner
        """
        atleastone = False
        cmnt = ""

        print("connect to", self.sserver)
        # port 587 banner
        if self.subconnect(port=self.submitport):
            print("try plain submit")
            if not self.ssock.has_extn('SMTPUTF8'):
                return ("Fail", f"Missing in submit, EHLO response was {self.ssock.ehlo_resp.decode()}")
            atleastone = True

            print("try STARTTLS submit")
            if self.subconnect(starttls=True):
                if not self.ssock.has_extn('SMTPUTF8'):
                    return ("Fail", f"Missing after STARTLS, EHLO response was {self.ssock.ehlo_resp.decode()}")
            else:
                cmnt = "\nDoes not do STARTTLS"
        else:
            cmnt = f"\nDoes not do port {self.submitport} SUBMIT"

        print("try submits")
        if self.submits and self.subconnect(smtps=True):
            if not self.ssock.has_extn('SMTPUTF8'):
                return ("Fail", f"Missing SMTPUTF8 in submits, EHLO response was {self.ssock.ehlo_resp.decode()}")
            atleastone = True
        else:
            cmnt += "\nDoes not do SUBMITS"
        if atleastone:
            return ("Pass", "Capability is present"+cmnt)
        else:
            return('Fail', "No submission server found")

    def msa002(self):
        """
        test that 8BITMIME in banner
        """
        atleastone = False
        cmnt = ""

        print("connect to", self.sserver)
        # port 587 banner
        print("try plain submit")
        if self.subconnect(port=self.submitport):
            if not self.ssock.has_extn('8BITMIME'):
                return ("Fail", f"Missing in submit, EHLO response was {self.ssock.ehlo_resp.decode()}")
            atleastone = True

            print("try STARTTLS submit")
            if self.subconnect(starttls=True):
                if not self.ssock.has_extn('8BITMIME'):
                    return ("Fail", f"Missing after STARTLS, EHLO response was {self.ssock.ehlo_resp.decode()}")
            else:
                cmnt = "\nDoes not do STARTTLS"
        else:
            cmnt = f"\nDoes not do port {self.submitport} SUBMIT"

        print("try submits")
        if self.submits and self.subconnect(smtps=True):
            if not self.ssock.has_extn('8BITMIME'):
                return ("Fail", f"Missing in submits, EHLO response was {self.ssock.ehlo_resp.decode()}")
            atleastone = True
        else:
            cmnt += "\nDoes not do SUBMITS"
        if atleastone:
            return ("Pass", "Capability is present"+cmnt)
        else:
            return('Fail', "No submission server found")

    def msa003(self):
        if not self.standalone:
            return ("NA", "Test not applicable")
        return None

    def msa004(self):
        if not self.standalone:
            return ("NA", "Test not applicable")
        return None

    def msa005(self):
        """
        test that it sends UTF-8 reverse path
        """
        fromaddr = self.pconfig.get('fromaddr')
        toaddr = self.pconfig.get('toaddr')

        if not fromaddr:
            return("NA", "No UTF-8 sending address")

        assert fromaddr and toaddr

        pmsg = self.domsg('plain', From=fromaddr, To=toaddr, getrmt=True)
        if not pmsg:
            return ('Fail', f"Cannot send test message {self.submiterror}")
        (dhdrs, lhdrs, body) = pmsg
        if 'eai-from' in dhdrs:
            if dhdrs['eai-from'][0] == fromaddr:
                return('Pass', f"Envelope from is {fromaddr}")
            else:
                return('Fail', f"Envelope from is {dhdrs['eai-from']}")
        else:
            return('Fail', f"Envelope from is missing, {dhdrs['return-path']}")
            
    def msa006(self):
        """
        test that it sends UTF-8 recipient
        """
        fromaddr = self.pconfig.get('fromaddr') or self.pconfig.get('asciifrom')
        toaddr = self.pconfig.get('toaddr')

        pmsg = self.domsg('plain', From=fromaddr, To=toaddr, getrmt=True, eaiflag=not self.nosubeai)
        if not pmsg:
            return ('Fail', f"Cannot send test message {self.submiterror}")
        (dhdrs, lhdrs, body) = pmsg
        if 'eai-rcpt' in dhdrs:
            if dhdrs['eai-rcpt'][0] == toaddr:
                return('Pass', f"Envelope to is {toaddr}")
            else:
                return('Fail', f"Envelope to is {dhdrs['eai-rcpt'][0]}")
        else:
            return('Fail', f"Envelope to is missing, {dhdrs['delivered-to']}")
            
    def msa007(self):
        """
        test that it sends UTF-8 From: header
        """
        fromaddr = self.pconfig.get( 'fromaddr')
        toaddr = self.pconfig.get( 'toaddr')

        if not fromaddr:
            return("NA", "No UTF-8 sending address")

        pmsg = self.domsg('plain', From=fromaddr, To=toaddr, getrmt=True)
        if not pmsg:
            return ('Fail', f"Cannot send test message {self.submiterror}")
        (dhdrs, lhdrs, body) = pmsg
        if 'from' in dhdrs:
            msgfrom = dhdrs['from'][0]
            if fromaddr in msgfrom:
                return ('Pass', f"UTF-8 From header: {msgfrom}")
            else:
                return ('Fail', f"No UTF-8 From header: {msgfrom}")
            
    def msa008(self):
        """
        test that it sends UTF-8 To: header
        """
        fromaddr = self.pconfig.get( 'fromaddr') or self.pconfig.get('asciifrom')
        toaddr = self.pconfig.get( 'toaddr')

        pmsg = self.domsg('plain', From=fromaddr, To=toaddr, getrmt=True)
        if not pmsg:
            return ('Fail', f"Cannot send test message {self.submiterror}")

        (dhdrs, lhdrs, body) = pmsg
        if 'to' in dhdrs:
            msgto = dhdrs['to'][0]
            if toaddr in msgto:
                return ('Pass', f"UTF-8 To header: {msgto}")
            else:
                return ('Fail', f"No UTF-8 To header: {msgto}")
            
    def msa009(self):
        """
        test that it sends UTF-8 Subject: header
        """
        fromaddr = self.pconfig.get( 'fromaddr') or self.pconfig.get('asciifrom')
        toaddr = self.pconfig.get( 'toaddr')

        pmsg = self.domsg('eaisubj', From=fromaddr, To=toaddr, getrmt=True)
        if not pmsg:
            return ('Fail', f"Cannot send test message {self.submiterror}")

        (dhdrs, lhdrs, body) = pmsg
        subject = dhdrs['subject'][0]
        if '中国' in subject:
            return ('Pass', "Message has unencoded UTF-8 subject")
        return ('Fail', "Message subject was "+subject)
            
    def msa010(self):
        """
        test that it sends ASCII messages as not EAI
        """
        fromaddr = self.pconfig.get( 'asciifrom')
        toaddr = self.pconfig.get( 'asciito')

        if not fromaddr:
            return('NA', 'No ASCII test address available')

        pmsg = self.domsg('plain', From=fromaddr, To=toaddr, eaiflag=False, getrmt=True)
        if not pmsg:
            return ('Fail', f"Cannot send test message {self.submiterror}")

        (dhdrs, lhdrs, body) = pmsg
        # find relay received line
        r = None
        for rx in dhdrs['received']:
            if 'mail1.iecc.com' in rx:
                r = rx
                break
        if not r:
            return ('NA', 'Cannot find received header', dhdrs['received'])
        if 'with UTF8' not in r:
            return ('Pass', 'Message sent as ASCII '+r)
        return ('Fail', 'Message not sent as ASCII '+r)

    def msa011(self):
        """
        test that EAI messages to ASCII host fail
        or are downgraded
        """
        fromaddr = self.pconfig.get( 'fromaddr') or self.pconfig.get('asciifrom')
        toaddr = self.pconfig.get( 'noeaito')

        self.submiterror = None
        pmsg = self.domsg('eaisubj', From=fromaddr, To=toaddr, getrmt=True)
        if pmsg:
            (dhdrs, lhdrs, body) = pmsg
            if self.iseai(dhdrs['return-path'][0]) or self.iseai(dhdrs['delivered-to'][0]) or self.iseai(dhdrs['subject'][0]):
                return ('Fail', f"Message sent anyway\nreturn path {dhdrs['return-path'][0]}\n" \
                    f"recipient {dhdrs['delivered-to'][0]}\nsubject {dhdrs['subject'][0]}")

            return('NA', "Message downgraded\nreturn path {dhdrs['return-path'][0]}\n" \
                    f"recipient {dhdrs['delivered-to'][0]}\nsubject {dhdrs['subject'][0]}")
        elif self.submiterror:
            return ('NA', f"Cannot send test message {self.submiterror}")

        # see if we have a bounce locally
        pmsg = self.getmori(maxcheck=1)
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

    def msa012(self):
        """
        See if EAI mail AA@UU from is downgraded
        """
        fromaddr = self.pconfig.get( 'dgfrom') # downgradable from address
        toaddr = self.pconfig.get( 'noeaito')

        if not fromaddr:
            return('NA', "No downgradable address available")

        self.submiterror = None
        pmsg = self.domsg('plain', From=fromaddr, To=toaddr, getrmt=True)
        if pmsg:
            (dhdrs, lhdrs, body) = pmsg
            if 'eai-from' in dhdrs:
                return('Fail', f"Envelope from is {dhdrs['eai-from'][0]}")
            return ('Pass', "Message sent with ASCII return address")
        elif self.submiterror:
            return ('NA', f"Cannot send test message {self.submiterror}")
            
        # see if we have a bounce
        pmsg = self.getmori(prefix='dg', maxcheck=1)
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
        
    def msa013(self):
        """
        See if EAI rcpt to AA@UU is downgraded
        """
        fromaddr = self.pconfig.get( 'asciifrom')
        toaddr = self.pconfig.get( 'adgto') # downgradable to address in envelope
        atoaddr = self.pconfig.get( 'adgto') # downgraded to address in To header

        if not fromaddr:
            return('NA', 'No ASCII test address available')

        self.submiterror = None
        pmsg = self.domsg('plaindg', From=fromaddr, To=toaddr, bFrom=fromaddr, bTo=atoaddr, getrmt=True)
        if pmsg:
            (dhdrs, lhdrs, body) = pmsg
            if 'eai-rcpt' in dhdrs:
                return('Fail', f"Envelope recipient is {dhdrs['eai-rcpt'][0]}")
            return ('Pass', f"Message sent with ASCII recipient address {dhdrs['delivered-to'][0]}")
        elif self.submiterror:
            return ('NA', f"Cannot send test message {self.submiterror}")
            
        # see if we have a bounce
        pmsg = self.getmori(prefix='dg', maxcheck=1)
        if pmsg:
            (dhdrs, lhdrs, body) = self.parsemsg(pmsg)
            return ('Pass', "Test message not received, likely bounce "+dhdrs['subject'][0])
        return ('Pass', "Test message not received")
        
    # for MSAs that do downgrades
    # mas014 downgrade From
    def msa014(self):
        """
        See if From header address is downgraded
        """
        if not self.downgrade:
            return ("NA", "Test not applicable")
        fromaddr = self.pconfig.get( 'fromaddr')
        toaddr = self.pconfig.get( 'dgto') # downgradable to address
        atoaddr = self.pconfig.get( 'adgto') # downgraded to address

        if not fromaddr:
            return('NA', 'No ASCII test address available')

        self.submiterror = None
        pmsg = self.domsg('plaindgcc', From=fromaddr, To=toaddr, bFrom=fromaddr, bTo=atoaddr, getrmt=True)
        if pmsg:
            (dhdrs, lhdrs, body) = self.parsemsg(pmsg)
            if 'eai-from' in dhdrs:
                return('Fail', f"Envelope from is {dhdrs['eai-from'][0]}")
            return ('Pass', "Message sent with ASCII sender address")
        elif self.submiterror:
            return ('NA', f"Cannot send test message {self.submiterror}")
            
        return ('NA', "Test message not received")

    # msa015 downgrade To
    def msa015(self):
        """
        see if Cc address is downgraded
        """

        if not self.downgrade:
            return ("NA", "Test not applicable")
        fromaddr = self.pconfig.get( 'fromaddr')
        toaddr = self.pconfig.get( 'dgto') # downgradable to address
        atoaddr = self.pconfig.get( 'adgto') # downgraded to address

        if not fromaddr:
            return('NA', 'No ASCII test address available')

        self.submiterror = None
        pmsg = self.domsg('plaindgcc', From=fromaddr, To=toaddr, bFrom=fromaddr, bTo=atoaddr, getrmt=True)
        if pmsg:
            (dhdrs, lhdrs, body) = self.parsemsg(pmsg)
            if iseai(dhdrs['cc'][0]):
                return('Fail', f"Recipient not downgraded {dhdrs['cc'][0]}")
            return ('Pass', f"Message sent with downgraded recipient {dhdrs['cc'][0]}")
        elif self.submiterror:
            return ('NA', f"Cannot send test message {self.submiterror}")
            
        return ('NA', "Test message not received")

    # msa016 downgrade Subject
    def msa016(self):
        """
        see if subject is downgraded
        """

        fromaddr = self.pconfig.get( 'fromaddr') or self.pconfig.get( 'asciifrom')
        toaddr = self.pconfig.get( 'dgto') # downgradable to address
        atoaddr = self.pconfig.get( 'adgto') # downgraded to address

        if not fromaddr:
            return('NA', 'No ASCII test address available')

        self.submiterror = None
        pmsg = self.domsg('plaindgcc', From=fromaddr, To=toaddr, bFrom=fromaddr, bTo=atoaddr, getrmt=True)
        if pmsg:
            (dhdrs, lhdrs, body) = self.parsemsg(pmsg)
            if iseai(dhdrs['subject'][0]):
                return('Fail', f"Subject not downgraded {dhdrs['subject'][0]}")
            return ('Pass', "Message sent with downgraded subject {dhdrs['subject'][0]}")
        elif self.submiterror:
            return ('NA', f"Cannot send test message {self.submiterror}")
            
        return ('NA', "Test message not received")

    # msa017 ASCII message ID in downgraded message
    def msa017(self):
        """
        see if downgraded message has ASCII message-ID
        """
        if not self.downgrade:
            return ("NA", "Test not applicable")
        fromaddr = self.pconfig.get( 'fromaddr') or self.pconfig.get( 'asciifrom')
        toaddr = self.pconfig.get( 'dgto') # downgradable to address
        atoaddr = self.pconfig.get( 'adgto') # downgraded to address

        if not fromaddr:
            return('NA', 'No ASCII test address available')

        # send message with unique subject and see if we get it back
        self.submiterror = None
        pmsg = self.domsg('plaindgsub', From=fromaddr, To=toaddr, bFrom=fromaddr, bTo=atoaddr,
            getrmt=True)
        if pmsg:
            (dhdrs, lhdrs, body) = self.parsemsg(pmsg)
            msgid = dhdrs['message-id'][0]
            if iseai(msgid):
                return('Fail', f"Generated message-id is UTF-8 {msgid}")
            return('Pass', f"Generated message-id is ASCII {msgid}")
        elif self.submiterror:
            return ('NA', f"Cannot send test message {self.submiterror}")
            
        return ('NA', "Test message not received")



################# main stub for debugging
if __name__=="__main__":
    import argparse

    parser = argparse.ArgumentParser(description='MSA test client')
    parser.add_argument('-d', action='store_true', help="Use debug server")
    parser.add_argument('--dg', action='store_true', help="Do message downgrade tests")
    parser.add_argument('--sa', action='store_true', help="Do standalone MSA tests")
    parser.add_argument("-p", help="Product name")
    parser.add_argument("-n", type=int, help="Max number of tests")
    parser.add_argument("tests", nargs='*', help="optional list of tests")
    
    args = parser.parse_args()

    if not args.p:
        raise TestError("Need product name")

    t = MSATestgroup(args.p, debug=args.d)
    if args.tests:
        tl = args.tests
    else:
        tl = t.testlist(all=True)
        if args.n:
            tl = tl[:args.n]
    
    t.dotests(tl)
