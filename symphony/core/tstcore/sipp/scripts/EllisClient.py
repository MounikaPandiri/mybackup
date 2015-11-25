import requests
import json
import sys
import argparse
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# create a file handler

handler = logging.FileHandler('Ellis.log')
handler.setLevel(logging.INFO)

# create a logging format

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger

logger.addHandler(handler)

class EllisClient(object):
  
    def __init__(self):
        pass

    def register_user(self, ellis_ip, username, password, fullname, email):
        headers = { 'Accept': 'application/json', 
                    'Content-Type': 'application/json', 
                    'NGV-API-Key': 'secret', 'NGV-Signup-Code': 'secret'}
  
        url = "http://"+str(ellis_ip)+"/accounts/"
  
        payload = {'username': username, 'password': password, 
                   'full_name': fullname, 'email': email}
  
        req_session = requests.Session()

        resp = req_session.post(url, data=json.dumps(payload), stream=False, headers=headers)

        return resp.__dict__

    def register_number(self, ellis_ip, number, email):
        headers = { 'Accept': 'application/json', 
                    'Content-Type': 'application/json', 
                    'NGV-API-Key': 'secret', 'NGV-Signup-Code': 'secret'}

        url = "http://"+ellis_ip+"/accounts/"+email+"/numbers/sip:"+str(number)+"@test.com/"

        payload = {'private_id': str(number)+"@test.com", 'new_private_id': 'True'}

        req_session = requests.Session()

        resp = req_session.post(url, data=json.dumps(payload), stream=False, headers=headers)

        return resp.__dict__

def main(*args):
    ec = EllisClient()
    arguments = args[0]
    csv = open("/home/tcs/scripts/"+arguments.file_name+".csv", 'w')
    if arguments.caller:
        file_name = arguments.file_name.replace('register', 'invite')
        invite = open("/home/tcs/scripts/"+file_name+".csv", 'w')
        invite.write('SEQUENTIAL\n')
    csv.write('SEQUENTIAL\n')
    ellis_ip = arguments.ellis_ip
    min_number = arguments.base_number
    max_number = arguments.base_number + arguments.call_count       
    for i in range(min_number, max_number):
        try:
            res = ec.register_user(ellis_ip, 'sim'+str(i), 'tcs@12345', 'sim'+str(i), 'sim'+str(i)+'@ex.com')
            user_details = ec.register_number(ellis_ip, i, 'sim'+str(i)+'@ex.com')
            logger.debug(user_details)
            sip_data = json.loads(user_details['_content'])
            file_data = sip_data['number']+';test.com;[authentication username='+sip_data['sip_username']+' password='+sip_data['sip_password']+'];'
            csv.write(file_data+'\n')
            file_data_invite = file_data + str(int(sip_data['number'])+arguments.call_count)+';'
            if arguments.caller:
                invite.write(file_data_invite+'\n')
        except KeyError:
             csv.close()
             if arguments.caller:
                 invite.close()
             logger.debug("Unable to complete the Registration")
             return "Unable to complete the Registration"
    csv.close()
    if arguments.caller:
        invite.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--ellis_ip", type=str, help="Ellis IP")
    parser.add_argument("--call_count", type=int, help="Number of user to be registred")
    parser.add_argument("--base_number", type=int, help="Usernumber starts with")
    parser.add_argument("--file_name", type=str, help="name of the file to stote the deatils")
    parser.add_argument("--caller", action="store_true", help="Specify whether is is caller/calle", default=False)
    arguments = parser.parse_args(sys.argv[1:])
    main(arguments)
