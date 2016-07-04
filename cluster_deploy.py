#! /usr/bin/env python
#
# Python script for the Interoute Virtual Data Centre API:
#   Name: cluster_deploy.py:
#   Purpose: Deploy a cluster of virtual machines across a specified set of VDC zones, 1 VM per zone, with private direct connect networking 
#   Requires: class VDCApiCall in the file vdc_api_call.py
# See the repo: https://github.com/Interoute/API-fun-and-education
#
# You can pass options via the command line: type 'python cluster_deploy.py -h'
# for usage information
#
# Copyright (C) Interoute Communications Limited, 2016
#
# References:
#   stackoverflow.com/questions/5105517/deep-copy-of-a-dict-in-python
#   stackoverflow.com/questions/3939361/remove-specific-characters-from-a-string-in-python
#   

from __future__ import print_function
from collections import OrderedDict
from copy import deepcopy
import base64
import vdc_api_call as vdc
import getpass
import json
import os
import sys
import pprint
import time
import datetime
import textwrap
import argparse
import urllib
import urllib2
import hashlib
import hmac
import ipaddress
from netaddr import *
import re
import random

if __name__ == '__main__':
    # STEP: Parse the command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default=os.path.join(os.path.expanduser('~'), '.vdcapi'),
                    help="path/name of the config file to be used for the API URL and API keys (default is ~/.vdcapi)")
    parser.add_argument("-n", "--clustername", default="DEFAULT", help="name of the cluster to be deployed (default is 'CLUSTER-' + creation time)")
    parser.add_argument("-d", "--dcgid", default=-1, help="ID of the Direct Connect Group to be used for private networking")
    parser.add_argument("-t", "--templatename", help="Name of the virtual machine template (it must be available in all of the deployment zones!)")
    parser.add_argument("-s", "--serviceoffering", default='1024-1',
                        help="Name of the service offering ('RAM-CPU' same format as given by listServiceOfferings; default='1024-1')")
    parser.add_argument("-a", "--allzones", action='store_true', help="deploy cluster in all regions and all zones")
    parser.add_argument("-z", "--zones", nargs='+', help="list of zonenames where cluster is to be deployed (if -a is used, this input will be ignored)")
    parser.add_argument("-o", "--outfile", default="DEFAULT", help="name of output file to receive the cluster setup information (default is CLUSTERNAME.json)")
    parser.add_argument("-m", "--accessmode", choices=['single','all'], default='single',
                        help="specify the public Internet access mode: single VM with Internet or all VM with Internet (default: single)")
    parser.add_argument("-p", "--primaryzone", default="DEFAULT", help="name of zone which should be the access point for single-zone Internet access")
    parser.add_argument("-q", "--publicport", type=int, default=62200, help="Public SSH port to be assigned for the public Internet network(s)")
    parser.add_argument("-k", "--keypair", help="Keypair name (if it does not exist in VDC, a new keypair will be created)")
    parser.add_argument("-u", "--userdatafile", default='', help="filename for userdata to use in deployment")
    config_file = parser.parse_args().config
    dcgID = parser.parse_args().dcgid
    templateName = parser.parse_args().templatename
    serviceofferingName = parser.parse_args().serviceoffering
    clusterName = parser.parse_args().clustername
    if clusterName == 'DEFAULT':
       timeNow = datetime.datetime.utcnow()
       timestamp = timeNow.strftime("%Y%m%dT%H%M%S")
       clusterName = "CLUSTER-" + timestamp
    outfile = parser.parse_args().outfile
    if outfile == "DEFAULT":
       outfile = clusterName + ".json"
    allZonesDeploy = parser.parse_args().allzones
    # if allZonesDeploy is True, the zonesList is not used
    zonesListInput = parser.parse_args().zones
    primaryZone = parser.parse_args().primaryzone
    publicPort = parser.parse_args().publicport
    accessMode = parser.parse_args().accessmode
    keypairName = parser.parse_args().keypair
    userdataFilename = parser.parse_args().userdatafile

    # Check if dcgid was input
    if dcgID==-1:
       print("ERROR: Direct Connect Group ID was not input")
       sys.exit("FATAL: Program terminating")

    # Check if zones list has been input
    if (not allZonesDeploy) and zonesListInput==[]:
       print("ERROR: List of zones was not input and allZonesDeploy=False")
       sys.exit("FATAL: Program terminating")
    
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

    # Check if dcgID is a valid DCG - otherwise exit
    dcgConfigTest = api.listDirectConnectGroups({'id':dcgID})['directconnectgroups']
    if dcgConfigTest == []:
       print("ERROR: Direct Connect Group ID is not an existing DCG for the account in use")
       sys.exit("FATAL: Program terminating")
    else:
       dcgConfig = dcgConfigTest[0]
    
    vdcRegions = ['Europe', 'USA', 'Asia']
    allZonesDict = {}
    for r in vdcRegions:
       zlist = api.listZones({'region':r})['zone']
       for z in zlist:
          name1 = z['name']
          allZonesDict[name1] = {}
          allZonesDict[name1]['name'] = z['name']
          allZonesDict[name1]['region'] = r
          allZonesDict[name1]['id'] = z['id']
    if allZonesDeploy:
       zonesDict = deepcopy(allZonesDict)
       if primaryZone != "DEFAULT":
          zonesDict[primaryZone]['primary'] = True  ## primaryZone should be set False for all of the other zones
       else:
          pz = sorted(zonesDict.keys())[0]
          zonesDict[pz]['primary'] = True           ## primaryZone should be set False for all of the other zones
          primaryZone = pz
    else:
       zonesDict = {}
       for z in zonesListInput:
          zonesDict[z] = deepcopy(allZonesDict[z])
       pz = zonesListInput[0]
       zonesDict[pz]['primary'] = True
       primaryZone = pz

    ## TO DO: CHECK VALIDITY OF templateName, serviceofferingName, ....

    # STEP: Check and if required create private networks in the zones
    # If there is more than one private DC network in the zone and the DCG, then the first one is selected
    for z in zonesDict:
       zonesDict[z]['clustername'] = clusterName
       privateNetworksInZone = api.listNetworks({'subtype':'privatedirectconnect','zoneid':zonesDict[z]['id'],'region':zonesDict[z]['region']})['network']
       if privateNetworksInZone != []:
          privateNetworksInZoneAndDCG = [netdict for netdict in privateNetworksInZone if netdict['dcgid']==dcgID]
          if privateNetworksInZoneAndDCG != []:
             zonesDict[z]['privatenetworkid'] = privateNetworksInZoneAndDCG[0]['id']
             zonesDict[z]['privatecidr'] = privateNetworksInZoneAndDCG[0]['cidr']
             zonesDict[z]['privategateway'] = privateNetworksInZoneAndDCG[0]['gateway']
          else:
             zonesDict[z]['privatenetworkid'] = 'MISSING'
       else:
          privateNetworksInZoneAndDCG = []
          zonesDict[z]['privatenetworkid'] = 'MISSING'
    zmissing = [zonesDict[z1]['name'] for z1 in zonesDict if zonesDict[z1]['privatenetworkid']=='MISSING']
    print("Private networks found for DCG %s in these zones:" % dcgID)
    for z in set(zonesDict.keys()) - set(zmissing):
       print("   %s: %s, %s" % (zonesDict[z]['name'],zonesDict[z]['privatenetworkid'],zonesDict[z]['privatecidr']))
    if zmissing==[]:
       print("Private networks are complete for the cluster. Continuing to next step...")
    else:
       print("Private networks to be created for DCG %s in these zones:" % dcgID)      
       for z in zmissing:
          print("   %s" % (zonesDict[z]['name']))
       raw_input("Press any key to continue with private network creation...")
       # Private network creation...
       takenIP = []
       for z in set(zonesDict.keys()) - set(zmissing):
          takenIP = takenIP + [zonesDict[z]['privatecidr']]
       takenIPSet = IPSet(takenIP)
       privateIPSet = IPSet(['10.0.0.0/16'])
       availablePrivateIPSet = privateIPSet - takenIPSet
       availablePrivateIPSet = availablePrivateIPSet.iter_cidrs()
       availableSlash24IPSet = []
       for i in range(len(availablePrivateIPSet)):
	  availableSlash24IPSet += availablePrivateIPSet[i].subnet(24)
       # CIDRs for the new networks will be taken as a block from the list availableSlash24IPSet using a random starting position
       startPositionIPBlock = random.randint(0,len(availableSlash24IPSet)-len(zmissing))
       networkCreationNumber = 0
       for z in zmissing:
          networkCIDR = availableSlash24IPSet[startPositionIPBlock + networkCreationNumber]
          networkGateway = IPSet(networkCIDR).iter_cidrs()[0][-2] # this will be IP address 'X.X.X.254'
          print("Creating network %d for zone %s... [wait for response]" % (networkCreationNumber+1,zonesDict[z]['name']))
          try:
             createResult = api.createPrivateDirectConnect({'region':zonesDict[z]['region'], 'zonename':zonesDict[z]['name'], 'dcgid':dcgID,
                                                             'cidr':str(networkCIDR), 'gateway':str(networkGateway), 'displaytext':"Network-for-cluster-%s"%(clusterName)})
             networkID = createResult['privatedirectconnect'][0]['id']
             zonesDict[z]['privatenetworkid'] = createResult['privatedirectconnect'][0]['id']
             zonesDict[z]['privategateway'] = createResult['privatedirectconnect'][0]['gateway']
             zonesDict[z]['privatecidr'] = createResult['privatedirectconnect'][0]['cidr']
          except:
             print("ERROR: Exception occurred in creating private direct connect network for zone %s. Please check if network created correctly." % zonesDict[z]['name'])
             sys.exit("FATAL: Program terminating")
          print("Created network %d: id:%s, CIDR:%s, Gateway:%s" % (networkCreationNumber+1,networkID,networkCIDR,networkGateway))
          networkCreationNumber = networkCreationNumber + 1
       print("Finished the creation of private networks... continuing to next step")     
    
    # STEP: Check and if required create internet gateway networks in the zones
    for z in zonesDict:
       internetNetworksInZone = api.listNetworks({'subtype':'internetgateway','zoneid':zonesDict[z]['id'],'region':zonesDict[z]['region']})['network']
       if internetNetworksInZone != []:
          zonesDict[z]['internetnetworkid'] = internetNetworksInZone[0]['id']
          zonesDict[z]['internetcidr'] = internetNetworksInZone[0]['cidr']
          zonesDict[z]['internetgateway'] = internetNetworksInZone[0]['gateway']
          zonesDict[z]['publicport'] = publicPort
       else:
          zonesDict[z]['internetnetworkid'] = 'MISSING'
          zonesDict[z]['publicport'] = 'MISSING'
    zmissing = [zonesDict[z1]['name'] for z1 in zonesDict if zonesDict[z1]['internetnetworkid']=='MISSING']
    print("Internet Gateway networks found in these zones:")
    for z in set(zonesDict.keys()) - set(zmissing):
       print("   %s: %s, %s" % (zonesDict[z]['name'],zonesDict[z]['internetnetworkid'],zonesDict[z]['internetcidr']))
    if accessMode == 'single':
       # For accessMode single, there is only one Internet Gateway network required in primaryZone
       if primaryZone in zmissing:
          zmissingcreate = [primaryZone]
          print("Internet Gateway only to be created in the primary zone %s...." % zonesDict[primaryZone]['name'])
       else:
          zmissingcreate = []  
    else:
       zmissingcreate = zmissing
    if zmissingcreate==[]:
       print("Internet Gateway networks are complete for the cluster. Continuing to next step...")
    else:
       print("Internet Gateway networks to be created in these zones:")      
       for z in zmissingcreate:
          print("   %s" % (zonesDict[z]['name']))
       raw_input("Press any key to continue with Internet Gateway network creation...")
       # Internet Gateway network creation...
       networkCreationNumber = 0
       for z in zmissingcreate:
          takenIP = []
          for net in internetNetworksInZone:
             takenIP = takenIP + [net['cidr']]
          takenIPSet = IPSet(takenIP)
          internetIPSet = IPSet(['192.168.0.0/16'])
          availableInternetIPSet = internetIPSet - takenIPSet
          availableInternetIPSet = availableInternetIPSet.iter_cidrs()
          availableInternetSlash24IPSet = []
          for i in range(len(availableInternetIPSet)):
	     availableInternetSlash24IPSet += availableInternetIPSet[i].subnet(24)
          networkCIDR = random.choice(availableInternetSlash24IPSet)
          networkGateway = IPSet(networkCIDR).iter_cidrs()[0][-2] # this will be IP address 'X.X.X.254'
          print("Creating Internet Gateway network %d for zone %s... [wait for response]" % (networkCreationNumber+1,zonesDict[z]['name']))
          try:
             createResult = api.createLocalNetwork({'region':zonesDict[z]['region'], 'zonename':zonesDict[z]['name'],
                                                             'cidr':str(networkCIDR), 'gateway':str(networkGateway),
                                                             'displaytext':"InternetNetwork-for-cluster-%s"%(clusterName)})
             networkID = createResult['localnetwork'][0]['id']
             zonesDict[z]['internetnetworkid'] = createResult['localnetwork'][0]['id']
             zonesDict[z]['internetgateway'] = createResult['localnetwork'][0]['gateway']
             zonesDict[z]['internetcidr'] = createResult['localnetwork'][0]['cidr']
          except:
             print("ERROR: Exception occurred in creating internet gateway network for zone %s. Please check if network created correctly." % zonesDict[z]['name'])
             sys.exit("FATAL: Program terminating")
          print("Created network %d: id:%s, CIDR:%s, Gateway:%s" % (networkCreationNumber+1,networkID,networkCIDR,networkGateway))
          networkCreationNumber = networkCreationNumber + 1
       print("Finished the creation of Internet Gateway networks... continuing to next step")
    
    # STEP: Check and if required create SSH keypair
    # ... TO BE DONE ...
    
    # STEP: Load and prepare userdata
    # ... TO BE DONE ...
    
    # STEP: Check and record templateid for each zone based on templateName
    # Assumption is that a template with templateName exists in all required zones
    for z in zonesDict:
       try:
          zonesDict[z]['templateid'] = api.listTemplates({'region':zonesDict[z]['region'],'templatefilter':'executable', 'name':templateName, 'zoneid':zonesDict[z]['id']})['template'][0]['id']
       except:
          print("ERROR: Failure occurred in API call listTemplates for zone %s" % zonesDict[z]['name'])
          sys.exit("FATAL: Program terminating")
    
    # STEP: Check and record serviceofferingid for each zone based on serviceofferingName (this ID should be same for all zones within a region)
    for z in zonesDict:
       try:
          zonesDict[z]['serviceofferingid'] = api.listServiceOfferings({'region':zonesDict[z]['region'], 'name':serviceofferingName})['serviceoffering'][0]['id']
       except:
          print("ERROR: Failure occurred in API call listServiceOfferings for zone %s" % zonesDict[z]['name'])
          sys.exit("FATAL: Program terminating")

    # STEP: Check that all private networks are provisioned (ready to use) - otherwise pause until ready
    ## TO BE DONE!

    raw_input("READY TO DEPLOY VIRTUAL MACHINES. Press any key to continue...")
    # STEP: Deploy virtual machines in zones
    for z in zonesDict:
       zonesDict[z]['deploycomplete'] = False
       vmName = "VM-" + re.sub('[ ()]','', zonesDict[z]['name']) + "-" + re.sub('[ ()]','', clusterName)
       ##if zonesDict[z]['internetnetworkid'] != 'MISSING':
       if accessMode == 'single' and z != primaryZone:
          netIDs = zonesDict[z]['privatenetworkid']
       else:
          netIDs = zonesDict[z]['internetnetworkid'] + "," + zonesDict[z]['privatenetworkid']
          
       try:
          print("Executing deployVirtualMachine for zone %s" % zonesDict[z]['name'])
          deployResult = api.deployVirtualMachine({'region': zonesDict[z]['region'], 'zoneid':zonesDict[z]['id'],'templateid':zonesDict[z]['templateid'],'serviceofferingid':zonesDict[z]['serviceofferingid'],'name':vmName, 'displayname':vmName, 'networkids':netIDs, 'keypair':keypairName})
          zonesDict[z]['deployjobid'] = deployResult['jobid']
       except:
          print("ERROR: Failure occurred in API call deployVirtualMachine for zone %s" % zonesDict[z]['name'])
          zonesDict[z]['deployjobid'] = 'MISSING'
          choice = raw_input("Input C to continue with cluster deployment, or any other key to exit:")
          if choice == "C" or choice == "c":
             pass
          else:
             with open(outfile, 'w') as outf:
                 json.dump(zonesDict, outf)
             sys.exit("FATAL: Program terminating. JSON file is being output.")
             

    # STEP: Monitor and wait for VM deploys to complete
    checkDelay = 2
    displayProgress = True
    deployAllComplete = False
    countdown = len(zonesDict)
    while not deployAllComplete:
       for z in zonesDict:
          if zonesDict[z]['deployjobid'] != 'MISSING' and not zonesDict[z]['deploycomplete']:
             try:
                result = api.queryAsyncJobResult({'region':zonesDict[z]['region'], 'jobid': zonesDict[z]['deployjobid']})
             except KeyError:
                pass
             if 'jobresult' in result:
                countdown = countdown - 1
                zonesDict[z]['deploycomplete'] = True
                vmNics = result['jobresult']['virtualmachine']['nic']
                zonesDict[z]['privateipaddress'] = [net for net in vmNics if net['networkid']==zonesDict[z]['privatenetworkid']][0]['ipaddress']
                ##if zonesDict[z]['internetnetworkid'] != 'MISSING':
                if accessMode == 'single' and z != primaryZone:
                   zonesDict[z]['internetipaddress'] = 'MISSING'
                   zonesDict[z]['publicipaddress'] = 'MISSING'        
                else:
                   zonesDict[z]['internetipaddress'] = [net for net in vmNics if net['networkid']==zonesDict[z]['internetnetworkid']][0]['ipaddress']
                   ipdata = api.listPublicIpAddresses({'region':zonesDict[z]['region'], 'associatednetworkid':zonesDict[z]['internetnetworkid']})['publicipaddress'][0]
                   zonesDict[z]['publicipaddress'] = ipdata['ipaddress']
                   zonesDict[z]['publicipaddressid'] = ipdata['id']
                zonesDict[z]['virtualmachineid'] = result['jobresult']['virtualmachine']['id']
                zonesDict[z]['virtualmachinename'] = result['jobresult']['virtualmachine']['name']
                zonesDict[z]['keypair'] = result['jobresult']['virtualmachine']['keypair']
                print('')
                print("VM deploy completed in zone %s. %d zones left to complete." % (zonesDict[z]['name'],countdown))
          elif zonesDict[z]['deployjobid'] == 'MISSING':
             countdown = countdown - 1
             zonesDict[z]['deploycomplete'] = True
       if countdown == 0:
          deployAllComplete = True
          print("Finished the deployment of virtual machines. Continuing to next step...")
       else:
          if displayProgress:
             print('.', end='')
             sys.stdout.flush()
          time.sleep(checkDelay)        
    
    # STEP: Create portforwarding rules
    for z in zonesDict:
       ##if zonesDict[z]['internetnetworkid'] != 'MISSING':
       if accessMode != 'single' or (z == primaryZone and accessMode == 'single'):
          try:
             print("Executing createPortForwardingRule for zone %s" % zonesDict[z]['name'])
             pfResult = api.createPortForwardingRule({'region': zonesDict[z]['region'], 'zoneid':zonesDict[z]['id'], 'openfirewall':True, 'publicport':publicPort, 'privateport':22, 'protocol':'TCP', 'virtualmachineid':zonesDict[z]['virtualmachineid'], 'ipaddressid':zonesDict[z]['publicipaddressid']})
             zonesDict[z]['pfjobid'] = pfResult['jobid']
          except:
             print("ERROR: Failure occurred in API call createPortForwardingRule for zone %s" % zonesDict[z]['name'])
             pass


    print("Finished the creation of portforwarding rules. Continuing to next step...")
                                                        
    # STEP: Output cluster data in JSON format
    print(json.dumps(zonesDict))
    with open(outfile, 'w') as outf:
       json.dump(zonesDict, outf)
    print("Cluster configuration data written to output file. Program terminating.")



