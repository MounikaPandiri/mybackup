from core import executionCore
import sys,os

cwd=os.getcwd()
cwd=cwd.split('/')
sysPath=''
for dirName in range(1,len(cwd)-3):     #for determining path to root directory
        sysPath=sysPath+'/'+cwd[dirName]

sys.path.append(sysPath)
class tvm(object):
 
	def __init__(self,onboard='True'):
		"""onboard the test framework"""
		self.templateID = self.execore.onBoard(self.NSD)
		self.exeCore.createService(self.templateID)
