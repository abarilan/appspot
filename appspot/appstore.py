#!/usr/bin/env python





AppGetHTMLTemplate = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"><head>
<title>%(title)s - iOS App Download</title>
<script type="text/javascript" src="%(qr_url)s/qrcode.js"></script> 
<script type="text/javascript" src="%(qr_url)s/sample.js"></script>
<script type="text/javascript">
    function copyWarning() {
        var inner = document.getElementById("warn-1").innerHTML;
        document.getElementById("warn-2").innerHTML = inner;
    }
</script>
</head>
<body onload="update_qrcode(location.href); copyWarning()" style="font: 12pt sans-serif;">
<div id="warn-1">
<table bgcolor="#ff6" border="1" cellspacing="0" cellpadding="20"><tr><td>
<big><i><b>WARNING</b>: in accordance with Apple's Internal Use Application agreement, this software must only be used by %(company)s employees. In addition, %(company)s customers can use it on %(company)s physical premises or under the <b>direct supervision</b> and <b>physical control</b> of %(company)s employees.</i>
<br><b><i>Do not forward the link to this application to unauthorized personnel.</i></b></big>
</td></tr></table>
</div>
<h1>%(title)s</h1>
<img src="%(url)s/icon.png"/><br/>
<h2><a href="itms-services://?action=download-manifest&amp;url=%(ssl_url)s/manifest.plist">Install</a> <small>(use directly from iPad/iPhone)</small></h2>
<h2><a href="%(url)s/app.ipa">Download</a> <small>(for installation through iTunes)</small></h2>

<div id="qr_code"></div>

<pre >
Timestamp:              %(time)s
Version:                %(version)s
Build Info:             %(build_info)s
Bundle name:            %(bundle_name)s
Bundle ID:              %(bundle_id)s
Size:                   %(size_kb)d kb
Minimum OS Version:     %(MinimumOSVersion)s
</pre>

<br/>

View <a href="%(url)s/notes.txt">notes</a> | <a href="%(url)s/manifest.plist">manifest</a> | <a href="%(url)s/profile.plist">provisioning profile</a> | <a href="%(url)s/devices.plist">provisioned devices</a>
<p></p>
<div id="warn-2">
</div>

</body></html>
"""

AppGetHTMLTemplateAPK = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"><head>
<title>%(appName)s - Android App Download</title>
<script type="text/javascript" src="%(qr_url)s/qrcode.js"></script> 
<script type="text/javascript" src="%(qr_url)s/sample.js"></script>
</head>
<body onload="update_qrcode(location.href)">
<h1>%(appName)s</h1>
<img src="%(url)s/icon.png"/><br/>
<h2><a href="%(url)s/app.apk">Download / Install</a></h2>
<div id="qr_code"></div>
<br/>
<pre>
Timestamp:      %(time)s
Version:        %(versionName)s
Package name:   %(packageName)s
Size:           %(size_kb)s
</pre>
</body></html>
"""

import apptoken
from storelib import HOME, extract_info, prepare_manifest, FILES_ABS, get_file, readfile, get_file_content, extract_info_apk
import storelib 

import os
import sys
import errno
import commands
import re
import httplib
import shutil
import glob
from tempfile import mkstemp, mkdtemp
from datetime import datetime
from zipfile import ZipFile
from xml.sax.saxutils import escape
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import web

import plistlib


# logfile = open(os.path.join(HOME, "log", "download.log"), "a")
# def log(msg):
#     logfile.write("[%s] %s %s\n" % (web.ctx.ip, datetime.utcnow().isoformat(),msg))

# import logging
# logging.basicConfig(format='%(message)s', filename=os.path.join(HOME, "log", "download.log"), level=logging.INFO)
# logging.info('Started')
# def log(msg):
#     logging.info("[%s] %s %s" % (web.ctx.ip, datetime.utcnow().isoformat(), msg))

from log import log

app = web.auto_application()

company_map = None

## Helpers <<

def get_url(token, path, *more):
    return os.path.join(web.ctx.realhome, token, path, *more)


def check_token(token, path):
    log("SERVE:CHECK_TOKEN: " + path)
    if not storelib.check_token(token, path):
        raise web.notfound("App not found")
    path = os.path.join(FILES_ABS, path)
    if not path.startswith(FILES_ABS):
        raise web.notfound("App not found")


def serve_app_bundle(path):
    
    log("SERVE:BUNDLE:START: " + path)
    file = get_file(path, "*.ipa")
    if not file:
        file = get_file(path, "*.apk")

    length = os.path.getsize(file)
    filename = get_file_content(path, "filename")
    
    web.header('Content-Type', 'application/octet-stream')
    web.header("Content-Length", length)
    web.header("Content-Disposition", "attachment; filename=" + filename)
    
    f = open(file, "rb")
    while True:
        d = f.read(1024000)
        if not d:
            break
        yield d
    f.close()

    log("SERVE:BUNDLE:DONE: " + path)



def get_file_or_none(path, name, content_type):

    p = get_file_content(path, name)
    if p:
        web.header('Content-Type', content_type)
        web.header("Content-Length", len(p))
        return p
    else:
        print path, name, "not found"
        web.header('Content-Type', 'text/plain')

## << Helpers



## iOS >>
class AppProvisionedDevices(app.page):
    path = "/([\w-]+)/(.+)/devices.plist"
    def GET(self, token, path):

        check_token(token, path)
        return get_file_or_none(path, "ProvisionedDevices.plist", 'text/xml')
        
class AppProvision(app.page):
    path = "/([\w-]+)/(.+)/profile.plist"
    def GET(self, token, path):

        check_token(token, path)
        return get_file_or_none(path, "Provision.plist", 'text/xml')

