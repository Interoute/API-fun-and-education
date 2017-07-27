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
##import vdc_api_call as vdc
##import getpass
import json
import os
import sys
import pprint
import argparse
import re
import numpy as np
#import time

# STEP: Parse the command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("-f", "--filename", help="name of input file with the cluster setup information in JSON format")
parser.add_argument("-s", "--summaryonly", action='store_true', help="Only output the summary statistics (number_VM, max, min, range, mean, median)")
datafile = parser.parse_args().filename
outputSummaryOnly = parser.parse_args().summaryonly
    
# STEP: Load the cluster data from the JSON file
with open(datafile) as json_file:
   zonesDict = json.load(json_file)

# STEP: Extract the 'created' and 'deploytime' data
deployTimeList = []
if not outputSummaryOnly:
   print("%s, %s, %s, %s, %s" % ("VDC_zone", "VM_created_datetime", "VM_deploytime", "VM_created_date", "VM_created_time"))    
for z in zonesDict:
   if 'created' in zonesDict[z].keys():
      if zonesDict[z]['created'] != "NA":
         zonesDict[z]['createddate'] = zonesDict[z]['created'].split('T')[0]
         zonesDict[z]['createdtime'] = zonesDict[z]['created'].split('T')[1].split('+')[0]
      else:
         zonesDict[z]['createddate'] = "NA"
         zonesDict[z]['createdtime'] = "NA"
      if not outputSummaryOnly:
         print("%s, %s, %d, %s, %s" % (re.sub('[ ()]','', zonesDict[z]['name']), zonesDict[z]['created'], zonesDict[z]['deploytime'],  zonesDict[z]['createddate'], zonesDict[z]['createdtime']))
      deployTimeList += [zonesDict[z]['deploytime']]
   else:
      if not outputSummaryOnly:
         print("%s, %s, %s, %s, %s" % (re.sub('[ ()]','', zonesDict[z]['name']), "NA", "NA", "NA", "NA"))

data = np.array(deployTimeList)
if not outputSummaryOnly:
   print("\nSUMMARY STATISTICS:\nN, MIN, MAX, RANGE, MEAN, MEDIAN")
print("%s, %s, %s, %s, %s, %s" % (len(deployTimeList), np.nanmin(data), np.nanmax(data), np.ptp(data), np.nanmean(data), np.median(data)))
