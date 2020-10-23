#!/usr/local/bin/python3
#
# EAI feature tests

from bottle import request, route, get, post, run, hook, app, template, view, \
    static_file, redirect, HTTPResponse, BaseRequest
from beaker.middleware import SessionMiddleware
from eaidb import EAIdb
import re, sys
import base64

debug = False

# allow large zones
BaseRequest.MEMFILE_MAX = 1024*1024

# to keep out random snoopers
apikeys = {
    "xxxxx": 'bob',
    "yyyyyyy": 'mary',
    }

session_opts = {
    'session.key': 'eaitest',
    'session.type': 'file',
    'session.data_dir': '/tmp/session',
    'session.lock_dir': '/tmp/sessionlock',
    'session.cookie_expires' : 86400,
    'session.secret': "swordfish",
    'session.auto': True
}

# my cookie directory, for debugging
if __name__=="__main__":
    if len(sys.argv) >= 2 and sys.argv[1].startswith("debug"):
        session_opts['session.data_dir'] ='/tmp/mysession'
        session_opts['session.lock_dir'] ='/tmp/mysessionlock'
        debug = True
        print("Debugging on")

myapp = SessionMiddleware(app(), session_opts)

# print something in red
def inred(msg):
    if msg:
        return '<font color="red">{0}</font>'.format(msg)
    return msg    

@hook('before_request')
def setup_request():
    request.session = request.environ['beaker.session']
    if 'user' not in request.session and request.path not in ('/api', '/login') and not request.path.startswith('/static'):
        return redirect("/login")
#    print "path is",request.path    
    
def boilerplate():
    """
    boilerplate toolbar at the top of each page
    """
    here = request.path
    def bp(page, desc):
        if here == page:
            return "<li><a href=\"{}\" class=active>{}</a></li>\n".format(page,desc)
        else:
            return "<li><a href=\"{}\">{}</a></li>\n".format(page,desc)

    bo = "<ul id=tabnav>\n"
    bo += bp("/packages","Packages")
    bo += bp("/tasks","Tasks")
    bo += bp("/tests","Tests")
    bo += bp("/summary","Summary")
    bo += bp("/help","Help")
    bo += bp("/logout", "Logout")
    bo += "</ul>\n<p align=right>Logged in as " + request.session['user']
    bo += "</p>"
    return bo

@view('failpage')
def failpage(why):
    """ return a failure page
    """
    return dict(boilerplate=boilerplate(),
        kvetch=why)

@view('statuspage')
def statuspage(why):
    """ return a status page
    """
    return dict(boilerplate=boilerplate(),
        kvetch=why)

#################### Session management ###########################
@get('/')
@get('/login')
@view('login')
def login():
    return dict(name="EAI Tests")

@post('/login')
@view('login')
def loginp():
    db = EAIdb(request.forms.user,debug=debug)
    cqr = db.userlogin(pw=request.forms.pw)

    if cqr:
        request.session['user'] = cqr['user']
        request.session['ttid'] = cqr['ttid']
        return redirect('/packages')

    if 'user' in request.session:
        del request.session['user']
    return dict(name="EAI tests", kvetch='User or password not recognized')

@get('/logout')
def logout():
    """ log out and return to login page """
    
    del request.session['user']
    return redirect('/login')
    
@get('/packages')
@view('packages')
def packages():
    db = EAIdb(request.session['user'],debug=debug)
    
    prods = db.getproducts()
    if not prods:
        return failpage("No packages")

    return dict(name="Packages to be tested", boilerplate=boilerplate(), prods=prods)
    
@get('/package/<pid:int>')
@view('package')
def package(pid):
    db = EAIdb(request.session['user'],debug=debug)

    prod = db.getproduct(pid=pid)
    return dict(name=f"Package info for {prod['name']}", prod=prod,
        boilerplate=boilerplate())


############################## Tests #############################
testtype = ('MUA','MSA','MTA','MDA','MSP','Web')

def typeselect(name="ttype"):
    sel = f'<select name="{name}">\n' + \
        "".join((f"<option>{t}</option>\n" for t in testtype)) + \
        "</select>\n"
    return sel

taskstate = ('assigned','working','done')

def stateselect(name="tstate", defstate=None):
    sel = f'<select name="{name}">\n' + \
        "".join(("<option {1}>{0}</option>\n".format(t, "selected" if t==defstate else "")
            for t in taskstate)) + \
        "</select>\n"
    return sel

@get('/tests')
@view('tests')
def tests0():
    return(tests(testtype[0]))          # default

@get('/tests/<ttype>')
@view('tests')
def tests(ttype):
    db = EAIdb(request.session['user'],debug=debug)
    
    tests = db.gettests(ttype)

    return dict(name="Tests for "+ttype, ttype=ttype, tests=tests,
        testtype=testtype, boilerplate=boilerplate())
    
