#!/usr/bin/env python

from storelib import gen_token, check_token

if __name__ == "__main__":
	import sys
	app = sys.argv[1]
	print "http://appspot.nds.com/public/a/" + gen_token(app).lower() + "/" + app
