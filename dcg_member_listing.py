#! /usr/bin/env python
# Python script for the Interoute Virtual Data Centre API:
#   Name: dcg_member_listing.py
#   Purpose: List the properties and membership of Direct Connect Groups
#   Requires: class VDCApiCall in the file vdc_api_call.py
# See the repo: https://github.com/Interoute/API-fun-and-education
#
# You can pass options via the command line: type 'python dcg_member_listing.py -h' for usage information
#
# The VDC account used must be able to access the VDC regions in the argument 'regionlist'.
# Use the regionlist argument to change the regions for a limited account (for example, a 14-day trial account is excluded from Asia region)
# Example of passing region names as arguments (do not use braces, quotes or commas): 'python dcg_member_listing.py --regionlist Europe USA -n'
#
# Copyright (C) Interoute Communications Limited, 2017

from __future__ import print_function
import vdc_api_call as vdc
import getpass
import json
import os
import string
import datetime
import argparse
import re

def print_network_members(vmList,networkid,isProvisioned,prefixChars):
   networkmembers = []
   for vm in vmList:
      for i in range(len(vm['nic'])):
         if networkid == vm['nic'][i]['networkid']:
            networkmembers.append([int(vm['nic'][i]['ipaddress'].split('.')[-1]),vm['nic'][i]['ipaddress'],vm['name'],vm['id']])
            break # Can break out of this loop as soon as the network id is found for a NIC 
   if len(networkmembers)>0:
      networkmembers.sort() # VMs will be sorted by the last segment of their IP address (=first element of each members list)
      for i in range(len(networkmembers)):
         if i==len(networkmembers)-1:  #this is last VM in the network
            print(prefixChars + unichr(0x2514)+" %s: '%s'" % (networkmembers[i][1],networkmembers[i][2]))
         else:
            print(prefixChars + unichr(0x251C)+" %s: '%s'" % (networkmembers[i][1],networkmembers[i][2]))
   else:
      if isProvisioned:
         print(prefixChars + "*(NO MEMBERS)")
      else:
         print(prefixChars + "*(NOT PROVISIONED)")


