#! /usr/bin/env python
#
# Python script for the Interoute Virtual Data Centre API:
#   Name: cluster_destroy.py:
#   Purpose: Destroy a cluster of virtual machines created by cluster_deploy.py
#   Requires: class VDCApiCall in the file vdc_api_call.py
# See the repo: https://github.com/Interoute/API-fun-and-education
#
# You can pass options via the command line: type 'python cluster_destroy.py -h'
# for usage information
#
# Copyright (C) Interoute Communications Limited, 2016
#

from __future__ import print_function
import vdc_api_call as vdc
import getpass
import json
import os
import sys
import pprint
import argparse
import re
import time

if __name__ == '__main__':
    # STEP: Parse the command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default=os.path.join(os.path.expanduser('~'), '.vdcapi'),
                    help="path/name of the config file to be used for the API URL and API keys (default is ~/.vdcapi)")
    parser.add_argument("-f", "--filename", help="name of input file with the cluster setup information in JSON format")
    parser.add_argument("-x", "--expunge", action='store_true', help="expunge the virtual machines")
    config_file = parser.parse_args().config
    datafile = parser.parse_args().filename
    expunge = parser.parse_args().expunge
    
    # STEP: If config file is found, read its content,
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

    # STEP: Create the API access object
    api = vdc.VDCApiCall(api_url, apiKey, secret)

    # STEP: Load the cluster data from the JSON file
    with open(datafile) as json_file:
       zonesDict = json.load(json_file)

    # STEP: Check if VM exists (ie. not already deleted)
    zNotExist = []
    for z in zonesDict:
       if 'virtualmachineid' not in zonesDict[z].keys():
          vmName = "VM-" + re.sub('[ ()]','', zonesDict[z]['name']) + "-" + re.sub('[ ()]','', zonesDict[z]['clustername'])
          resultVmNameCheck = api.listVirtualMachines({'region':zonesDict[z]['region'], 'name':vmName})
          if resultVmNameCheck == {}:
             print("VM NOT FOUND in zone %s" % (zonesDict[z]['name']))
             zNotExist = zNotExist + [z]
             zonesDict[z]['virtualmachineid'] = 'MISSING'
          else:
             zonesDict[z]['virtualmachineid'] = resultVmNameCheck['virtualmachine'][0]['id']
             zonesDict[z]['deploycomplete'] = True
       elif api.listVirtualMachines({'region':zonesDict[z]['region'], 'id':zonesDict[z]['virtualmachineid']}) == {}:
           print("VM NOT FOUND OR ALREADY DELETED: %s in zone %s" % (zonesDict[z]['virtualmachineid'],zonesDict[z]['name']))
           zNotExist = zNotExist + [z]
    if set(zonesDict.keys())-set(zNotExist) == set([]):
       print("All VMs are already deleted. Nothing to do.")
       sys.exit("FATAL: Program terminating")
           
    # STEP: Confirm destruction of virtual machines
    print("These virtual machines are being setup for destruction:")
    for z in set(zonesDict.keys()) - set(zNotExist):
       print("  VM %s in zone %s" % (zonesDict[z]['virtualmachineid'],zonesDict[z]['name']))
    choice = raw_input("Input D to destroy the virtual machines, or any other key to exit:")
    if choice != "d" and choice != "D":
       sys.exit("FATAL: Program terminating")
        
    # STEP: Execute the API calls to destroy the virtual machines
    for z in set(zonesDict.keys()) - set(zNotExist):
       destroyparams = {'region':zonesDict[z]['region'], 'id':zonesDict[z]['virtualmachineid']}
       zonesDict[z]['destroycomplete'] = False
       if expunge:
          destroyparams['expunge'] = True
       try:
          destroyResult = api.destroyVirtualMachine(destroyparams)
          zonesDict[z]['destroyjobid'] = destroyResult['jobid']
       except:
          print("ERROR: Failure occurred in API call destroyVirtualMachine for VM %s" % zonesDict[z]['virtualmachineid'])
          pass

    # STEP: Monitor and wait for VM destruction to complete
    checkDelay = 2
    displayProgress = True
    destroyAllComplete = False
    countdown = len(zonesDict)
    while not destroyAllComplete:
       for z in set(zonesDict.keys()) - set(zNotExist):
          if zonesDict[z]['deploycomplete'] and not zonesDict[z]['destroycomplete']:
             try:
                result = api.queryAsyncJobResult({'region':zonesDict[z]['region'], 'jobid': zonesDict[z]['destroyjobid']})
             except KeyError:
                pass
             if 'jobresult' in result:
                countdown = countdown - 1
                zonesDict[z]['destroycomplete'] = True
                print('')
                print("VM %s destroyed in zone %s. %d zones left to compete." % (zonesDict[z]['virtualmachineid'],zonesDict[z]['name'],countdown))                
       if countdown == 0:
          destroyAllComplete = True
          print("Finished the destruction of virtual machines. Program terminating.")
       else:
          if displayProgress:
             print('.', end='')
             sys.stdout.flush()
          time.sleep(checkDelay)
        



