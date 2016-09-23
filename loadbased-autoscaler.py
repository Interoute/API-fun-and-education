#! /usr/bin/env python
# Python script for the Interoute Virtual Data Centre API:
#   Name: loadbased-autoscaler.py
#   Purpose: Perform autoscaling of webserver virtual machines in VDC based on loading of an HAProxy frontend load-balancer
#   Requires: class VDCApiCall in the file vdc_api_call.py
# See the repo: https://github.com/Interoute/API-fun-and-education
#
# You can pass options via the command line: type 'python loadbased-autoscaler.py -h' for usage information
#
# This program must be run with 'sudo' because it rewrites the file '/etc/haproxy/haproxy.cfg' 
#
# Based on an original VDC implementation and Perl script by Stefan Bienek
#
# Copyright (C) Interoute Communications Limited, 2016
#
# NOTES AND REFERENCES
# Rewriting 'haproxy.cfg': http://www.kloppmagic.ca/auto-scaling-with-haproxy/
# Using a threading timer to repeat a function call: http://stackoverflow.com/questions/12435211/python-threading-timer-repeat-function-every-n-seconds

from __future__ import print_function
import vdc_api_call as vdc
import requests
import sys
import getpass
import json
import os
import string
import time
import datetime
import argparse
import re
import math
from subprocess import call

def write_logfile(logfile_handle, message):
   timeNow = datetime.datetime.utcnow()
   timestamp = timeNow.strftime("%Y-%m-%dT%H:%M:%S+0000")
   logfile_handle.write("%s : %s\n" % (timestamp, message))

# SETUP: Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", default=os.path.join(os.path.expanduser('~'), '.vdcapi'),
               help="path/name of the config file to be used for the API URL and API keys (default is ~/.vdcapi)")
parser.add_argument("-r", "--region", choices=['Europe','europe','USA','usa','Asia','asia'],
               default='Europe', help="specify the VDC region: Europe, USA or Asia (default Europe)")
parser.add_argument("-i", "--interval", default=240,
               help="specify the time interval in seconds for running the autoscaler process (default 240 seconds)")
parser.add_argument("-t", "--timeout", default=300,
               help="specify the deploy 'timeout': if deploy time exceeds this, the VM deploy will be abandoned (default 300 seconds)")
parser.add_argument("-l", "--logfile", default='./autoscaler.log',
               help="path/name of the logfile to be used to log the runs of the autoscaler process (default ./autoscaler.log)')")
vdcRegion = parser.parse_args().region
config_file = parser.parse_args().config
repeat_interval = parser.parse_args().interval
deploy_timeout = parser.parse_args().timeout
logfile = parser.parse_args().logfile

# TEMPORARY: Hard configuration settings (these should be set via a configuration file)
# REPLACE [INSERT] WITH YOUR OWN VALUES
haproxyStatsURL = 'http://[INSERT]/haproxy?stats;csv'
haproxyStatsUser = '[INSERT]'
haproxyStatsPassword = '[INSERT]'
zoneID = '7144b207-e97e-4e4a-b15d-64a30711e0e7'
templateID = '[INSERT]'
serviceofferingID = '4cb92069-e001-4637-8848-76d74f406bb8'
networkIDs = '[INSERT],[INSERT]'
haproxyConfigFileStatic = 'haproxy_cfg_static'
haproxyConfigFile = '/etc/haproxy/haproxy.cfg'
# name stem for VMs, a timestamp and count digits will be added
vmName = 'Webcluster-Frankfurt-web-'   
# min and max numbers of VMs to run
maxVM = 10			
minVM = 1
# the target loading of the cluster is a mean number of web sessions per VM
sessionPerVM = 5		

# SETUP: If config file is found, read its content, else query user for the URL, API key, Secret key
if os.path.isfile(config_file):
    with open(config_file) as fh:
        data = fh.read()            
        config = json.loads(data)
        api_url = config['api_url']
        apiKey = config['api_key']
        secret = config['api_secret']
else:
    print('API url (e.g. http://10.220.18.115:8080/client/api):', end='')
    api_url = raw_input()
    print('API key:', end='')
    apiKey = raw_input()
    secret = getpass.getpass(prompt='API secret:')

# SETUP: Create the api access object for VDC
api = vdc.VDCApiCall(api_url, apiKey, secret)

