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
            self.tcase_run = 0
            self.tcase_dir = None

	@report.__report__
	def execute(self,method, **kwargs):
	    if method in self.testCaseMap :
                import pdb;pdb.set_trace()
		invokeMethod =  self.testCaseMap[method]
                self.tcase_run = self.tcase_run + 1
                self.create_private_sessionDir(method)
	    else :
		invokeMethod = 'unsupportedOperation'
		setattr(kwargs,'unsupportedOperation',method)

	    return getattr(self,invokeMethod)(**kwargs)

        def startDiagnostics(self):
            self.execore.startDiagnostics(self.tcase_dir)

        def stopDiagnostics(self):
            self.execore.Stopdiagnostics(self.tcase_dir)
           
	def unsupportedOperation(self,**kwargs):
		exceptionString = 'Unsupported operation : ' + kwargs['unsupportedOperation'] + ' for module ' + self.__name__
		raise ValueError(exceptionString)

        def create_private_sessionDir(self, method):
            """All testcase specific data is stored 
            by creating a directory for each testcase execution"""

            tcase = method + str(self.tcase_run)
            session_dir = os.path.join(self.execore.sessionDir, tcase)

            try:
                os.mkdir(session_dir)
                self.tcase_dir = session_dir
                #if a directory with the same session ID exists raise exception
            except:
                raise