class AppManifest(app.page):
    path = "/([\w-]+)/(.+)/manifest.plist"
    def GET(self, token, path):
        check_token(token, path)
        
        web.header('Content-Type', 'text/xml')
        log("SERVE:BUNDLE:PREPARE_MANIFEST " + path)
        return prepare_manifest(extract_info(path), get_url(token, path))

class AppIPA(app.page):
    path = "/([\w-]+)/(.+)/app.ipa"
    def GET(self, token, path):
        check_token(token, path)
        check_auth(path)
        
        return serve_app_bundle(path)

    def HEAD(self, token, path):
        check_token(token, path)
        ipa = get_file(path, "*.ipa")
        length = os.path.getsize(ipa)
        web.header('Content-Type', 'application/octet-stream')
        web.header("Content-Length", length)
        return None

## << iOS


## Android >>
class AppAPK(app.page):
    path = "/([\w-]+)/(.+)/app.apk"
    def GET(self, token, path):
        check_token(token, path)

        return serve_app_bundle(path)

## << Android


## Common >>

class Static(app.page):
    path = "/static/(.+)?"
    def GET(self, path):
        if path[0] in ('.', '/'):
            return None
        ext = os.path.splitext(path)[1]
        types = {'.png':'image/png', '.gif':'image/gif','.css':'text/css','.js':'application/javascript'}
        type = types.get(ext, 'text/plain')
        web.header('Content-Type', type)
        return readfile('/'.join((HOME, 'static', path)))

class AppIcon(app.page):
    path = "/([\w-]+)/(.+)/icon.png"
    def GET(self, token, path):
        check_token(token, path)

        return get_file_or_none(path, "*.png", 'image/png')

class AppNotes(app.page):
    path = "/([\w-]+)/(.+)/notes.txt"
    def GET(self, token, path):
        check_token(token, path)

        return get_file_or_none(path, "notes.txt", 'text/plain')

# Must appear last!

def pretty_size(filename):
    a = str(os.path.getsize(filename)/1024)
    b = []
    len_a = len(a)
    for i in xrange(len_a):
        if i > 0 and (len_a-i) % 3 == 0:
            b.append(',')
        b.append(a[i])
    return ''.join(b)

def map_bundle_id_to_company(bundle_id):
    global company_map
    if not company_map:
        company_map = json.load(open(os.path.join(HOME, "inhouse-map.json")))
    for k, v in company_map.iteritems():
        if bundle_id.startswith(k):
            return v
    return "<Unknown>"

class AppGet(app.page):
    path = '/([\w-]+)/(.+)'
    def GET(self, token, path):

        check_token(token, path)
        web.header('Content-Type', 'text/html')
        
        ipa = get_file(path, "*.ipa")
        apk = get_file(path, "*.apk")
        
        if ipa:
            log("SERVE:PAGE:IPA: " + path)
            
            info = extract_info(path)
            bundle_id = info['CFBundleIdentifier']
            log("SERVE:PAGE:IPA:BUNDLE_ID " + bundle_id)

            app_url = get_url(token, path)
            log("SERVE:PAGE:IPA:URL " + app_url)

            try:
                app_page = AppGetHTMLTemplate % dict(
                    url = app_url, 
                    ssl_url = app_url.replace("http://", "https://"),
                    title = escape(info.get('CFBundleDisplayName', info["CFBundleName"])), 
                    bundle_id=escape(bundle_id), 
                    time = datetime.fromtimestamp(os.path.getctime(ipa)).isoformat(), 
                    version=escape(info['CFBundleVersion']), 
                    build_info=escape(info.get('TvcBuildInfo','<none>')), 
                    bundle_name=escape(info["CFBundleName"]),
                    company = escape(map_bundle_id_to_company(bundle_id)),
                    size_kb=os.path.getsize(ipa)/1024,
                    MinimumOSVersion=info.get("MinimumOSVersion","<unknown>"),
                    qr_url=web.ctx.realhome + "/static/QR")
            except:
                log("SERVE:PAGE:IPA:FAIL ")
                raise
            return app_page  
        
        if apk:
            log("SERVE:PAGE:APK: " + path)
            info = extract_info_apk(path)

            filename = get_file_content(path, "filename")
            if not info.get("versionName"):
                info["versionName"] = "<none>"
            
            info['url'] = get_url(token, path)
            info['size_kb'] = pretty_size(apk) + "kb"
            info['time'] = datetime.fromtimestamp(os.path.getctime(apk)).isoformat()
            info['qr_url'] = web.ctx.realhome + "/static/QR"
            eInfo = {}
            for k, v in info.iteritems():
                eInfo[k] = escape(v)
            
            return AppGetHTMLTemplateAPK % eInfo

        return web.notfound()
## << Common


###############################################################################
# BASIC AUTH #############################################################
##############################################################################

def please_auth():
    web.header('WWW-Authenticate', 'Basic realm="Protected app"')
    raise web.Unauthorized("Protected app, please provide username and password")

def check_auth(path):
    auth_req = get_file_content(path, "auth")
    if not auth_req:
        return
    auth_req = auth_req.strip()
    
    auth = web.ctx.env.get('HTTP_AUTHORIZATION')
    if not auth:
        please_auth()
    
    # auth was provided, check
    username, password = [None,None]
    # get auth data from header
    auth = re.sub('^Basic ', '', auth)
    
    # for now, auth file just contains username:password
    auth_decoded = auth.strip().decode("base64")
    
    if auth_decoded != auth_req:
        please_auth()
    
if __name__.startswith("_mod_wsgi_"):
    print>>sys.stderr, "Running under mod_wsgi:", __name__
    print>>sys.stderr, "Python Version:", sys.version
    application = app.wsgifunc()

if __name__ == "__main__":
    sys.argv.append('8989')
    app.run()
