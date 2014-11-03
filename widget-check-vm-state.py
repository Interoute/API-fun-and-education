#! /usr/bin/env python
# Python script for the Interoute Virtual Data Centre API:
#   Name: widget-check-vm-state.py
#   Purpose: GUI widget to display the states of the VMs in a VDC
#   Requires: class VDCApiCall in the file vdc_api_call.py
#       [https://gist.github.com/InterouteGIST/aff2f957b7f0d766fab9]

# Copyright (C) Interoute Communications Limited, 2014

# This program is used in the blog post:
# http://cloudstore.interoute.com/main/knowledge-centre/blog/vdc-api-programming-fun-part-04
 
# How to use (for Linux and Mac OS):
# (0) You must have Python version 2.6 or 2.7 installed in your machine
# (1) Create a configuration file '.vdcapi' for access to the VDC API according to the instructions at
# http://cloudstore.interoute.com/main/knowledge-centre/library/vdc-api-introduction-api
# (2) Put this file and the file vdc_api_call.py in any location
# (3) You can run this file using the command 'python widget-check-vm-state.py'


from Tkinter import *
import vdc_api_call as vdc
import json
import os
import datetime

class Application(Frame):
    def vmStates_update(self):
        self.vmStatesLabel["text"]=self.get_vm_info()
        # VM information will update after 60000 millisecs = 1 minute
        # ...set this value as you like
        self.vmStatesLabel.after(60000, self.vmStates_update)

    def get_vm_info(self):
        #this method performs the API call 'listVirtualMachines'
        request={}
        checkTime = datetime.datetime.utcnow() # get the current time (UTC = GMT)
        result = self.api.listVirtualMachines(request)

        vmresultstring=""
        for vm in result['virtualmachine']:
            if vm['state'] == 'Running':
               vmresultstring = vmresultstring + "\n  %s" % vm['name']
            elif vm['state'] == 'Stopped':
               vmresultstring = vmresultstring + "\n  %s (%s)" % (vm['name'],vm['state'])
            else:
               vmresultstring = vmresultstring + "\n  %s (%s)" % (vm['name'],vm['state'])

        return "%d VMs in the account '%s'\nchecked at %s" % (result['count'],result['virtualmachine'][1]['account'],checkTime.strftime("%Y-%m-%d %H:%M:%S UTC")) + vmresultstring

    def refresh_states(self):
        #this method is called when the 'REFRESH' button is pressed
        self.vmStatesLabel["text"]=self.get_vm_info()
        
    def createWidgets(self):
        self.vmStatesLabel = Label(self)
        self.vmStatesLabel.pack({"side":"top"})
        self.vmStatesLabel["font"]=('Courier','14')
        self.vmStatesLabel["justify"]=LEFT
        self.vmStatesLabel["text"]=self.get_vm_info()
        # VM information will update after 60000 millisecs = 1 minute
        # ...set this value as you like
        self.vmStatesLabel.after(60000, self.vmStates_update)

        self.QUIT = Button(self)
        self.QUIT["text"] = "QUIT"
        self.QUIT["fg"]   = "red"
        self.QUIT["command"] =  self.quit
        self.QUIT.pack({"side": "right"})

        self.refresh = Button(self)
        self.refresh["text"] = "REFRESH",
        self.refresh["command"] = self.refresh_states
        self.refresh.pack({"side": "left"})

    def __init__(self, master=None):
        Frame.__init__(self, master)

        config_file = os.path.join(os.path.expanduser('~'), '.vdcapi')
        if os.path.isfile(config_file):
            with open(config_file) as fh:
                data = fh.read()
                config = json.loads(data)
                api_url = config['api_url']
                apiKey = config['api_key']
                secret = config['api_secret']
    
        # Create the api access object
        self.api = vdc.VDCApiCall(api_url, apiKey, secret)

        # INITIALISE THE GUI
        self.pack()
        self.createWidgets()

root = Tk()
root.title("VM State Widget")
app = Application(master=root)
app.mainloop()
root.destroy()
