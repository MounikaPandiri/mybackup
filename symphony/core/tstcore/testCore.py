import os,sys

cwd=os.getcwd()
cwd=cwd.split('/')
sysPath=''
for dirName in range(1,len(cwd)-2):	#for determining path to root directory
	sysPath=sysPath+'/'+cwd[dirName]

sys.path.append(sysPath)

from report import report
class TestCore(object):
	def __init__(self):
            import pdb;pdb.set_trace()
	    self.moduleName = self.__name__
            self.tcase=0

	@report.__report__
	def execute(self,method, **kwargs):
	    if method in self.testCaseMap :
                import pdb;pdb.set_trace()
		invokeMethod =  self.testCaseMap[method]
                self.tcase = self.tcase + 1
	    else :
		invokeMethod = 'unsupportedOperation'
		setattr(kwargs,'unsupportedOperation',method)

	    return getattr(self,invokeMethod)(**kwargs)

        def startDiagnostics(self):
            self.execcore.startDiagnostics()

        def stopDiagnostics(self):
            self.execcore.Stopdiagnostics()
           

	def unsupportedOperation(self,**kwargs):
		exceptionString = 'Unsupported operation : ' + kwargs['unsupportedOperation'] + ' for module ' + self.__name__
		raise ValueError(exceptionString)

