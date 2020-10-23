#!/usr/local/bin/python3
#
# do tests and
# talk to remote client of eaitest

import tclient
import re
import paramiko
import datetime
import time
import hashlib
import string
import configparser
import smtplib
from email.base64mime import body_encode as encode_base64
import base64
import imapclient
import ssl
import subprocess

# patch smtplib to handle utf-8 login

class USMTP(smtplib.SMTP):
    def auth(self, mechanism, authobject, *, initial_response_ok=True):
        """Authentication command - requires response processing.

        'mechanism' specifies which authentication mechanism is to
        be used - the valid values are those listed in the 'auth'
        element of 'esmtp_features'.

        'authobject' must be a callable object taking a single argument:

        data = authobject(challenge)

        It will be called to process the server's challenge response; the
        challenge argument it is passed will be a bytes.  It should return
        a UTF-8 string that will be base64 encoded and sent to the server.

        Keyword arguments:
            - initial_response_ok: Allow sending the RFC 4954 initial-response
              to the AUTH command, if the authentication methods supports it.
        """
        # RFC 4954 allows auth methods to provide an initial response.  Not all
        # methods support it.  By definition, if they return something other
        # than None when challenge is None, then they do.  See issue #15014.
        mechanism = mechanism.upper()
        initial_response = (authobject() if initial_response_ok else None)
        if initial_response is not None:
            response = encode_base64(initial_response.encode(self.command_encoding), eol='')
            (code, resp) = self.docmd("AUTH", mechanism + " " + response)
        else:
            (code, resp) = self.docmd("AUTH", mechanism)
        # If server responds with a challenge, send the response.
        if code == 334:
            challenge = base64.decodebytes(resp)
            response = encode_base64(
                authobject(challenge).encode(self.command_encoding), eol='')
            (code, resp) = self.docmd(response)
        if code in (235, 503):
            return (code, resp)
        raise smtplib.SMTPAuthenticationError(code, resp)

class USMTP_SSL(smtplib.SMTP_SSL):
    auth = USMTP.auth


class TestError(Exception):
    pass

