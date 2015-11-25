import paramiko
import time

MAX_RETRY_COUNT = 300
def _check_connection():
    ssh_connected = False
    # keep connecting till ssh is success
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    retries = 0;
    while not ssh_connected:
        try:
            if retries != MAX_RETRY_COUNT:
                ssh.connect(self.mgmt_ip, username = self.uname, password = self.password, allow_agent=False, timeout=10)
                ssh_connected = True
                print "No of retries if success : " + str(retries)
                print "VM IS UP"
        except Exception:
            print "No of retries if failure : " + str(retries)
            retries += 1
            time.sleep(10)
            print "VM IS DOWN"
            pass

_check_connection()
