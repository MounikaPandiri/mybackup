#! /usr/bin/python

# Python module to run netconf commands

# Usage:
#	wrapper = NetconfJavaWrapper("10.138.89.35","root","firefly2")
#	wrapper.executeCommands(<list of command type and command>)

# The client should catch "CommandInSufficientException" to check if valid arguments are passed to the "executeCommands" method
# Examples of valid arguments are
#	wrapper.executeCommands(["cli", "show log"])
#	wrapper.executeCommands(["configuration", "show system host-name"])

#	wrapper.executeCommands(["show system host-name"])

import os
import sys
from time import sleep
from subprocess import call, Popen, PIPE

class CommandInSufficientException(Exception):
	def __init__(self, value):
	        self.value = value
class IncorrectInputException(Exception):
	def __init__(self,exType,exValue):
		self.exType=exType
		self.exValue=exValue
	def __str__(self):
		return "Exception"+":"+self.exType+":"+self.exValue
class NetconfJavaWrapper:
	def __init__(self, ip, uname, password, ncport):
		self.__ip = "server="+ip
		self.__uname = "user="+uname
		self.__password = "password="+password
		self.__ncport = "ncport="+ncport

	def executeCommand(self, command):
		commandList = [command]
		#print commandList
		executionList = ['/home/tcs/Desktop/working/OpenYuma-master/netconf/target/bin/yangcli']
		executionList.extend([self.__ip, self.__uname, self.__password, self.__ncport])
		executionList.append(command);
		#executionList.extend(command);
		#print executionList
		process = Popen(executionList, stdout=PIPE)
		retVal = "";
		for line in iter(process.stdout.readline,''):
			retVal = retVal + line.rstrip()+"\n"
		if "exception" in retVal:
			#print("Caught in Python : java exception");
			result=retVal.split(";")
			resultClass=result[1].split(".")
			raise IncorrectInputException(resultClass[-1],result[2])
		else:
			return retVal

			
	def __str__(self):
		return "NetconfJavaWrapper : " + self.__ip + " : " + self.__uname

class build_cmds:

    ops_maps = {'set':'create','show':'sget','delete':'delete'}

    resource_maps = {
            'map_key_firewall':{'firewall':'firewall-name',
                                'rule':'rule',
                                'action':'action',
                                'default-action':'default-action',
                                'destination':'destination/address'},
            'map_key_nat':{'nat':'source',
                           'rule':'rule',
                           'source':'source/address',
                           'destination':'destination/address',
                           'translation':'translation/address',
                           'outbound-interface':'outbound-interface'},

            'map_key_interfaces':{'ethernet':'ethernet',
                                  'firewall':'firewall/in/name'}
    }

    def build_cmd(self, keys,resource):
        return self.ops_maps[keys] + ' /vyatta-'+resource

    def set_name(self, resource, args_list):
        list_len = len(args_list)
        maps1 = self.resource_maps['map_key_'+resource]
        return command + '/' + maps1[args_list[0]] +'[name=\'' + args_list[list_len-1] +'\']'

    def set_value(self, resource, args_list):
        list_len = len(args_list)
        maps1 = self.resource_maps['map_key_'+resource]
        return command + '/' + maps1[args_list[0]] + ' --value=\"' + args_list[list_len-1]+'\"'

    def set_default(self, resource, args_list):
        list_len = len(args_list)
        return command + '/' + args_list[list_len-1]

    def add_cmdparms_firewall(self,command,cmd,args_list):      
        if cmd =="set":
            if args_list[0] == "firewall" or args_list[0] == "rule":
                return self.set_name(resource,args_list)
            else:
                return self.set_value(resource,args_list)
        else:
                return self.set_default(resource,args_list)

    def add_cmdparms_nat(self,command,cmd,args_list):        
        if cmd =="set":
            if args_list[0] == "nat":
                return command + '/' + self.map_key_nat[args_list[0]]
            elif args_list[0] == "rule":
                return self.set_name(resource,args_list)
            else:
                return self.set_value(resource,args_list)
        else:
                return self.set_default(resource,args_list)

    def add_cmdparms_interfaces(self,command,cmd,args_list):        
        if cmd =="set":
            if args_list[0] == "ethernet":
                return self.set_name(resource,args_list)
            else:
                return self.set_value(resource,args_list)
        else:
                return self.set_default(resource,args_list)


cli_cmds = ['set','show','delete']
wrapper = NetconfJavaWrapper(sys.argv[1],sys.argv[2],sys.argv[3], sys.argv[4])

"""keywords_firewall = ['firewall','default-action','rule','destination','action']
keywords_nat = ['nat','source','rule','outbound-interface','destination','translation']
keywords_interfaces = ['ethernet','firewall']

val_firewall = {'firewall':3,'default-action':2,'rule':2,'destination':3,'action':2}
val_nat = {'nat':2,'rule':2,'source':2,'outbound-interface':1,'destination':3,'translation':2}
val_interfaces = {'firewall':4,'ethernet':2}
#actions = ['drop','accept','reject']
# uncomment below lines to test from command line


cmd1 = build_cmds()
cmd_args = sys.argv[1]
args_list = cmd_args.split(' ')
ops = args_list[0]
resource = args_list[1]
command = ""

if ops in cli_cmds:

    if resource == 'firewall':
        command = cmd1.build_cmd(ops,resource)
        for args in args_list:
            if args in keywords_firewall:     
                val1 = args_list.index(args)
                val2 = val_firewall[args]
                updt_list = args_list[val1:val1+val2]
                command = cmd1.add_cmdparms_firewall(command,args_list[0],updt_list)
            else:
                pass
    elif resource == 'nat':
        command = cmd1.build_cmd(ops,resource)
        val1 = args_list.index('nat')
        val2 = val_nat['nat']
        updt_list = args_list[val1:val1+val2]
        command = cmd1.add_cmdparms_nat(command,args_list[1],updt_list)
        args_list1 = args_list[val1+val2:]

        for args in args_list1:       
           if args in keywords_nat:   
                val1 = args_list1.index(args)
                val2 = val_nat[args]
                updt_list = args_list1[val1:val1+val2]
                command = cmd1.add_cmdparms_nat(command,args_list[0],updt_list)
           else:
                pass

    elif resource == 'interfaces':
        command = cmd1.build_cmd(ops,resource)
        for args in args_list:
           if args in keywords_interfaces:     
               val1 = args_list.index(args)
               val2 = val_interfaces[args]
               updt_list = args_list[val1:val1+val2]
               command = cmd1.add_cmdparms_interfaces(command,args_list[0],updt_list)
           else:
               pass       

    else:
        print 'Unknown Resource '+resource        
    #print command

else:
        print args_list[0]+"-No Such Command Found"
"""
command = sys.argv[5]
#command = "replace /vyatta-nat/source/rule[name='3']/destination/address --value='!200.168.1.0/24'"

if(command != ""):
    print wrapper.executeCommand(command)        