class Testgroup:
    """
    a bunch of tests of a single type on a single product
    """
    def __init__(self, testtype, product, config="config.txt", debug=False):
        """
        pass config file or dict if it's already been read
        """
        if not testtype:
            raise TestError("need testtype")
        self.testtype = testtype
        if not product:
            raise TestError("need product")
        self.product = product

        # use existing dict or read file
        if type(config) in (dict, configparser.ConfigParser):
            self.config = config
        else:
            self.config = configparser.ConfigParser()
            try:
                self.config.read_file(open(config, "r"))
            except configparser.ParsingError as err:
                raise TestError(err)
        self.pconfig = self.config[product]
                
        self.debug = debug

        # get the tests and results
        self.tclient = tclient.TClient(config=self.config, debug=debug)
        self.done = self.tclient.getresults(product, testtype, done=True)
        self.task = self.tclient.getresults(product, testtype, done=False)
        if not (self.task or self.done):
            raise TestError(f"No task for product {product}, type {testtype}")
        self.ssock = None                # socket to submission server
        self.login = False              # server logged in
        self.ssl = False
        self.sserver = self.pconfig.get('submitserver')
        self.submits = self.pconfig.getboolean('submits',fallback=False)
        self.submitport = self.pconfig.getint('submitport',fallback=587)
        self.subjseq = str(int(time.time()))      # subject code to find the message
        self.submiterror = None
        self.sstarttls = False
        self.csock = None               # socket to MTA
        self.cstarttls = False
        self.user = self.pconfig.get('submituser')
        self.passwd = self.pconfig.get( 'submitpass')
        self.idnhost = self.pconfig.getboolean( 'idnhost', fallback=False)

        self.mailserver = self.pconfig.get('mailserver')

    def testlist(self, all=False):
        """
        return list of tests in the current task
        all says include ones already done
        """

        if all:
            tt = self.task or []
            dd = self.done or []
            tl = [ t['testid'] for t in tt+dd ]
            tl.sort()
            return tl

        if self.task:
            tl = [ t['testid'] for t in self.task ]
            tl.sort()
            return tl

        return ()

    def dotests(self, tests):
        """
        do all the tests in a list we can do
        and upload the results
        """

        for test in tests:
            print("do",test)
            m = re.match(r'EAI-(?P<ttype>\w+)-(?P<seq>\d+)$', test)
            if not m:
                m = re.match(r'(?P<ttype>[a-z]{3})(?P<seq>\d{3})$', test)
                if not m:
                    print("Mystery test", test)
                    continue
            # routine is named xxx123
            tstrtn = m.group('ttype').lower()+m.group('seq')
            testid = f"EAI-{m.group('ttype').upper()}-{m.group('seq')}"

            # see if the routine exists in this class
            try:
                ptr = self.__class__.__dict__[tstrtn]
            except KeyError as err:
                print("No test",err)
                continue

            # call it and 
            print("do test",test)
            r = ptr(self)
            print("result of",test,"is",r)
            try:
                result, comment = r
            except (TypeError, ValueError) as err:
                print("odd result", r)
                continue
                
            # save it
            self.tclient.setresult(self.product, testid, result, comments=comment)

    def getmsg(self, prefix='', maxage=None, sltime=None,
        subject=None, maxcheck=None):
        """
        get a recently sent message via SSH from a Maildir target, where target is
        per product and prefix is name prefix in the config

        wait until there is a message no older than maxage seconds
        or look for one with subject
        up to maxcheck times, sltime pause between tries
        """

        if not maxage:
            maxage = 60
        if not maxcheck:
            maxcheck = 5
        if not sltime:
            sltime = 15

        thost = self.pconfig.get(prefix+'host')
        tport = self.pconfig.getint(prefix+'port', fallback=22)
        tuser = self.pconfig.get(prefix+'user')
        tdir = self.pconfig.get(prefix+'dir')

        print("getmsg", thost, tport, tuser, tdir)
        sshcl = paramiko.client.SSHClient()
        sshcl.load_system_host_keys()
        sshcl.connect(thost, username=tuser, port=tport)
        sftp = sshcl.open_sftp()

        # look in the /new subdirectory
        try:
