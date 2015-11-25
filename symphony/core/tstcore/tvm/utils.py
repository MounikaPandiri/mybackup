from common import utils
from common import schema

def get_interfaces(client):
    retries = 0
    interface_set = True
    while interface_set:
        try:
            output, err = utils.exec_command("cli listInterfaces| tail --lines=+2 | awk '{print $1}'", client=client)
        except exception.TypeError:
            retries = retries + 1
            if retries > schema.MAX_RETRIES:
               break
        if output:
            interfaces = output.rstrip('\n').split('\n')
        return interfaces