if __name__ == '__main__':
    # STEP 1: Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default=os.path.join(os.path.expanduser('~'), '.vdcapi'),
                    help="path/name of the config file to be used for the API URL and API keys")
    parser.add_argument("-n","--netmem",action='store_true',
                    help="show the VM members of the Private Direct Connect networks")
    parser.add_argument("-r","--regionlist",default=['Europe', 'USA', 'Asia'],nargs='+',
                    help="specify the list of regions to be checked")
    # Note : The VDC account used must be able to access all of the VDC regions in the argument 'regionlist'.
    # Use this argument to change the list for a limited account (for example, a 14-day trial account is excluded from Asia region)
    config_file = parser.parse_args().config
    show_netmem = parser.parse_args().netmem
    vdcRegions = parser.parse_args().regionlist

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
    dcgList = api.listDirectConnectGroups({})
    networksLists = {}
    if show_netmem:
       vmLists = {}
    for r in vdcRegions:
       nlistPDC = api.listNetworks({'region': r, 'subtype': 'privatedirectconnect'})
       nlistPDCEgress = api.listNetworks({'region': r, 'subtype': 'privatedirectconnectwithgatewayservicesegress'})
       if nlistPDC['count'] == 0 and nlistPDCEgress['count'] == 0: # there are no PrivateDirectConnect networks in this region
          networksLists[r] = {'count':0, 'network':[]}
       else:
          networksLists[r] = {'count': nlistPDC['count'] + nlistPDCEgress['count'], 'network': nlistPDC['network'] + nlistPDCEgress['network']}
       if show_netmem:
          zonesResponse = api.listZones({'region':r})
          zonesList = [z['name'] for z in zonesResponse['zone']]
          vmRawList = api.listVirtualMachines({'region':r}) 
          for z in zonesList:
              try:
                  vmLists[z] = [v for v in vmRawList['virtualmachine'] if v['zonename']==z]
              except KeyError:  # there are no VMs in this region so lookup in the dict will fail
                  vmLists[z] = []
              

    # STEP 5: Process the information from the API calls
    try:
        checkTime = datetime.datetime.utcnow() # get the current time (UTC = GMT)
        print("\nDirect Connect Groups for the account '%s' checked at %s:"
            % (api.getApiLimit({})['apilimit']['account'], checkTime.strftime("%Y-%m-%d %H:%M:%S UTC")))
        if len(vdcRegions)==3:
            print("\n** All VDC regions are being scanned for Private Direct Connect networks")
        else:
            print("\n** Only these regions will be scanned and their Private Direct Connect networks shown: %s" % (vdcRegions))
        print("\n** Networks which have 'isprovisioned' set to False are labelled with '/NotProv/' and are not functional")
        print("** Output may not be correct for DCGs and networks that were not created with NetworkAPI functions because\n** they may be missing the information in the listNetworks call which identifies the DCG membership of the network.")
        print("** (+E) denotes networks with gateway services for Internet egress\n")
        for d in dcgList['directconnectgroups']:
            print(" "+unichr(0x2015)+' \'%s\' (dcgid: %s)' % (d['name'], d['id']))
            members = []
            for r in vdcRegions:
               if networksLists[r]['network'] != []:
                  for n in networksLists[r]['network']:
                      if n['dcgfriendlyname'] == d['name']:
                         if 'isprovisioned' not in n:
                            n['isprovisioned'] = 'Unknown'
                         members.append([n['cidr'],n['name'],n['zonename'],r,n['id'],n['isprovisioned'],n['displaytext'],n['subtype']])
            if len(members)>0:
                members = sorted(members, key=lambda x: x[2]) #sort by zonename
                members = sorted(members, key=lambda x: x[3]) #sort by region
                for i in range(len(members)):
                    if members[i][7] == 'privatedirectconnectwithgatewayservicesegress':
                       egressLabel = " (+E)"
                    else:
                       egressLabel = ""
                    if members[i][5] == True:
                       provisionedLabel = ""
                    elif members[i][5] == False:
                       provisionedLabel = "/NotProv/ "
                    elif members[i][5] == 'Unknown':
                       provisionedLabel = "/ProvUnknown/ "
                    if i==len(members)-1:  #if this is last item in list
                       if members[i][1] != members[i][6]: #if network 'name' and 'displaytext' are not the same
                          print("   "+unichr(0x2514)+" %s%s: %s'%s'|'%s' (%s, %s)" % (members[i][0],egressLabel,provisionedLabel,members[i][1],members[i][6],members[i][2],members[i][3]))
                       else:
                          print("   "+unichr(0x2514)+" %s%s: %s'%s' (%s, %s)" % (members[i][0],egressLabel,provisionedLabel,members[i][1],members[i][2],members[i][3]))
                       if show_netmem:
                           if vmLists[members[i][2]] != {}:
                              print_network_members(vmLists[members[i][2]],members[i][4],members[i][5],"        ")
                           else:
                              print("        " + "*(NO MEMBERS)")
                    else:
                       if members[i][1] != members[i][6]: #if network 'name' and 'displaytext' are not the same
                          print("   "+unichr(0x251C)+" %s%s: %s'%s'|'%s' (%s, %s)" % (members[i][0],egressLabel,provisionedLabel,members[i][1],members[i][6],members[i][2],members[i][3]))
                       else:
                          print("   "+unichr(0x251C)+" %s%s: %s'%s' (%s, %s)" % (members[i][0],egressLabel,provisionedLabel,members[i][1],members[i][2],members[i][3]))
                       if show_netmem:
                           if vmLists[members[i][2]] != {}:
                              print_network_members(vmLists[members[i][2]],members[i][4],members[i][5],"   "+unichr(0x2502)+"    ")
                           else:
                              print("        " + "*(NO MEMBERS)")
                print(" ")
            else:
                print("   *(NO NETWORKS)")
            print(" ")

    except KeyError:
        print("Exception: KeyError")
        ##print('Nothing to do: No Direct Connect Groups found')
