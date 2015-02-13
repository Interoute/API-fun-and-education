#! /usr/bin/env python
# Python script for the Interoute Virtual Data Centre API:
#   Name: networks_member_listing-v2.py
#   Purpose: List the networks in a VDC with the VMs belonging to each network
#   Requires: class VDCApiCall in the file vdc_api_call.py
# See the repo: https://github.com/Interoute/API-fun-and-education   
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

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default=os.path.join(os.path.expanduser('~'), '.vdcapi'),
                    help="path/name of the config file to be used for the API URL and API keys")
    parser.add_argument("-r", "--region", choices=['Europe','europe','USA','usa','Asia','asia'],
                    default='Europe', help="specify the VDC region (Europe, USA or Asia)")
    parser.add_argument("-f", "--diagfile", default='VDC-network-data.diag',
                    help="name of the output diag file for use with nwdiag")
    vdcRegion = parser.parse_args().region
    diagfileName = parser.parse_args().diagfile
    config_file = parser.parse_args().config

    # If config file is found, read its content,
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

    # Create the api access object
    api = vdc.VDCApiCall(api_url, apiKey, secret)

    #API calls to get the information about networks and VMs
    request = {'region': vdcRegion}
    networksList = api.listNetworks(request)
    vmList = api.listVirtualMachines(request)
    portForwardingRulesList = api.listPortForwardingRules(request)
                        

    nameStringSubs = string.maketrans(" -","__")

    try:
        diagfile = open(diagfileName, 'w')
        checkTime = datetime.datetime.utcnow() # get the current time (UTC = GMT)
        diagfile.write('nwdiag {\n internet [shape=cloud]\n VDC [shape=cloud] \n internet -- VDC\n')
        print("\nNetwork configuration for the account '%s' in VDC region '%s' checked at %s:" 
            % (vmList['virtualmachine'][0]['account'],vdcRegion,checkTime.strftime("%Y-%m-%d %H:%M:%S UTC")))
        for network in networksList['network']:
            print(" "+unichr(0x2015)+' \'%s\' (Zone: %s, CIDR: %s' % (
                network['name'],
                network['zonename'],
                network['cidr']
            ), end='')
            #FIND EXTERNAL IP ADDRESS IF EXISTS
            testdict=request
            testdict['associatednetworkid']=network['id']
            external_IP=api.listPublicIpAddresses(testdict)
            if external_IP != {}:
               print(", IP: %s)" % external_IP['publicipaddress'][0]['ipaddress'])
            else:
               print(")")
            members = []
            for vm in vmList['virtualmachine']:
                for i in range(len(vm['nic'])):
                    if network['id'] == vm['nic'][i]['networkid']:
                        members.append([int(vm['nic'][i]['ipaddress'].split('.')[-1]),vm['nic'][i]['ipaddress'],vm['name'],vm['id']])
                        break # Can break out of this loop as soon as the network id is found for a NIC 
            if len(members)>0:
                #For nwdiag, network name has zone city appended (this is necessary because default VDC network names are same in all zones
                diagfile.write('network %s_Z_%s {\n address=\"%s\"\n' % (str(network['name']).translate(nameStringSubs),
                       network['zonename'].split()[0], network['cidr']))
                if external_IP != {}:
                    diagfile.write(' VDC [address=\"IP %s\"]\n' % (external_IP['publicipaddress'][0]['ipaddress']))
                members.sort() # VMs will be sorted by the last segment of their IP address (=first element of each members list)
                for i in range(len(members)):
                    if i==len(members)-1:  #this is last VM in the network
                       print("   "+unichr(0x2514)+" %s: '%s'" % (members[i][1],members[i][2]), end='')
                    else:
                       print("   "+unichr(0x251C)+" %s: '%s'" % (members[i][1],members[i][2]), end='')
                    if external_IP != {}:
                       #check for port forwarding rules
                       if portForwardingRulesList != {}: # Test if any port-forwarding rules exist
                          pfRules = [p for p in portForwardingRulesList['portforwardingrule'] if 
                              p['virtualmachineid']==members[i][3] and p['ipaddress']==external_IP['publicipaddress'][0]['ipaddress']]
                       else:
                          pfRules = []
                       if pfRules != []:
                          print(" (ports:",end='')
                          for p in pfRules:
                              if p['publicport']!=p['publicendport']:
                                 print(" [%s/%s]->"%(p['publicport'],p['publicendport']),end='')
                              else:
                                 print(" [%s]->"%(p['publicport']),end='')
                              if p['privateport']!=p['privateendport']:
                                 print("[%s/%s]"%(p['privateport'],p['privateendport']),end='')
                              else:
                                 print("[%s]"%(p['privateport']),end='')
                          print(")",end='')
                    print(" ")
                    diagfile.write('\"%s\" [address=\"%s\"];\n' % (str(members[i][2]).translate(nameStringSubs),members[i][1]))
                diagfile.write('}\n')
            else:
                print("   *(NO MEMBERS)")
            print(" ")
        diagfile.write("}\n")
        diagfile.close()
                
    except KeyError:
        # if no network, " networksList['network'] " will raise exception
        # but any other failure of API calls will also raise this exception!?
        print('Nothing to do: No networks found')
