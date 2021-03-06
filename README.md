# Eaitesttools
Tools for testing EAI compliance of mail software

These are the software we used to for tests of EAI conformance. There
is a web application to track and report test results, some scripts to
do MSA, MTA, and MDA tests, and two scripts to extract results into
Excel XLSX files or store them into Google Sheets spreadsheets.

They are provided with no support and no promise they will work in
other environments. Many of the tests involve sending a test message
and then looking at it after it is received. Since test environments
don't always provide a reliable way to send or receive EAI messages, some tests use ssh
to a remote server to submit or retrieve messages, or call sendmail on
the local host to send messages.

The scripts were run under python 3.8 and 3.9. The database was MySQL
5.7. The web application was run under mod_wsgi in Apache 2.4 but
should work on any WSGI server.

John Levine, Standcore LLC, October 2020

## Test tool server

These need the python modules bottle, beaker, pymysql

eaitest.sql:
Creates database tables

eaitest.py:
Main web app module

eaidb.py:
Database module for web app

views, static:
templates and static files

## Test scripts

These need python modules requests, paramiko, imapclient

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

config.txt:
Target configuration parameters that tests use.

## Reports

wrtitess.py:
Write results in XLSX spreadsheets.  Needs python module xlsxwriter.

writegs.py:
Write results in Google sheets.  Needs python modules for the Google
API.

## Miscellaneous

ldtest.py:
Load test descriptions from CSV files

ldproducts.py:
Load products to test from CSV file

