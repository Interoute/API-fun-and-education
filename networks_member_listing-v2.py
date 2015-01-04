#! /usr/bin/env python
# Python script for the Interoute Virtual Data Centre API:
#   Name: networks_member_listing.py
#   Purpose: List the networks in a VDC with the VMs belonging to each network
#   Requires: class VDCApiCall in the file vdc_api_call.py
# See the repo: https://github.com/Interoute/API-fun-and-education   
#
# Copyright (C) Interoute Communications Limited, 2015

#TO DO: COMMAND LINE OPTIONS FOR:
#  region
#  Output diag file
#

from __future__ import print_function
import vdc_api_call as vdc
import getpass
import json
import os
import string
import datetime


if __name__ == '__main__':
    cloudinit_scripts_dir = 'cloudinit-scripts'
    config_file = os.path.join(os.path.expanduser('~'), '.vdcapi')
    if os.path.isfile(config_file):
        with open(config_file) as fh:
            data = fh.read()
            config = json.loads(data)
            api_url = config['api_url']
            apiKey = config['api_key']
            secret = config['api_secret']
            try:
                cloudinit_scripts_dir = config['cloudinit_scripts_dir']
            except KeyError:
                pass
    else:
        print('API url (e.g. http://10.220.18.115:8080/client/api):', end='')
        api_url = raw_input()
        print('API key:', end='')
        apiKey = raw_input()
        secret = getpass.getpass(prompt='API secret:')

    # Create the api access object
    api = vdc.VDCApiCall(api_url, apiKey, secret)

    #API calls to get the information about networks and VMs
    vdcRegion = 'Europe'
    request = {'region': vdcRegion}
    networksList = api.listNetworks(request)
    vmList = api.listVirtualMachines(request)
    portForwardingRulesList = api.listPortForwardingRules(request)

    nameStringSubs = string.maketrans(" -","__")

    try:
        diagfile = open('VDC-network-data.diag','w')
        checkTime = datetime.datetime.utcnow() # get the current time (UTC = GMT)
        diagfile.write('nwdiag {\n')
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
                diagfile.write('network %s {\n address=\"%s\"\n' % (str(network['name']).translate(nameStringSubs),network['cidr']))
                members.sort() # VMs will be sorted by the last segment of their IP address (=first element of each members list)
                for i in range(len(members)):
                    if i==len(members)-1:  #this is last VM in the network
                       print("   "+unichr(0x2514)+" %s: '%s'" % (members[i][1],members[i][2]), end='')
                    else:
                       print("   "+unichr(0x251C)+" %s: '%s'" % (members[i][1],members[i][2]), end='')
                    if external_IP != {}:
                       #check for port forwarding rules
                       ##for p in portForwardingRulesList['portforwardingrule']:
                           ##print( "check vm id: %s == %s (%s)   check ip: %s == %s (%s)" % (p['virtualmachineid'],members[i][3], p['virtualmachineid']==vm['id'],p['ipaddress'],external_IP['publicipaddress'][0]['ipaddress'],p['ipaddress']==external_IP['publicipaddress'][0]['ipaddress']))
                       pfRules = [p for p in portForwardingRulesList['portforwardingrule'] if p['virtualmachineid']==members[i][3] and p['ipaddress']==external_IP['publicipaddress'][0]['ipaddress']]
                       if pfRules != []:
                          print(" (ports:",end='')
                          for p in pfRules:
                              ##print(p)
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
        print('Nothing to do: No networks found')