@get('/test/<tid:int>')
@view('test')
def test(tid):
    """
    show one test
    """

    db = EAIdb(request.session['user'],debug=debug)
    
    test = db.gettest(tid=tid)

    if not test:
        return failpage("No such test")

    return dict(name="Test description for "+test['testid'], test=test, tid=tid, boilerplate=boilerplate())

################ Tasks ################
@get('/tasks/<sortkey>')
@view('tasks')
def taskssort(kvetch=None , sortkey=None):
    if sortkey in ('user', 'product','testtype','state'):
        return tasks(sortkey=sortkey)
    return tasks(kvetch=f"Mystery sortkey {sortkey}")
    

@get('/tasks')
@view('tasks')
def tasks(kvetch=None , sortkey=None):
    db = EAIdb(request.session['user'],debug=debug)
    
    tasks = db.gettasks(stats=True)

    if sortkey:
        tasks.sort(key=lambda x: x[sortkey])

    return dict(name="Assigned Tasks", boilerplate=boilerplate(),
        tasks=tasks, kvetch=kvetch)

@get('/finish/<ttid:int>/<pid:int>/<ttype>/<state>')
def chgtask(ttid, pid, ttype, state):
    """
    mark task as done or something
    """

    db = EAIdb(request.session['user'],debug=debug)

    product = db.getproduct(pid=pid)

    ldone = db.getresults(ttid, pid, ttype, done=True)
    ndone = db.getresults(ttid, pid, ttype, done=False)
    args = {'ttid': ttid,
        'pid': pid,
        'testtype': ttype,
        'state': state
        }
    r = db.addtask(args, update=True)
    if not r[0]:
        if debug:
            print("failed",r)
        return tasks(kvetch=r[1])              # error message
    return tasks()

@get('/newtask')
@view('newtask')
def newtask():
    db = EAIdb(request.session['user'],debug=debug)
    
    return dict(name="Add a new task",
        typeselect=typeselect(),
        testerselect=db.testerselect(),
        productselect=db.productselect(),
        stateselect=stateselect(),
        boilerplate=boilerplate())

@post('/newtask')
def pnewtask():
    db = EAIdb(request.session['user'],debug=debug)
    
    args = {'ttid': request.forms.tester,
        'pid': request.forms.product,
        'testtype': request.forms.ttype,
        'state': request.forms.tstate
        }
    r = db.addtask(args)
    if not r[0]:
        if debug:
            print("failed",r)
        return tasks(kvetch=r[1])              # error message
    return tasks()

@get('/task/<ttid:int>/<pid:int>/<ttype>')
@view('task')
def task(ttid, pid, ttype):
    """
    show pending and completed tests in a task
    """

    db = EAIdb(request.session['user'],debug=debug)

    product = db.getproduct(pid=pid)

    ldone = db.getresults(ttid, pid, ttype, done=True)
    ndone = db.getresults(ttid, pid, ttype, done=False)

    return dict(boilerplate=boilerplate(), name="Tests in this Task", ttid=ttid, pid=pid, ttype=ttype,
        ldone=ldone, ndone=ndone, product=product)

@get('/result/<ttid:int>/<pid:int>/<tid:int>')
@view('result')
def result(ttid, pid, tid, kvetch=None, comments=None):
    """
    show or update a result for a specific test
    """
    db = EAIdb(request.session['user'],debug=debug)

    res = db.getoneresult(tid, pid, ttid)
    hashval = db.dhash(res)
    test = db.gettest(tid=tid)
    product = db.getproduct(pid=pid)
    if res and res['picture']:
        picurl = pictourl(res['picture'])
    else:
        picurl = None
    if comments:
        res['comments'] = comments      # keep value from failed update
        
    return dict(boilerplate=boilerplate(), name="Test Result", ttid=ttid, pid=pid, tid=tid,
        res=res, test=test, product=product, picurl=picurl, kvetch=kvetch, hashval=hashval)

def pictourl(pic):
    """
    turn bytes into data URL
    """
    if pic.startswith(b'\x89\x50\x4e\x47\r\n\x1a\n'): # PNG signature
        return b"data:image/png;base64," + base64.b64encode(pic)
    if pic.startswith(b'\xff\xd8'):
        return b"data:image/jpeg;base64," + base64.b64encode(pic)
    return b"data:,Unknown%20file%20format"


@post('/result/<ttid:int>/<pid:int>/<tid:int>')
@view('result')
def postresult(ttid, pid, tid):
    """
    add or update a test result
    """
    db = EAIdb(request.session['user'],debug=debug)
    status = request.forms.s
    comments = request.forms.c
    picture = request.files.get('pic')
    oldhv = request.forms.hv

    if not status:
        return result(ttid, pid, tid, kvetch="Status not set")

    test = db.gettest(tid=tid)
    if request.forms.rr:
        return task(ttid, pid, test['testtype'])
    if request.forms.nn:
        return result(ttid, pid, tid+1)
        
    if not status:
        return result(ttid, pid, tid, kvetch="Status not set", comments=comments)
        
    res = db.getoneresult(tid, pid, ttid)
    hashval = db.dhash(res)
    if hashval != oldhv:
        return result(ttid, pid, tid, kvetch="Database changed", comments=comments)

    if picture:
        l = picture.content_length
        pictext = picture.file.read(l)
    else:
        pictext = None

    r, m = db.addresult(tid, ttid, pid, status, comments, pictext)
    if debug:
        print("did addresult",request.forms.u, request.forms.ur, request.forms.un)
    # return to this page
    if (not r) or request.forms.u:
        return result(ttid, pid, tid, kvetch=m)

    if request.forms.un:    # next test
        if debug:
            print("result",ttid,pid,tid+1)
        return result(ttid, pid, tid+1)

    # return to test page
    return task(ttid, pid, test['testtype'])