# THE REST OF THE PROGRAM RUNS IN A REPEATING LOOP, WITH A DELAY OF repeat_interval SECONDS AT THE END OF THE LOOP
repeatOn = True
logfile_handle = open(logfile, 'w', 1)

while repeatOn:
    # STEP: Program starting message
    timeNow = datetime.datetime.utcnow()
    timestamp = timeNow.strftime("%Y-%m-%d %H:%M:%S UTC")
    write_logfile(logfile_handle, 'Starting')
    print("\n\n********************************************")
    print("loadbased_autoscaler: Starting at %s" % timestamp)
    print("********************************************")

    # STEP: Check the number of running VMs
    vmresult1 = api.listVirtualMachines({'region': vdcRegion, 'zone': zoneID, 'state': 'Running', 'name': vmName})
    ## add VMs with state=Starting because the VM deploy time could be longer than the run frequency of this script
    vmresult2 = api.listVirtualMachines({'region': vdcRegion, 'zone': zoneID, 'state': 'Starting', 'name': vmName})
    if vmresult2 != {} and vmresult1 != {}:
       currentVmCount = vmresult1['count'] + vmresult2['count']
       currentVmList = [[vm['id'],vm['name'],vm['state']] for vm in vmresult1['virtualmachine']] + [[vm['id'],vm['name'],vm['state']] for vm in vmresult2['virtualmachine']]
    elif vmresult1 != {}:
       currentVmCount = vmresult1['count']
       currentVmList = [[vm['id'],vm['name'],vm['state']] for vm in vmresult1['virtualmachine']]
    else:
       currentVmCount = 0
       currentVmList = []
    # sort list alphabetically by VM names
    currentVmList.sort(key=lambda x: x[1])
    write_logfile(logfile_handle, "Current virtual machines: %d" % currentVmCount)
    print("Current virtual machines: %d" % currentVmCount)
    print("VM list:")
    for v in currentVmList:
        print("%s: %s (state: %s)" % (v[0],v[1],v[2]))

    # STEP: Query to HAProxy VM statistics and extract the number of current sessions
    # Do this twice with a time gap to get a more reliable number
    haproxydata = requests.get(haproxyStatsURL, auth=(haproxyStatsUser, haproxyStatsPassword)).text
    currentSessions1 = float((haproxydata.split('\n')[1]).split(',')[4])
    time.sleep(10)
    haproxydata = requests.get(haproxyStatsURL, auth=(haproxyStatsUser, haproxyStatsPassword)).text
    currentSessions2 = float((haproxydata.split('\n')[1]).split(',')[4])
    currentSessionsCount = int(math.ceil(0.5*(currentSessions1 + currentSessions2)))
    write_logfile(logfile_handle, "Current web sessions: %d" % currentSessionsCount)
    print("Current web sessions: %d" % currentSessionsCount)

    # STEP: Calculate number of VMs required for current session loading
    if currentSessionsCount % sessionPerVM == 0:
       requiredVmCount = currentSessionsCount / sessionPerVM
    else:
       requiredVmCount = currentSessionsCount / sessionPerVM + 1

    # FOR TESTING: SET THIS VARIABLE TO OVERRIDE THE SESSION-BASED CALCULATION 
    ##requiredVmCount = 3

    if requiredVmCount > maxVM:
       requiredVmCount = maxVM
    if requiredVmCount < minVM:
       requiredVmCount = minVM

    changeVMNum = requiredVmCount - currentVmCount
    print("Required VMs (for target loading of %d sessions per VM): %d" % (sessionPerVM, requiredVmCount))
    print("Change to VMs: %d" % changeVMNum)

    # STEP: Create new VM, or delete VM, or no changes required
    if changeVMNum == 0:
       write_logfile(logfile_handle, "No changes to VMs required.")
       print("No changes to VMs required.")
    elif changeVMNum > 0:
       write_logfile(logfile_handle, "Creating %d VMs now..." % changeVMNum)
       print("Creating %d VMs now..." % changeVMNum)
       timeNow = datetime.datetime.utcnow()
       timestamp = timeNow.strftime("%Y%m%dT%H%M%S")
       newVmDict = {}
       for i in range(changeVMNum):
          vmNewName = vmName + timestamp + '-' + "%03d" % (i+1)
          print("  creating: %s" % vmNewName)
          newVmDict[vmNewName] = {}
          try:
              deployResult = api.deployVirtualMachine({'region':vdcRegion, 'name':vmNewName, 'displayname':vmNewName, 'zoneid': zoneID, 'templateid': templateID, 'serviceofferingid': serviceofferingID, 'networkids': networkIDs}) 
              newVmDict[vmNewName]['deployjobid'] = deployResult['jobid']
              newVmDict[vmNewName]['deploycomplete'] = False
          except:
              write_logfile(logfile_handle, "ERROR while trying to deploy VM %s. Carrying on but results may not be correct." % vmNewName)
              pass
       # NEED TO WAIT FOR DEPLOYS TO COMPLETE SO THAT NEW VMs' IP ADDRESSES ARE AVAILABLE TO HAPROXY CONFIG 
       checkDelay = 2
       displayProgress = True
       deployAllComplete = False
       countdown = len(newVmDict)
       deployStartTime = datetime.datetime.utcnow()
       while not deployAllComplete:
          for v in newVmDict: 
              if not newVmDict[v]['deploycomplete']:
                 try:
                    result = api.queryAsyncJobResult({'region': vdcRegion, 'jobid': newVmDict[v]['deployjobid']})
                 except KeyError:
                    pass
                 elapsedTime = (datetime.datetime.utcnow() - deployStartTime).seconds
                 if 'jobresult' in result:
                    countdown = countdown - 1
                    newVmDict[v]['deploycomplete'] = True
                    print('')
                    print("VM deploy completed: %s. %d deploys left to complete." % (v, countdown))
                 elif elapsedTime > deploy_timeout:
                    countdown = countdown - 1
                    newVmDict[v]['deploycomplete'] = True
                    print('')
                    print("TIMEOUT for VM %s: deploy took too long. %d deploys left to complete." % (v, countdown))
          if countdown == 0:
              deployAllComplete = True
              write_logfile(logfile_handle, "Finished the deployment of virtual machines.")
              print("Finished the deployment of virtual machines.")
          else:
              if displayProgress:
                 print('.', end='')
                 sys.stdout.flush()
              time.sleep(checkDelay)       
    elif changeVMNum < 0:
       write_logfile(logfile_handle, "Deleting %d VMs now..." % abs(changeVMNum)) 
       print("Deleting %d VMs now..." % abs(changeVMNum)) 
       for i in range(abs(changeVMNum)):
          print("  deleting: %s" % currentVmList[i][1])
          try:
              api.destroyVirtualMachine({'region':vdcRegion, 'id': currentVmList[i][0], 'expunge':True})
          except:
              write_logfile(logfile_handle, "ERROR while trying to destroy VM %s. Carrying on but results may not be correct." % currentVmList[i][1])
              pass
       # Pause so that the deleted VMs have time to switch off, and won't be detected at the next step
       time.sleep(30)
       write_logfile(logfile_handle, "Finished deleting virtual machines.") 

    # STEP: Rewrite the HAProxy config file if there is a change
    if changeVMNum != 0:
       # Get network IP addresses for currently running VMs
       vmresult = api.listVirtualMachines({'region': vdcRegion, 'zone': zoneID, 'state': 'Running', 'name': vmName})
       vmAddressList = [[vm['name'].replace('-','').lower(), [net for net in vm['nic'] if net['networkid']==networkIDs.split(',')[0]][0]['ipaddress']] for vm in vmresult['virtualmachine']]
       vmAddressList.sort(key=lambda x: x[0])
       with open(haproxyConfigFileStatic) as fh:
          haproxyConfigStatic = fh.read()
       with open(haproxyConfigFile, 'w') as outfh:
          outfh.write(haproxyConfigStatic)
          for v in vmAddressList:
             outfh.write('\n        server %s %s:80 check' % (v[0], v[1]))
       write_logfile(logfile_handle, "New configuration written to config file %s" % haproxyConfigFile)
       print("New configuration written to config file %s" % haproxyConfigFile)

       # Restart the HAProxy service
       call(['sudo', 'service', 'haproxy', 'restart'])
       write_logfile(logfile_handle, "Service haproxy restarted.")
       print("Service haproxy restarted.")

    # STEP: Program finished
    write_logfile(logfile_handle, "Finished.\n\n")
    timeNow = datetime.datetime.utcnow()
    timestamp = timeNow.strftime("%Y-%m-%d %H:%M:%S UTC")
    print("********************************************")
    print("loadbased_autoscaler: Finished at %s" % timestamp)
    print("********************************************")

    # Autoscale loop finished, so wait 'repeat_interval' seconds
    time.sleep(float(repeat_interval))

    
