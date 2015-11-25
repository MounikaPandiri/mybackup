import ast
import os

import csv
#from tabulate import tabulate

def csvAnalyzer(load,filePath):
	#import pdb
	#pdb.set_trace()
	#check if for invite file or reg
	load=int(load)
	fp=open(filePath,'r')
	data=fp.readlines()
	callRate=''
	returnDict={}
	totalSuccessfulCalls=0
	totalFailedCalls=0
	for line in range(1,len(data)-1):
		lineContents=data[line].split(';')
		totalSuccessfulCalls+=int(lineContents[14])
		totalFailedCalls+=int(lineContents[16])
	if totalSuccessfulCalls+totalFailedCalls > 0:
		callRate=totalSuccessfulCalls/float(totalSuccessfulCalls+totalFailedCalls)
	else:
		callRate=1
	returnDict['load']=load
	returnDict['CSR']=callRate
	return returnDict
	
def csvWrite(function,data,path):
	#import pdb
	#pdb.set_trace()
	strin=str(data)
	strin=strin.replace('\\t','-')
	dictReport=ast.literal_eval(strin)
	fileName=''
	fileData=''
	if function=='invite':
		for i in dictReport:
			fileName=i
			fileData=dictReport[i]
	elif function=='registration':
		resultDict=dictReport['register_result']
		for i in resultDict:
			fileName=i
			fileData=resultDict[i]
	currPath=os.getcwd()
	fileName=path+'/'+fileName
	fp=open(fileName,'a')
	print len(fileData)
	for i in fileData:
		fp.write(i)
	return fileName
#csvFileName=csvWrite('registration',s1)
#print 'done'
#csvAnalyzer(100,'invite_final_1_1708_.csv')
