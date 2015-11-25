import report
import sys,os

cwd=os.getcwd()
cwd=cwd.split('/')
sysPath=''
for dirName in range(1,len(cwd)-1):     #for determining path to root directory
        sysPath=sysPath+'/'+cwd[dirName]

sys.path.append(sysPath)
from common import utils
from termcolor import colored,cprint
import time

def __report__(method):
    def logForReporting(*args,**kwargs):
        temp_fnName = args[1]
        text = '\n\n***\t'+ temp_fnName + '\n'
        cprint(text,'white',on_color='on_cyan',attrs=['bold'])
        result = method(*args,**kwargs)
        try:
           for function in result['report'].keys():
               getattr(utils.pdf, function)(result)
        except:
           pass
        return result
    return logForReporting
