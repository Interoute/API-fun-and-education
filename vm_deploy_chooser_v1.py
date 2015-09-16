#! /usr/bin/env python
#
# Python script for the Interoute Virtual Data Centre API:
#   Name: vm_deploy_chooser.py:
#   Purpose: Chooser-based command line interface to deploy a virtual machine
#   Requires: class VDCApiCall in the file vdc_api_call.py
# See the repo: https://github.com/Interoute/API-fun-and-education
#
# VERSION 1 FROZEN 2015-09-16
#
# Copyright (C) Interoute Communications Limited, 2015
#
# Original code by Kelcey Damage, 2012 & Kraig Amador, 2012
# Revised by Sandy Walker (Interoute), 2013

from __future__ import print_function
import base64
import vdc_api_call as vdc
import getpass
import json
import os
import sys
import pprint
import time
import textwrap

try:
    import lxml.etree as xml
    xml_parser_imported = True
except ImportError:
    # We don't have lxml. Oh well- operate with reduced functionality
    xml_parser_imported = False

# Taken from https://bitbucket.org/maddagaska/maddautils/src/411cf3811f995de0ee6de000aed069f409afc719/__init__.py?at=master # noqa
# Offered under BSD license.

def choose_item_from_list(items,
                          source=sys.stdin,
                          dest=sys.stdout,
                          default='-',
                          prompt='Please select an item:'):
    # No item can be selected if there are no items
    if len(items) == 0:
        return -1

    # Use the default if we can- otherwise, make sure it's safe
    if default != '-' and (default in items or default == 'None'):
        if default == 'None':
            default = -1
        else:
            default = items.index(default)
    elif isinstance(default, int) and default in range(-1, len(items)):
        # The default is already an index in the list, or it is none
        # We don't need to do anything
        pass
    else:
        # If the default has been incorrectly set, or if it has not been set,
        # set it to nothing
        default = None

    # Ask the user to make a selection
    selection = None
    while selection is None:
        selection = default

        # Output the header
        dest.write('%s\n' % prompt)
        dest.write('0. None')
        if default == -1:
            # This is the default option
            dest.write(' (default)\n')
        else:
            dest.write('\n')

        # Output all of the items
        for item in range(0, len(items)):
            dest.write('%s. %s' % (item + 1, items[item],))
            if int(item) == default:
                # This is the default option
                dest.write(' (default)\n')
            else:
                dest.write('\n')

        dest.flush()

        response = source.readline().rstrip()

        if len(response) == 0:
            # No response given, prompt again
            # Otherwise it causes a problem with 'startswith' later
            continue

        try:
            # If the input is an integer we treat it as a selection
            # We don't try to match it to the text of a list item
            response = int(response)
            response -= 1
            if response in range(-1, len(items)):
                selection = response
            else:
                # Give helpful feedback
                response += 1
                dest.write('\n')
                dest.write('I do not have an item number %s.\n' % response)
                dest.write('\n')
                dest.flush()

        except ValueError:
            # It wasn't an integer. Did it match any items in the list?
            candidates = []
            for item in ['None'] + items:
                if item.startswith(response):
                    candidates.append(item)

            # If the selection is unambiguous, accept it as the choice
            if len(candidates) == 1:
                if 'None'.startswith(response):
                    selection = -1
                else:
                    for item in items:
                        if item.startswith(response):
                            selection = items.index(item)
            elif len(candidates) > 1:
                # The response was ambiguous, it could match multiple items
                dest.write('\n')
                dest.write('%s matches multiple items. ' % response)
                dest.write('Please be more specific.\n')
                dest.write('\n')
                dest.flush()
            else:
                # The named item wasn't in our list, give useful feedback
                dest.write('\n')
                dest.write('%s is not an option.\n' % response)
                dest.write('\n')
                dest.flush()

    return selection


if __name__ == '__main__':
    #cloudinit_scripts_dir = 'cloudinit-scripts'
    config_file = os.path.join(os.path.expanduser('~'), '.vdcapi')
    if os.path.isfile(config_file):
        with open(config_file) as fh:
            data = fh.read()
            config = json.loads(data)
            api_url = config['api_url']
            apiKey = config['api_key']
            secret = config['api_secret']
            #try:
            #    cloudinit_scripts_dir = config['cloudinit_scripts_dir']
            #except KeyError:
            #    pass
    else:
        print('API url (e.g. http://10.220.18.115:8080/client/api):', end='')
        api_url = raw_input()
        print('API key:', end='')
        apiKey = raw_input()
        secret = getpass.getpass(prompt='API secret:')

    api = vdc.VDCApiCall(api_url, apiKey, secret)


