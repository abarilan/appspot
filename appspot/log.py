#!/usr/bin/env python

import os, sys
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storelib import HOME
import web

logging.basicConfig(format='%(message)s', filename=os.path.join(HOME, "log", "access.log"), level=logging.INFO)
def log(msg):
    try:
        ip = web.ctx.ip
    except AttributeError:
        ip = None
    
    logging.info("[%s] %s %s" % (ip, datetime.utcnow().isoformat(), msg))