#            print("chdir", tdir+'/new')
            sftp.chdir(tdir+'/new')
        except FileNotFoundError as err:
            print("Cannot chdir to",tdir)
            sshcl.close()
            return None
        # see what looks reasonably recent
        now = int(time.time())
        ncheck = 0                     # only do this 5 times
        seen = set()                    # files we've seen

        if self.debug and subject:
            print("find", subject)

        while ncheck < maxcheck:
            if ncheck:
                time.sleep(sltime)           # don't hammer too fast
                print("try",ncheck)
            ncheck += 1
            # files in /new directory
            dir = sftp.listdir_attr()
            if not dir:
                print("no files", ncheck, maxcheck)
                continue                # no files

            # get recent ones
            rdir = [ d for d in dir if d.st_mtime >= (now-maxage)]
            if not rdir:
                print("no recent files", ncheck, maxcheck)
                continue

            # sort chronologically
            rdir.sort(key=lambda x: x.st_mtime)
            for fn in rdir:
                if fn.filename in seen:
                    continue            # already looked at it
                # slurp in message, drop line endings
                with sftp.open(fn.filename, "rb") as f:
                    fl = [l.decode(encoding="utf-8", errors="replace") for l in f]
                seen.add(fn.filename)

                if subject:
                    m = tuple(l for l in fl if l.lower().startswith('subject') )
                    if m:
                        msub = m[0].split(maxsplit=1)[1]
                        if subject.lower() not in msub: # not it
                            print("not it",fn.filename, msub, ncheck, maxcheck)
                            continue
                    else:
                        print("no subject",fn.filename, ncheck, maxcheck)
                        continue

                # found one
                sshcl.close()
                return fl
            # didn't like any of these, loop and try again
            
        print("timeout")
        sshcl.close()
        return None

    def parsemsg(self, msg):
        """
        parse message headers
        return (dict of hdrs, list of hdrs, list of body)
        """
        mout = []
        while msg:
            l = msg.pop(0).rstrip('\r\n') # peel off a line at a time
            if l == "":
                break                   # end of header
            if l[0] in " \t":           # unfold folded lines
                mout[-1] += l
            else:
                mout.append(l)
        # now make table of headers
        hdrs = {}
        for l in mout:
            h, c = re.split(r':\s*', l, maxsplit=1)
            n = h.lower()
            if n in hdrs:
                hdrs[n].append(c)
            else:
                hdrs[n] = [ c ]
        return (hdrs, mout, msg)
                
    def genseq(self, tfile):
        """
        generate msgseq token for tfile
        """
        return hashlib.sha1((tfile+self.subjseq).encode()).hexdigest()[:20]

    def genmsg(self, tfile, **kwds):
        """
        generate a message from a template file tfile.msg
        filled in from config
        """
        # read in template. discard comment lines
        tl = []
        now = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
        with open(tfile+".msg", "r") as f:
            for l in f:
                if l[:1] == '#':
                    continue
                            
                t = string.Template(l)
                tl.append(t.substitute(self.pconfig, date=now, **kwds))
        return tl

    def subconnect(self, login=False, smtps=False, starttls=False, port=587, reuse=True):
        """
        connect to submission server if not already connected, login if requestd
        port is non-submits port
        """
        if self.debug:
            print("subconnect", login, smtps, starttls, reuse)
        if self.ssock and ( self.ssl != smtps or not reuse): # switch between SSL and submits if need be
            try:
                self.ssock.quit()
            except smtplib.SMTPServerDisconnected:
                pass                    # who cares
            self.ssock = None
            time.sleep(5)              # pause to let things close?

        if not self.ssock:
            try:
                if smtps:
                    self.ssock = USMTP_SSL(self.sserver, port=465, local_hostname="eaitest.local")
                    self.ssl = True
                else:
                    self.ssock = USMTP(self.sserver, port=port, local_hostname="eaitest.local")
                    self.ssl = False
                    self.starttls = False
            except (ConnectionRefusedError, smtplib.SMTPException) as err:
                print(f"Cannot connect to {self.sserver} {err}")
                return None

            self.ssock.command_encoding = 'utf-8' # hack
            self.login = False
            code, msg = self.ssock.ehlo('eaitest.local')
            if code != 250:
                print("EHLO failed")
                return None

        if not smtps and starttls and not self.starttls:
            try:
                self.ssock.starttls()
                self.ssock.ehlo()        # do another EHLO after the starttls
                self.starttls = True
            except smtplib.SMTPException as err:
                print("STARTTLS failed", err)
                return None

        if login and not self.login:
            self.ssock.set_debuglevel(10)
            try:
                self.ssock.login(self.user, self.passwd)
            except smtplib.SMTPException as err:
                print("Login failed", err)
                return None
            self.login = True
            print("logged in as", self.user)
            self.ssock.set_debuglevel(0)
        return True

    def submit(self, msg, From=None, To=None, eaiflag=True, port=None):
        """
        submit a message via the submission server
        """

        if type(msg) != str:            # if it's a list of lines
            msg = "".join(msg)
        bmsg = msg.replace('\n','\r\n').encode('utf8')
        sc = self.subconnect(smtps=self.submits, starttls=True, login=True, port=port, reuse=False)
        if not sc:
            return False
        print("after subconnect",sc)
        try:
            if eaiflag and not self.pconfig.getboolean('nosubeai', fallback=False):
                r = self.ssock.sendmail(From, To, bmsg, mail_options=('SMTPUTF8',))
            else:
                r = self.ssock.sendmail(From, To, bmsg)
        except smtplib.SMTPException as err:
            self.submiterror = err
            return False
        return True

    def getimap(self, prefix='', folder=None, maxage=60, sltime=5,
        subject=None, maxcheck=5):
        """
        get a recently sent message via IMAP from a target, where target is
        per product and prefix is name prefix in the config

        wait until there is a message no older than maxage
        or look for one with subject
        up to maxcheck times, sltime pause between tries
        """

        thost = self.pconfig.get(prefix+'imaphost')
        tport = self.pconfig.getint(prefix+'imapport', fallback=993)
        tuser = self.pconfig.get(prefix+'imapuser')
        tpwd = self.pconfig.get(prefix+'imappw')

        # HACK don't verify ssl cert because Coremail's
        sslcx = ssl.create_default_context()
        if not self.pconfig.getboolean('checkssl', fallback=True):
            print("turn off ssl check")
            sslcx.check_hostname = False
            sslcx.verify_mode = ssl.CERT_NONE
        sslcx.load_default_certs()

        try:
            print("try imap",thost,tport, tuser)
            i = imapclient.IMAPClient(thost, port=tport, ssl_context=sslcx)
        except Exception as err:
            print("no IMAP", err)
            return None

        self.imap = i
        i.folder_encode = False         # don't use UTF7
        i._imap._mode_utf8()            # HACK allow UTF-8 login

        if b'AUTH=PLAIN' in i.capabilities():
            print("try auth")
            try:
                r = i.plain_login(tuser, tpwd)
            except imapclient.IMAPClient.Error as err:
                print("auth failed", err)
                return None
        else:
            try:
                r = i.login(tuser, tpwd)
            except imapclient.IMAPClient.Error as err:
                print("login failed", err)
                return None

        ncheck = 0

        while ncheck < maxcheck:
            # also check junk folder if it exists
            junkf = self.pconfig.get(prefix+'junkfolder')
            if junkf:
                folders = ('INBOX', junkf)
            else:
                folders = ('INBOX',)
            for folder in folders:
                print("select", folder)
                r = i.select_folder(folder.encode())
                print("select", folder, r)
                if subject:
                    r = i.search(['HEADER', 'subject', subject])
                else:
                    r = i.search([u'SINCE', datetime.datetime.now()-datetime.timedelta(minutes=maxage)])
                #print("search", r)
                if r:
                    mm = i.fetch(r[-1], ['RFC822']) # get the last one
                    md = mm[r[-1]]
                    mt = md[b'RFC822'].replace(b'\r',b'') # message text
                    fl = [l.decode(encoding="utf-8", errors="replace") for l in mt.split(b'\n')]
                    return fl

            if ncheck:
                time.sleep(sltime)           # don't hammer too fast
            print("noop", i.noop())       #   should look at the result here
            ncheck += 1
        return None
        
    def getmori(self, prefix='', folder=None, maxage=60, sltime=5, subject=None, maxcheck=5):
        """
        get local message via ssh or imap
        depending on localstore setting
        """
        mori = self.pconfig.get('localstore')
        if mori == 'imap':
            return self.getimap(prefix=prefix, folder=folder, maxage=maxage, sltime=sltime, subject=subject, maxcheck=maxcheck)
        elif mori == 'ssh':
            assert not folder
            return self.getmsg(prefix=prefix, maxage=maxage, sltime=sltime, subject=subject, maxcheck=maxcheck)
        else:
            print("localstore undefined, giving up")
            exit(1)

    # submit and retrieve a message
    def domsg(self, tfile, From=None, To=None, eaiflag=True, subject=None,
        sendmail=False, submit=True, getrmt=False, maxcheck=None, **kwds):
        """
        submit tfile with From/To and retrieve from test server
        submit flag says use submmission server, otherwise SSH and sendmail?
        getrmt is get by SSH from my remote server rather than test server
        subject is string to look for in message subject
        save and reuse
        other kwds expand macros in tfile template
        """
        t = (tfile, From, To, eaiflag)
        if t in self.messages:
            return self.messages[t]
        msgseq = self.genseq(tfile)
        msg = self.genmsg(tfile, From=From, To=To, msgseq=msgseq, **kwds)
        if maxcheck is None:
            maxcheck = self.msgtime*4

        if sendmail:
            # send via local sendmail
            r = self.sendmail(msg, From=From, To=To)
        elif submit:
            # submit to this server by SUBMIT or sendmail
            r = self.sendmsg(msg, From=From, To=To, eaiflag=eaiflag)
        else:
            # csend is in mtatestgroup, for MTA tests only
            r = self.csend(msg, From=From, To=To, eaiflag=eaiflag)
        if not r:
            print(f"cannot send message {From} -> {To}")
            return None
        print("sent msg", r, From, To)
        if not subject:
            subject = msgseq            # look for the token
        if getrmt:
            res = self.getmsg(prefix='srv', subject=subject, maxcheck=maxcheck) # checks every 15 secs
        else:
            res = self.getmori(subject=subject, maxcheck=maxcheck) # checks every 15 secs
        if not res:
            print("cannot find", subject)
            self.messages[t] = None     # remember it didn't work
            return None
        pres = self.parsemsg(res)
        self.messages[t] = pres
        return pres

    def sendmail(self, msg, From=None, To=None):
        """
        send a message through local mail system (must support EAI) using sendmail
        """
        smpgm = self.pconfig.get('sendmail')

        if type(msg) != str:            # if it's a list of lines
            msg = "".join(msg)
        args = [smpgm]
        if From:
            args.append(f"-f{From}")
        if To:
            args.append(To)
        else:
            args.append('-t')

        r = subprocess.run(args, input=msg, encoding='utf8')
        if r.returncode == 0:
            return True
        raise TestError("sendmail failed", r)

    def sendmsg(self, msg, From=None, To=None, eaiflag=True):
        """
        send a message however this MTA does it
        """
        how = self.pconfig.get('testsend')
        if how == 'local':
            return self.lclsubmit(msg, From=From, To=To)
        elif how == 'submit':
            return self.submit(msg, From=From, To=To, eaiflag=eaiflag)
        else:
            raise TestError("Mystery send rule",how)

    def lclsubmit(self, msg, From=None, To=None):
        """
        submit locally using SSH and sendmail
        """
        thost = self.pconfig.get('sendhost')
        tport = self.pconfig.getint('sendport', fallback=22)
        tuser = self.pconfig.get('senduser')
        tdir = self.pconfig.get('senddir')

        sshcl = paramiko.client.SSHClient()
        sshcl.load_system_host_keys()
        sshcl.connect(thost, username=tuser, port=tport)

        if type(msg) != str:            # if it's a list of lines
            msg = "".join(msg)

        stdin, stdout, stderr = sshcl.exec_command(f"sendmail -f{From} {To}; echo $?")
        stdin.write(msg.encode('utf8'))
        stdin.close()
        l = stdout.readline().strip()
        return l


    def iseai(self, s):
        """
        see if str or bytes are eai
        """
        if type(s) is str:
            return any(ord(x) > 127 for x in s)
        if type(s) is bytes:
            return any(x > 127 for x in s)
        raise TestError(f"mystery string {repr(s)}")

    def cconnect(self, starttls=False):
        """
        connect to MTA as client if not already connected
        """
        print("client connect", starttls)
        if self.csock and self.cstarttls and not starttls:
            try:
                self.csock.quit()           # start over
            except smtplib.SMTPServerDisconnected:
                pass                    # who cares
            self.csock = None

        if not self.csock:
            try:
                self.csock = USMTP(self.mailserver, port=25, local_hostname="eaitest.local")
                self.cstarttls = False
            except smtplib.SMTPException:
                print(f"Cannot connect to {self.cserver}")
                return None

            code, msg = self.csock.ehlo('eaitest.local')
            if code != 250:
                print("EHLO failed")
                return None

        if starttls and not self.cstarttls:
            try:
                self.csock.starttls()
                self.csock.ehlo()        # do another EHLO after the starttls
                self.cstarttls = True
            except smtplib.SMTPException as err:
                print("STARTTLS failed", err)
                return None
        return True

################# main stub for debugging
if __name__=="__main__":
    import argparse

    parser = argparse.ArgumentParser(description='EAI test client')
    parser.add_argument('-d', action='store_true', help="Use debug server")
    parser.add_argument("-p", help="Product name")
    parser.add_argument("-s", help="subject tag")
    parser.add_argument("tests", nargs='*', help="optional list of tests")
    
    args = parser.parse_args()

    if not args.p:
        raise TestError("Need product name")

    t = Testgroup('MTA', args.p, debug=args.d)
    for test in args.tests:
        if test == 'i':
            r = t.getimap(prefix='test', maxcheck=2, subject=args.s)
            if r:
                print(t.parsemsg(r))
            else:
                print(r)
        else:
            print("???", test)
