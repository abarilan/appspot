#!/usr/bin/env python

import string
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
import xml.dom.minidom as dom
#from xml.etree import cElementTree as etree

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp")


import plistlib
import ipin

HOME = os.path.dirname(os.path.abspath(__file__))
FILES_DIR = "files"
FILES_ABS = os.path.join(HOME, FILES_DIR)

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError, exc:
        if exc.errno == errno.EEXIST:
            pass
        else: raise

def readfile(path):
	f = open(path, "rb")
	data = f.read()
	f.close()
	return data

def writefile(path, data):
	f = open(path, "wb")
	f.write(data)
	f.close()

def prepare_manifest(info, url):

	CFBundleDisplayName = info["CFBundleDisplayName"]
	CFBundleName = info["CFBundleName"]
	CFBundleVersion = info["CFBundleVersion"]
	CFBundleIdentifier = "" + info["CFBundleIdentifier"] #+ ".ios8fix"
	try:
		CFBundleIconFile = info["CFBundleIconFile"]
	except KeyError:
		CFBundleIconFile = "icon.png"
	
	ipa_url = url + "/app.ipa"
	icon_url = url + "/icon.png"
	
	manifest_plist = {
		'items' : [
			{
				'assets' : [
					{
						'kind' : 'software-package',
						'url' : ipa_url,
					},				
					{
						'kind': 'display-image',
						'needs-shine': True,
						'url' : icon_url,
					},
                                        {
                                                'kind': 'full-size-image',
                                                'needs-shine': True,
                                                'url' : icon_url,
                                        }
				],
				'metadata' : {
					'bundle-identifier' : CFBundleIdentifier,
					'bundle-version' : CFBundleVersion,
					'kind' : 'software',
					'title' : CFBundleDisplayName,
					}
				}
			]
		}
	
	return plistlib.writePlistToString(manifest_plist)


def get_file_content(path, name):
	f = get_file(path, name)
	if f:
		return readfile(f)

def get_file(path, pattern):
	g = glob.glob(os.path.join(FILES_ABS, path, pattern))
	if not g:
		return None
	return g[0]

def firstByName(xml, name):
    e = xml.getElementsByTagName(name)
    if e and len(e) > 0:
	return e[0]
    return None

def extract_info_apk(path):
	apk_file = get_file(path, "*.apk")
	info_name = os.path.join(FILES_ABS, path, "info.plist")
	xml_name = os.path.join(FILES_ABS, path, "manifest.xml")
	try:
		if os.path.getmtime(apk_file) < os.path.getmtime(info_name):
			return plistlib.readPlist(info_name)
	except:		# the above may fail on file not found or corrupted plist
		pass
	
	# this takes care of extracting manifest into xml
	os.system('java -classpath "%s" AndroidXMLDecompress "%s" > "%s"' % (HOME, apk_file, xml_name));
	
	# now build plist from android xml
	xml = dom.parse(xml_name)
	#print xml.toxml()
	
	packageName = firstByName(xml, "manifest").getAttribute("package")
	appName = firstByName(xml, "application").getAttribute("name")
	versionName = firstByName(xml, "manifest").getAttribute("versionName")
	
	if not appName:
	    appName = packageName
	
	info_plist = {
		'packageName': packageName,
		'appName': appName,
		'versionName': versionName
	}

	plistlib.writePlist(info_plist, info_name)
	return info_plist


