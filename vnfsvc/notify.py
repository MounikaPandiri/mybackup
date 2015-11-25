import datetime
class notifyClient():

    def __init__(self):
        self.msg = None

    def info(self, nsdid, event, msg):
        msg_notify = "%s INFO %s %s %s " % (str(datetime.datetime.now()).split('.')[0], nsdid, event, msg)
        return msg_notify

    def error(self, nsdid, event, msg):
        msg_notify = "%s ERROR %s %s %s " % (str(datetime.datetime.now()).split('.')[0], nsdid, event, msg)
        return msg_notify
"""    
    def notify_user(self, userdetails, templateid, nsdid, msg, xml_info = None):
         import pdb;pdb.set_trace()
         url = userdetails['endpoint'] + '?template_id=' + templateid + '&ns_id='+ nsdid
         #return requests.post(url, data={"xml_info": data})
         data={"notification":{"event": msg, "xml_info": xml_info}}
         return requests.post(url, data=json.dumps(data))
"""      
