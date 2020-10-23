# eaitesttools
Tools for testing EAI compliance of mail software

These are the software I used to for tests of EAI conformance. There
is a web application to track and report test results, some scripts to
do MSA, MTA, and MDA tests, and two scripts to extract results into
Excel XLSX files or store them into Google Sheets spreadsheets.

They are provided with no support and no promise they will work in
other environments. Many of the tests involve sending a test message
and then looking at it after it is received. Since test environments
don't always provide an EAI-confirmant environment, some tests use ssh
to a remote server to submit or retrieve messages, or call sendmail on
the local host to send messages.

The scripts were run under python 3.8 and 3.9. The database was MySQL
5.7. The web application was run under mod_wsgi in Apache 2.4 but
should work on any WSGI server.

## Test tool server

Needs python modules bottle, beaker, pymysql

eaitest.sql:
Creates database tables
eaitest.py:
Main web app module
eaidb.py:
Database module for web app
views, static:

## Test scripts

Needs python modules requests, paramiko, imapclient

testgroup.py:
Base module for test
msatestgroup.py:
Do MSA tests
mtatestgroup.py:
Do MTA tests
mdatestgroup.py:
Do MDA tests
tclient.py:
Web API client to manage results in the web server database

## Reports

wrtitess.py:
Write results in XLSX spreadsheets.  Needs python module xlsxwriter.
writegs:py:
Write results in Google sheets.  Needs python modules for the Google
API.


