#! /usr/bin/env python
#
# Python script for the Interoute Virtual Data Centre API:
#   Name: cluster_check_deploytime.py:
#   Purpose: Get the deploy time information from the JSON data for a cluster of virtual machines, output by cluster_deploy.py
#   Requires: class VDCApiCall in the file vdc_api_call.py
# See the repo: https://github.com/Interoute/API-fun-and-education
#
# You can pass options via the command line: type 'python cluster_check_deploytime.py -h'
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
#import time

# STEP: Parse the command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", default=os.path.join(os.path.expanduser('~'), '.vdcapi'),
                help="path/name of the config file to be used for the API URL and API keys (default is ~/.vdcapi)")
parser.add_argument("-f", "--filename", help="name of input file with the cluster setup information in JSON format")
##parser.add_argument("-x", "--expunge", action='store_true', help="expunge the virtual machines (otherwise they will put into Destroyed state)")
config_file = parser.parse_args().config
datafile = parser.parse_args().filename
##expunge = parser.parse_args().expunge
    
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

# STEP: Extract the 'created' and 'deploytime' data
print("%s, %s, %s, %s, %s" % ("VDC_zone", "VM_created_datetime", "VM_deploytime", "VM_created_date", "VM_created_time"))    
for z in zonesDict:
   if 'created' in zonesDict[z].keys():
      if zonesDict[z]['created'] != "NA":
         zonesDict[z]['createddate'] = zonesDict[z]['created'].split('T')[0]
         zonesDict[z]['createdtime'] = zonesDict[z]['created'].split('T')[1].split('+')[0]
      else:
         zonesDict[z]['createddate'] = "NA"
         zonesDict[z]['createdtime'] = "NA"
      print("%s, %s, %d, %s, %s" % (re.sub('[ ()]','', zonesDict[z]['name']), zonesDict[z]['created'], zonesDict[z]['deploytime'],  zonesDict[z]['createddate'], zonesDict[z]['createdtime']))
   else:
      print("%s, %s, %s, %s, %s" % (re.sub('[ ()]','', zonesDict[z]['name']), "NA", "NA", "NA", "NA"))
