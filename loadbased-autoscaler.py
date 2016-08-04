#! /usr/bin/env python
# Python script for the Interoute Virtual Data Centre API:
#   Name: loadbased-autoscaler.py
#   Purpose: Perform autoscaling of webserver virtual machines in VDC based on loading of an HAProxy frontend server
#   Requires: class VDCApiCall in the file vdc_api_call.py
# See the repo: https://github.com/Interoute/API-fun-and-education
#
# You can pass options via the command line: type 'python loadbased-autoscaler.py -h'
# for usage information
#
# Based on original VDC design and Perl script by Stefan Bienek
#
# Copyright (C) Interoute Communications Limited, 2016

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

if __name__ == '__main__':
    # STEP 1: Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default=os.path.join(os.path.expanduser('~'), '.vdcapi'),
                    help="path/name of the config file to be used for the API URL and API keys (default is ~/.vdcapi)")
    parser.add_argument("-r", "--region", choices=['Europe','europe','USA','usa','Asia','asia'],
                    default='Europe', help="specify the VDC region: Europe, USA or Asia (default Europe)")
    ##parser.add_argument("-w", "--writediag", action='store_true', help="write a diag file for use with nwdiag")
    ##parser.add_argument("-f", "--diagfile", default='VDC-network-data.diag',
    ##                help="name of the output diag file for use with nwdiag")
    ##parser.add_argument("-z", "--zone", help="filter results by zone name (match by initial characters) ")
    ##parser.add_argument("-v", "--vmstate", action='store_true', help="display VM state by text colour")
    vdcRegion = parser.parse_args().region
    ##writeDiag = parser.parse_args().writediag
    config_file = parser.parse_args().config
    ##zonenameFilter = parser.parse_args().zone
    ##showVmState =  parser.parse_args().vmstate
    ##if writeDiag:
    ##   diagfileName = parser.parse_args().diagfile

    # TEMPORARY: Hard configuration settings
    haproxyStatsURL = 'http://213.39.4.189:8080/haproxy?stats;csv'
    haproxyStatsUser = 'stats'
    haproxyStatsPassword = '132stats'
    zoneID = '7144b207-e97e-4e4a-b15d-64a30711e0e7'
    templateID = '524f0b99-f811-446c-bde2-31df4ba0378c'
    serviceofferingID = '4cb92069-e001-4637-8848-76d74f406bb8'
    networkIDs = '86af9d6d-0ed2-4b4b-a2ae-30b061e3524d'
    # naming convention for VMs, a date and random digits will be added
    vmName = 'Webcluster-'   
    # min and max numbers of VMs to run
    maxVM = 10			
    minVM = 1
    # max allowed loading of cluster is a number of web sessions per VM
    sessionPerVM = 5		

    # STEP 2: If config file is found, read its content,
    # else query user for the URL, API key, Secret key
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

    # STEP: Create the api access object for VDC
    api = vdc.VDCApiCall(api_url, apiKey, secret)

    # STEP: Check the number of running VMs
    vmresult = api.listVirtualMachines({'region': vdcRegion, 'zone': zoneID, 'state': 'Running', 'name': vmName})
    ## Probably need to also add VMs with state=Starting because the VM deploy time could be longer than the run frequency of this script
    currentVmCount = vmresult['count']
    currentVmList = [[vm['id'],vm['name']] for vm in vmresult['virtualmachine']]
    print("Current virtual machines: %d" % currentVmCount)
    print("VM list:")
    for v in currentVmList:
        print("%s: %s" % (v[0],v[1]))
    
    # STEP: Query to HAProxy VM statistics and extract the number of current sessions
    # Do this twice to get a more reliable number
    haproxydata = requests.get(haproxyStatsURL, auth=(haproxyStatsUser, haproxyStatsPassword)).text
    currentSessions1 = float((haproxydata.split('\n')[1]).split(',')[4])
    time.sleep(10)
    haproxydata = requests.get(haproxyStatsURL, auth=(haproxyStatsUser, haproxyStatsPassword)).text
    currentSessions2 = float((haproxydata.split('\n')[1]).split(',')[4])
    currentSessionsCount = int(math.ceil(0.5*(currentSessions1 + currentSessions2)))
    print("Current web sessions: %d" % currentSessionsCount)

    # STEP: Calculate number of VMs required for current session loading
    if currentSessionsCount % sessionPerVM == 0:
       requiredVmCount = currentSessionsCount / sessionPerVM
    else:
       requiredVmCount = currentSessionsCount / sessionPerVM + 1

    if requiredVmCount > maxVM:
       requiredVmCount = maxVM
    if requiredVmCount < minVM:
       requiredVmCount = minVM

    print("Required VMs (for %d sessions per VM): %d" % (sessionPerVM, currentSessionsCount))
        
    changeVMNum = requiredVmCount - currentVmCount

    print("Change to VMs: %d" % changeVMNum)

    if changeVMNum == 0:
       print("No changes to VMs required. Stopping script")
    ##elif changeVMNum > 0:
       
       
    # STEP: 
    
'''
if(($currentvms < $tobevms) and ($currentvms < $maxvms)) {
	$addvms = $tobevms-$currentvms;
	print "Increasing VM amount plus $addvms\n";
	for (my $n=1;$n<=$addvms;$n++) {
		my $randomnr = int(rand(8999)+1000);
		my $command = "$cloudmonkey deploy virtualmachine name=$vmname$randomnr displayname=$vmname$randomnr zoneid=$zoneid serviceofferingid=$serviceofferingid templateid=$templateid networkids=$networkid > \/dev\/null 2>\&1";
		# print "$command \n";
		my $pid = fork();
		if (defined $pid && $pid == 0) {
			close STDIN;
			close STDOUT;
    			exec($command);
    			exit 0;
		}
	}
} elsif (($currentvms > $tobevms) and ($currentvms > $minvms)) {
	$decvms = $currentvms-$tobevms;
	print "Decreasing VM amount by $decvms\n";
	for (my $n=1;$n<=$decvms;$n++) {
		my $command = "$cloudmonkey stop virtualmachine id=$existingvms[$n-1] >\/dev\/null 2>\&1;$cloudmonkey destroy virtualmachine expunge=true id=$existingvms[$n-1] >\/dev\/null 2>\&1;$cloudmonkey stop virtualmachine id=$existingvms[$n-1] >\/dev\/null 2>\&1;$cloudmonkey destroy virtualmachine expunge=true id=$existingvms[$n-1] >\/dev\/null 2>\&1";
		# print "$command\n";
		my $pid = fork();
		if (defined $pid && $pid == 0) {
			close STDIN;
			close STDOUT;
			exec($command);
			exit 0;
		}
	}
} else {
	print "Nothing to do\n";
}

print "################################\n";

'''