#STEP 1: CHOOSE REGION OR FIND ZONES FOR ALL REGIONS (THAT THE VDC ACCOUNT CAN ACCESS)..........................

    # Service offerings (CPU / RAM)
    # **** REPLACE THIS CODE ****
    request = {}
    result = api.listServiceOfferings(request)

    service_offering_ids = [offering['id']
                            for offering
                            in result['serviceoffering']]
    service_offering_names = [offering['displaytext']
                              for offering
                              in result['serviceoffering']]

    choice = -1
    while choice == -1:
        choice = choose_item_from_list(
            service_offering_names,
            prompt='Select your service offering:'
        )

        if choice == -1:
            print()
            print('Please select a service offering.')

    service_offering_id = service_offering_ids[choice]

    print('Using service offering: %s' % service_offering_id)
    # **** REPLACE THIS CODE ****

    request = {
        'available': 'true',
    }
    result = api.listZones(request)

    zone_ids = [zone['id']
                for zone
                in result['zone']]
    zone_names = [zone['name']
                  for zone
                  in result['zone']]

    choice = -1
    while choice == -1:
        choice = choose_item_from_list(
            zone_names,
            prompt='Select your zone:'
        )

        if choice == -1:
            print()
            print('Please select a zone.')

    zone_id = zone_ids[choice]

    print('Zone: %s' % zone_id)

    request = {
        'templatefilter': 'executable',
        'zoneid': zone_id,
    }
    result = api.listTemplates(request)

    # We have to filter out templates that are not ready. If we leave them in
    # and they are selected, an HTTP 530 error will occur.
    template_ids = [template['id']
                    for template
                    in result['template']
                    if template['isready']]
    template_names = [template['displaytext']
                      for template
                      in result['template']
                      if template['isready']]

    choice = -1
    while choice == -1:
        choice = choose_item_from_list(
            template_names,
            prompt='Select your template:'
        )

        if choice == -1:
            print()
            print('Please select a template.')

    template_id = template_ids[choice]

    print('Template: %s' % template_id)

    request = {
        'zoneid': zone_id,
    }
    result = api.listNetworks(request)

    network_ids = [network['id']
                   for network
                   in result['network']]
    network_names = [network['displaytext']
                     for network
                     in result['network']]

    choice = -1
    while choice == -1:
        choice = choose_item_from_list(
            network_names,
            prompt='Select your network:'
        )

        if choice == -1:
            print()
            print('Please select a network.')

    network_id = network_ids[choice]
    '''
    # Find out which cloudinit script the user wants to use
    user_data_options = os.listdir(cloudinit_scripts_dir)

    choice = choose_item_from_list(
        user_data_options,
        prompt='Select which user data file to attach:'
    )

    if choice == -1:
        # User didn't want to attach user data
        user_data = ""
    else:
        user_data_filename = os.path.join(
            cloudinit_scripts_dir,
            user_data_options[choice],
        )

        with open(user_data_filename) as user_data_handle:
            user_data = user_data_handle.read()

    if xml_parser_imported:
        # If the template is an XSLT, process it
        if user_data.startswith('<?xml '):
            user_data_template = xml.XML(user_data)

            # Get the stylesheet prefix
            prefix = user_data_template.tag.split('}')[0] + '}'

            # Find all required variables
            required_variables = {}
            elements = user_data_template.getchildren()[0].findall('%svalue-of'
                                                                   % prefix)
            for element in elements:
                required_variables[element.values()[0].split('/', 1)[1]] = ''

            for variable in required_variables.keys():
                # Get value user wants to use for variable
                print('Enter value for template variable %s:' % variable,
                      end='')
                required_variables[variable] = raw_input()

            # Build an XML doc from the provided variables to use with the XSLT
            xml_variables = '<vars>'
            for variable, value in required_variables.items():
                xml_variables += '<%s>%s</%s>' % (variable, value, variable)
            xml_variables += '</vars>'
            xml_variables = xml.XML(xml_variables)

            # Convert the template to XSLT
            user_data_template = xml.XSLT(user_data_template)

            # Apply the variables to the template to get the user data
            user_data = str(user_data_template(xml_variables))

            # Remove the leading line with the XML version added by the XSLT
            user_data = user_data.split('\n', 1)[1].strip()
    else:
        print('No xml parser present.')
        print('Using raw cloudinit script.')
        print('If the template is xml this is probably bad')
        print('See README if you need to fix this.')

    print('Using user data: %s' % user_data)

    user_data = base64.b64encode(user_data)
    '''
    default_hostname = '%s-%d' % (getpass.getuser(), time.time())
    hostname = raw_input(
        'Enter hostname for new VM (default %s):' % default_hostname
    )
    hostname = hostname.strip()
    if len(hostname) == 0:
        hostname = default_hostname

    default_displayname = hostname
    displayname = raw_input(
        'Enter displayname for new VM (press ENTER for default %s):' % default_displayname
    )
    displayname = displayname.strip()
    if len(displayname) == 0:
        displayname = default_displayname

    choice = -1
    while choice == -1:
        choice = choose_item_from_list(
            ['On', 'Off'],
            prompt='Select the initial power state of your VM:'
        )

        if choice == -1:
            print()
            print('Please select the initial power state of your VM.')

    if choice == 0:
        start_vm = 'true'
    else:
        start_vm = 'false'

    # Now build the VM
    request = {
        'serviceofferingid': service_offering_id,
        'templateid': template_id,
        'zoneid': zone_id,
        'displayname': displayname,
        'name': hostname,
        ##'userdata': user_data,
        'networkids': network_id,
        'startvm': start_vm,
    }

    # Get rid of the userdata if none is set
    #if len(request['userdata']) == 0:
    #    request.pop('userdata')

    # Print the request and wait for confirmation
    print("This is the chosen configuration:\n %s\n" % request)
    choice = -1
    while choice == -1:
        choice = choose_item_from_list(
            ['Deploy now', 'Cancel and exit'],
            prompt='Deploy VM or cancel:'
        )

    if choice == 2:
        exit

    result = api.deployVirtualMachine(request)
    job_id = result['jobid']

    request = {
        'jobid': job_id,
    }

    pprint.pprint(api.wait_for_job(job_id))

