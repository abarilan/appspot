#!/usr/bin/env python

import apptoken
from storelib import HOME, FILES_ABS, mkdir_p, extract_info, readfile, writefile, get_file, extract_info_apk, gen_rand_token, check_token

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
from random import randint

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import web

import plistlib
from log import log

app = web.auto_application()


def safejoin(base, *pn):
	joined = []
	for p in pn:
		joined.append(p.strip("./"))
	return os.path.join(base, *joined)


class Browse(app.page):
	path = "/browse(/.+)?"
	def GET(self, root):
		#print root
		if not root:
			root = ''
		else:
			root = root[1:]
		
		dirs = []
		apps = []
		home = web.ctx.realhome
		web.header('Content-Type', 'text/html')
		for dir in os.listdir(safejoin(FILES_ABS, root)):
			if [f for f in os.listdir(safejoin(FILES_ABS, root, dir)) if f.endswith('.ipa') or f.endswith('.apk')]:
				path = os.path.join(root, dir)
				token = apptoken.gen_token(path).lower()
				apps.append( '<h2><!--%s--><i><a href="http://appspot.nds.com/public/a/%s/%s">%s</a></i></h2>' % (path, token, path, path))
			else:
				dirs.append( '<h2> + <a href="%s/browse/%s">%s</a></h2>' % (home, os.path.join(root, dir), dir))
		
		links = sorted(dirs) + ["<hr/>"] + sorted(apps)
		return '\n'.join(links)

class KeepApp(app.page):
    path = "/keepApp"
    def GET(self):
        web.header('Content-Type', 'text/html')
        return """<html><head></head><body><form method="POST">App URL: <input size="100" type="text" 
name="url"><input type="submit" value="Submit"></form></body></html>"""

    def POST(self):
        web.header('Content-Type', 'text/plain')
        form = web.input()
        url = form.get("url")
        match = re.match("http://appspot.nds.com/public/a/([^/]+)/(.+)", url)
        #print match.groups()
        token, path = match.groups()
        if not check_token(token, path):
            return "Invalid app URL: %s" % url

        keepfile = os.path.join(FILES_ABS, path, "KEEP")
        writefile(keepfile , "True")

        log("KEEP:APP: " + path)
        
        return """App "%s" \n(%s) \nwill be kept forever.""" % (path, url)
    

def value_or_none(dict, key):
	if dict is None:
		return '<None>'
	return dict.get(key, '<None>')

def html_td(text):
	return '<td>' + str(text) + '</td>'

class Static(app.page):
	path = "/static/(.+)?"
	def GET(self, path):
		#print path
		if path[0] in ('.', '/'):
			#print 'invalid path'
			return None
		ext = os.path.splitext(path)[1]
		types = {'.png':'image/png', '.gif':'image/gif','.css':'text/css','.js':'application/javascript'}
		type = types.get(ext, 'text/plain')
		web.header('Content-Type', type)
		return readfile('/'.join((HOME, 'static', path)))

class BrowseFlat(app.page):
	path = "/browseflat(/.+)?"
	def GET(self, root):
		if not root:
			root = ''
		else:
			root = root[1:]
		
		web.header('Content-Type', 'text/html')
		apps = []
		output = []
		
		yield '''<html><head>
			<script src="/appLoad/static/sorttable.js"></script>

			<!--style>
* {margin:0; padding:0}
body {font:10px Verdana,Arial}
#wrapper {width:825px; margin:50px auto}
.sortable {width:823px; border:1px solid #ccc; border-bottom:none}
.sortable th {padding:4px 6px 6px; background:#444; color:#fff; text-align:left; color:#ccc}
.sortable td {padding:2px 4px 4px; background:#fff; border-bottom:1px solid #ccc}
.sortable .head {background:#444 url(static/images/sort.gif) 6px center no-repeat; cursor:pointer; padding-left:18px}
.sortable .desc {background:#222 url(static/images/desc.gif) 6px center no-repeat; cursor:pointer; padding-left:18px}
.sortable .asc {background:#222 url(static/images/asc.gif) 6px  center no-repeat; cursor:pointer; padding-left:18px}
.sortable .head:hover, .sortable .desc:hover, .sortable .asc:hover {color:#fff}
.sortable .even td {background:#f2f2f2}
.sortable .odd td {background:#fff}			
			</style-->
<style>
/* Sortable tables */
table.sortable thead {
    background-color:#eee;
    color:#666666;
    font-weight: bold;
    cursor: default;
}
</style>
<script>

function make_list() {
	var list_text = document.getElementById("path_list");
	var boxes = document.getElementsByClassName("path_box");
	var set = {};
	var list = [];
	for (var i=0, N=boxes.length; i<N; i++) {
		box = boxes[i];
		if (box.checked) {
			set[box.value] = true;
			//list.push(box.value);
		}
	}
	list = Object.keys(set);
	list.sort();
	list_text.textContent = list.join("\\n");
}

</script>
			</head>
			<body>
		'''
		
		yield '''<table class="sortable" border="1" cellspacing="0">
		<th>Path</th><th>Parent</th><th>Filename</th><th>App id</th><th>Version</th><th>Name</th><th>Timestamp</th><th>Size (kb)</th>
		'''
		for root, dirs, files in os.walk(safejoin(FILES_ABS, root)):
			if [f for f in files if f.endswith('.ipa')]:
			
				yield '<tr>'


				path = root[len(FILES_ABS)+1:]
				if path.startswith("tmp/"):                                                                                                             
					continue                                                                                                                            

				token = apptoken.gen_token(path).lower()
				url = "http://appspot.nds.com/public/a/%s/%s\n" % (token, path)
				
				button = '<input type="checkbox" class="path_box" value="%s">'

				yield html_td(button % path + '<a href="%s">%s</a>' % (url, path))
				
				parent = os.path.dirname(path)
				yield html_td(button % parent + '<a href="/appLoad/browseflat/%s">%s</a>' % (parent, parent))
				
				ipa_file = get_file(root, '*.ipa')
				timestamp = datetime.fromtimestamp(os.path.getmtime(ipa_file)).isoformat()
				
				try:
					yield html_td(readfile(safejoin(root, 'filename')))
				except IOError:
					yield html_td(os.path.basename(ipa_file))
					
				try:
					info = extract_info(root) #plistlib.readPlist(os.path.join(root, 'info.plist'))
					if info is None:
						info = {}
				except IOError:
					info = {}
				
				yield html_td(info.get('CFBundleIdentifier','?'))
				yield html_td(info.get('CFBundleVersion','?'))
				yield html_td(info.get('CFBundleDisplayName','?'))
					
				yield html_td(timestamp)
				yield html_td(os.path.getsize(ipa_file)/1024)
					
				yield '</tr>\n'
		yield '</table>'
		
		yield '<hr>'
		yield '<input value="Make List" type="button" onclick="make_list()">'
		yield '<pre id="path_list"></pre>'
		yield '</body></html>'