def extract_info(path):

	ipa_file = get_file(path, "*.ipa")
	xml_name = os.path.join(FILES_ABS, path, "info.plist")
	try:
		if os.path.getmtime(ipa_file) < os.path.getmtime(xml_name):
			return plistlib.readPlist(xml_name)
	
	except:		# the above may fail on file not found or corrupted plist
		pass
	
	ipa_file = get_file(path, "*.ipa")
	ipa = ZipFile(ipa_file, 'r')
	names = ipa.namelist()


	# find the info.plist
	info_plist = [f for f in names if re.match("Payload/.+\.app/\w*\-?Info\.plist", f)]

	# convert to xml
	if not info_plist:
		return None
	data = ipa.read(info_plist[0])
	temp = mkdtemp(dir=TEMP_DIR)
	
	if data.startswith("bplist"):
		bin_name = os.path.join(temp, "info.plist")
		writefile(bin_name, data)	
		os.system('"%s/plutil.pl" "%s"' % (HOME, bin_name))
		os.rename(os.path.join(temp, "info.text.plist"), xml_name)
	else:
		writefile(xml_name, data)

	# now parse info.plist
	info = plistlib.readPlist(xml_name)
		
	# extract icon
	icon_file = [f for f in names if re.match(r"Payload/.+\.app/" + info.get('CFBundleIconFile', 'icon.png'), f)]
	try:	
		data = ipa.read(icon_file[0])
		norm = ipin.getNormalizedPNG(data)
		if not norm:
			norm = data

		writefile(os.path.join(FILES_ABS, path, "icon.png"), norm)
	except:
		print "No icon"
		pass
	
	# extract provisioning profile
	prov_file = [f for f in names if re.match(r"Payload/.+\.app/embedded.mobileprovision", f)]
	try:
		data = ipa.read(prov_file[0])
		
		# HACK: extract plist from profile
		plist = data[data.index("<?xml"):data.rindex("</plist>")+len("</plist>")]
		profile = plistlib.readPlistFromString(plist)
		
		plistlib.writePlist(profile, os.path.join(FILES_ABS, path, "Provision.plist"))
		
		devices = profile.get('ProvisionedDevices', None)
		if devices:
			plistlib.writePlist(devices, os.path.join(FILES_ABS, path, "ProvisionedDevices.plist"))
			
		# also save the mobileprovision file as-is
		writefile(os.path.join(FILES_ABS, path, "embedded.mobileprovision"), data)
		
	except:
		print "No embedded profile"
		pass
	
	ipa.close()
		
	return info



# token
try:
	from hashlib import sha1
except ImportError: # python v < 2.5
	from sha import new as sha1

TOKEN_SECRET = "d4789t23984gf2i3rgb98d75ydljkhbfwe8d274yt89d273gekwrhjg290378y5"

#CHARS = "0123456789abcdefghijklmnopqrstuvwxyz"
CHARS = "BCDFGHJKLMNPQRSTVWXZ"	# no vowels
CHARS_LEN = len(CHARS)
NUM_BYTES_IN_TOKEN = 8
TRANS_TABLE = string.maketrans("0123456789aeiou","ghjklmnpqrstvwx")	# convert digits to letters and remove vowels

def dashed_token(token):
    tok_len = len(token)
    r = []
    for i in xrange(tok_len):
	if i > 0 and i % 4 == 0:
	    r.append('-')
	r.append(token[i])
    return ''.join(r)
    

def gen_rand_token(dash=True):
    s = os.urandom(NUM_BYTES_IN_TOKEN).encode('hex').translate(TRANS_TABLE)
    r = []
    
    if dash:
	for i in xrange(NUM_BYTES_IN_TOKEN * 2):
	    if i > 0 and i % 4 == 0:
		r.append('-')
	    r.append(s[i])
	token = ''.join(r)
    else:
	token = s

    return token
	
def gen_token_hash(path, dash=True):
	s = sha1(TOKEN_SECRET)
	s.update(path)

	retok = get_file_content(path, "retok")
	if retok:
		s.update(retok)
	
	s = s.digest()
	
	s = s[:12]
	r = []
	if dash:
		for i in xrange(len(s)):
			if i > 0 and i % 4 == 0:
				r.append('-')
			r.append(CHARS[ord(s[i]) % CHARS_LEN])
	else:
		r = [CHARS[ord(c) % CHARS_LEN] for c in s]
	
	return ''.join(r)

def gen_token(path, dash=True):
    realtoken = get_file_content(path, "TOKEN")
    if realtoken:
	token = realtoken.strip()
	if dash:
	    return dashed_token(token)
	else:
	    return token
    else:
	return gen_token_hash(path, dash)
    
    

def check_token(token, path):    
    realtoken = get_file_content(path, "TOKEN")
    if realtoken:
	return realtoken.strip() == token.replace('-','').lower()
    else:
	return gen_token(path, False) == token.replace('-','').upper()