@get('/summary/<ttype>')
@view('summary')
def tsummary(ttype):
    return summary(ttype=ttype)

@get('/summary')
@view('summary')
def summary(ttype='MUA', ttid=None):
    """
    summary table of tests and products
    """
    db = EAIdb(request.session['user'],debug=debug)
    if not ttid:
        ttid=request.session['ttid']
    
    s = db.getsummary(ttid, testtype=ttype)
    if not s:
        return template('nosummary', boilerplate=boilerplate(), name="Test Summary",
            ttype=ttype, ttid=ttid, testtype=testtype, testerselect=db.testerselect(addall=True))

    return dict(boilerplate=boilerplate(), name="Test Summary", products=s[0],
        tests=s[1], results=s[2], ttype=ttype, ttid=ttid, testtype=testtype,
            testerselect=db.testerselect(addall=True))
    
@post('/summary')
@view('summary')
def postsummary():
    """
    change who or what on summary page
    """

    ttid = request.forms.tester
    ttype = request.forms.ttype
    return summary(ttype=ttype, ttid=ttid)


################################################################
# programmatic API

@post('/api')
def api():
    """
    API for 
    json blob of
     apikey: secret key
     request: getresult, setresult, getresults, gettasks

     getresults; product, testtype, optional Done. optional tester
     getresult: product, testid or tid
     setresult: product, testid or tid, status, optional comments
     tasks: product, testtype

    response blob of
     request: whatever
     answer: yes
     
    """

    j = request.json
#    print("request", j)
    k = j.get('apikey','x')
    if k not in apikeys or 'request' not in j:
        raise HTTPResponse(status=403)

    db = EAIdb(apikeys[k],debug=debug)        # fake login as user for api key

    req = j['request']
    r = { 'request': req, "answer": "yes" }

    # get tester ID
    if 'ttid' in j:
        ttid = j['ttid']
    else:
        user = db.getuser()
        ttid = user['ttid']

    # get product
    if req == 'products':
        res = db.getproducts()
        r['result'] = res
        return r

    if 'product' not in j:
        raise HTTPResponse(status=403)
    product = db.getproduct(name=j['product'])
    if not product:
        raise HTTPResponse(status=403)
    pid = product['pid']

    if req == 'getresults':
        if 'testtype' not in j:
            raise HTTPResponse(status=403)
        if debug:
            print("getresults", ttid, pid, j['testtype'], j.get('done', False)) # check for arguments
        res = db.getresults(ttid, pid, j['testtype'], j.get('done', False)) # check for arguments
        r['result'] = res
        return r

    elif req in ('getresult', 'setresult'):
        if 'tid' in j:
            tid = j['tid']
        elif 'testid' in j:
            tt = db.gettest(testid=j['testid'])
            if tt:
                tid = tt['tid']
            else:
                raise HTTPResponse(status=403) # unknown test
        else:
            raise HTTPResponse(status=403) # need tid or testid
        if req == 'getresult':
            res = db.getoneresult(tid, pid)
            r['result'] = res
        else:   # setresult
            if 'status' not in j:
                raise HTTPResponse(status=403) # need status
            res = db.addresult(tid, ttid, pid, j['status'], comments=j.get('comments', None))
            r['result'] = res
        return r

    elif req == 'tasks':
        testtype = j.get('testtype')    # default OK
            
        res = db.gettasks(testtype=testtype, pid=pid, stats=True)
        r['result'] = res
        return r

    else:
        raise HTTPResponse(status=403) # unknown request


############################################################
# try to be helpful

@get('/help')
@view('help')
def help():
    """ be helpful
    """
    return dict(boilerplate=boilerplate(), name="Help")

################################################################
# for CSS and images
@route('/static/<filename:path>')
def send_static(filename):
    return static_file(filename, root='./static')

@route('/favicon.ico')
def favicon():
    return static_file('favicon.ico', root='./static')

@route('/robots.txt')
def robots():
    return static_file('robots.txt', root='./static')

################# main stub for debugging
if __name__=="__main__":
    import sys

    if len(sys.argv) >= 2 and sys.argv[1] == "debug":
        run(app=myapp, host='localhost', port=8802, debug=True, reloader=True)
    else:
        run(app=myapp, server="cgi", debug=True)
