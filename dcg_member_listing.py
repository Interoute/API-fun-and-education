#! /usr/bin/env python
# Python script for the Interoute Virtual Data Centre API:
#   Name: dcg_member_listing.py
#   Purpose: List the properties and membership of Direct Connect Groups
#   Requires: class VDCApiCall in the file vdc_api_call.py
# See the repo: https://github.com/Interoute/API-fun-and-education
#
# You can pass options via the command line: type 'python dcg_member_listing.py -h'
# for usage information
#
# Copyright (C) Interoute Communications Limited, 2015

from __future__ import print_function
import vdc_api_call as vdc
import getpass
import json
import os
import string
import datetime
import argparse
import re

if __name__ == '__main__':
    # STEP 1: Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default=os.path.join(os.path.expanduser('~'), '.vdcapi'),
                    help="path/name of the config file to be used for the API URL and API keys")
    ##parser.add_argument("-f", "--diagfile", default='VDC-network-data.diag',
    ##                help="name of the output diag file for use with nwdiag")
    ##parser.add_argument("-z", "--zone",help="filter results by zone name (match by initial characters) ")
    ##diagfileName = parser.parse_args().diagfile
    config_file = parser.parse_args().config
    ##zonenameFilter = parser.parse_args().zone

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

    # STEP 3: Create the api access object
    api = vdc.VDCApiCall(api_url, apiKey, secret)

    # STEP 4: API calls to get the information about DCGs and networks
    vdcRegions = ['Europe', 'USA', 'Asia']
    dcgList = api.listDirectConnectGroups({})
    networksLists = {}
    for r in vdcRegions:
       networksLists[r] = api.listNetworks({'region': r, 'subtype': 'privatedirectconnect'})

    ##if zonenameFilter:
    ##   networksList['network'] = [network for network in networksList['network'] if re.search('\A'+zonenameFilter,network['zonename'])]

    # STEP 5: Process the information from the API calls
    try:
        checkTime = datetime.datetime.utcnow() # get the current time (UTC = GMT)
        print("\nDirect Connect Groups for the account '%s' checked at %s:" 
            % (networksLists['Europe']['network'][0]['account'], checkTime.strftime("%Y-%m-%d %H:%M:%S UTC")))
        for d in dcgList['directconnectgroups']:
            print(" "+unichr(0x2015)+' \'%s\' (dcgid: %s' % (
                d['name'],
                d['id']
            ), end='') 
            members = []
            for r in vdcRegions:
               for n in networksLists[r]['network']:
                  if n['dcgfriendlyname'] == d:
                     members.append([n['cidr'],n['name'],n['zonename'],r])
            if len(members)>0:
                ##members.sort() # ?? to be sorted?
                for i in range(len(members)):
                    if i==len(members)-1:  #if this is last item in list 
                       print("   "+unichr(0x2514)+" %s: '%s' (%s, $s)" % (members[i][0],members[i][1],members[i][2],members[i][3]), end='')
                    else:
                       print("   "+unichr(0x251C)+" %s: '%s' (%s, $s)" % (members[i][0],members[i][1],members[i][2],members[i][3]), end='')
                print(" ")
             else:
                print("   *(NO MEMBERS)")
            print(" ")
                
    except KeyError:
        print('Nothing to do: No Direct Connect Groups found')