def rand(L):
	return ''.join(chr(randint(0,25)+ord('a')) for i in range(L))


class Upload(app.page):
	path = "/?"
	def GET(self):
		#raise web.notfound()
		
		web.header('Content-Type', 'text/html')
		return readfile(os.path.join(HOME, "upload.html"))
	
	def POST(self):
		#raise web.notfound()
		

		x = web.input(fileToUpload={}, path=None, output=None)
		
		# print "Upload started, form data:", repr(x)
		
		#filename = x['fileToUpload'].filename
		file = x['fileToUpload']
		filename = file.filename
		path = x['path']
		
		log("UPLOAD:START: " + str(path))

		# detect ipa or apk
		apptype = os.path.splitext(filename)[1].lower()
		if apptype not in ('.ipa','.apk'):
		    raise web.notfound('invalid app')
		
		
		# download to a temporary dir
		upload_dir = os.path.join(FILES_ABS, 'tmp')
		mkdir_p(upload_dir)
		upload_dir = mkdtemp(dir=upload_dir)
		
		#filename = filename.replace("/","_")
		
		writefile(os.path.join(upload_dir, "filename"), filename)
		writefile(os.path.join(upload_dir, "app" + apptype), file.value)
		
		# gen token
		if x.get('keepToken')=='1' and path and os.path.isdir(safejoin(FILES_ABS, path)):
			new_token = apptoken.gen_token(path, False)
			print "Keeping old token", new_token, "for new upload", path
		else:
			new_token = gen_rand_token(False)
			
		writefile(os.path.join(upload_dir, "TOKEN"), new_token)
		
		notes = x.get('notes')
		if notes:
			writefile(os.path.join(upload_dir, "notes.txt"), notes)

		env_vars = x.get('env_vars')
		if env_vars:
			writefile(os.path.join(upload_dir, "env_vars.txt"), env_vars)
		
		if apptype == '.ipa':
			info = extract_info(upload_dir)
		elif apptype == '.apk':
			info = extract_info_apk(upload_dir)
		
		log("UPLOAD:INFO: " + repr(info))

		if not path:
			appid = info.get('CFBundleIdentifier', 'unknown')
			path_base = os.path.join(FILES_ABS, 'upload', 'app_' + appid)
			mkdir_p(path_base)
			for i in xrange(100):
				sub_path = rand(8)
				try:
					path_abs = os.path.join(path_base, sub_path)
					os.rename(upload_dir, path_abs)
					path = path_abs[len(FILES_ABS)+1:]
				except OSError:
					continue
				break
		
		else:
			path_abs = safejoin(FILES_ABS, path)
			if os.path.isdir(path_abs):
				shutil.rmtree(path_abs)
			else:
				mkdir_p(os.path.dirname(path_abs))

			os.rename(upload_dir, path_abs)

		
		token = apptoken.gen_token(path).lower()
		
		url = "http://appspot.nds.com/public/a/%s/%s\n" % (token, path)
		
		log("UPLOAD:DONE: " + url)

		if x['output'] == "link":
			return '''<a href="%s">%s</a>''' % (url, path)
		
		return url
		

class TestTimeout(app.page):
    path = "/timeout"
    def GET(self):
	print "starting timeout"
	from time import sleep
	sleep(500)
	print "500 left"
	sleep(500)
	print "done"
	
    def HEAD(self): return self.GET()
    def POST(self): return self.GET()	

application = app.wsgifunc()
print sys.version

if __name__ == "__main__":
	#print dir(app.wsgifunc)
	sys.argv.append('8989')
	app.run()
