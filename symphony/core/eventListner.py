import os,sys

cwd=os.getcwd()
cwd=cwd.split('/')
sysPath=''
for dirName in range(1,len(cwd)-1):	#for determining path to root (symphony) directory
	sysPath=sysPath+'/'+cwd[dirName]
sys.path.append(sysPath)

from flask import Flask, request, Response, g
from lxml import etree
from StringIO import StringIO
import os
import json
import socket 

import executionCore
import threading 
import eventlet
from common import utils

eventlet.monkey_patch() 

app = Flask(__name__, instance_path='/tmp/ns_events')


class EventListner(threading.Thread):
 
    @app.route("/index")
    def hello():
	#comm_queue
	fileRef = open('/var/symphony/session_data/9df174ea-1314-41cd-a2e3-ae84c236eaea/b4ded600-4e6d-43da-a8ab-eb2decf55460/nsinfo','r')
	buf = fileRef.read()
	utils.eventNotification.acquire()
	utils.comm_queue.append(buf)
	utils.eventNotification.notify()
	utils.eventNotification.release()
        return "Welcome to Python Flask App!"


    @app.route("/events")
    def events():
	    templateid = request.args.get('template_id')
	    nsid = request.args.get('ns_id')
	    filename = os.path.join(logdir, nsid)
	    ns_events = os.path.join(filename, "events")
	    with open(ns_events) as f:
		data = f.read()
	    if data is None:
		return "No network service info is available"
	    else:
		return Response(data, mimetype='text/plain')
		#return Response(data[2])

    @app.route("/nsinfo")
    def nsinfo():
	    templateId = request.args.get('template_id')
	    nsid = request.args.get('ns_id')
	    templatePath = os.path.join(logdir, templateId)
	    filename = os.path.join(templatePath, nsid)
	    #filename = '/var/symphony/session_data/9df174ea-1314-41cd-a2e3-ae84c236eaea/b4ded600-4e6d-43da-a8ab-eb2decf55460'
	    ns_info = os.path.join(filename, "nsinfo")
	    if not os.path.exists(ns_info):
		return "No network service info is available"
	    else:
		with open(ns_info) as f:
		    data = f.read()
		if data is None:
		    return "No network service info is available"
		else:
		    return Response(data, mimetype='text/xml')

    @app.route("/Insert", methods=["GET", "POST"])
    def Insert():
	    if request.method == 'GET':
		return "Welcome"
	    templateid = request.args.get('template_id')
	    nsid = request.args.get('ns_id')
	    xml_dat = json.loads(request.data)
	    if not xml_dat:
		xml_dat = "Data not available"
	    ns_template = os.path.join(logdir, templateid)
	    if not os.path.exists(ns_template):
		os.makedirs(ns_template)
	    ns_path = os.path.join(ns_template, nsid)
	    if not os.path.exists(ns_path):
		os.makedirs(ns_path)
	    filename = os.path.join(ns_path, "events")
	    #buf = fileRef.read()
	    buf = xml_dat['notification']['event']
	    utils.eventNotification.acquire()
	    utils.comm_queue.append(buf)
	    utils.eventNotification.notify()
	    utils.eventNotification.release()
            if not os.path.exists(filename):
                with open(filename, 'w') as f:
                    f.write(xml_dat['notification']['event'])
                    f.write("\n")
                events = ["Onboard_complete", "Deletion"]
                for event in events:
                    if event in xml_dat['notification']['event']:
                        ns_file = os.path.join(ns_path, "nsinfo")
                        with open(ns_file, 'w') as f:
                            f.write(xml_dat['notification']['xml_info'])
            else:
                 with open(filename, "a") as f:
                     f.write(xml_dat['notification']['event'])
                     f.write("\n")
                 events = ["Onboard_complete", "Deletion"]
                 for event in events:
                     if event in xml_dat['notification']['event']:
                         ns_file = os.path.join(ns_path, "nsinfo")
                         with open(ns_file, 'w') as f:
                             f.write(xml_dat['notification']['xml_info'])
            return "Success in committing"

    @app.route('/shutdown', methods=['POST'])
    def shutdown():
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()
        return 'Server shutting down...'

    def run(self):
	args = {'host':self.host,'port':self.port,'threaded':'True'}
	app.use_reloader = False
	app.run(**args)
    
    def __init__(self, host, port,queue,logDir):
	self.port = port
	self.host = host
	self.logDir = logDir
	self.eventQueue = queue
        global logdir
        logdir = self.logDir
	

