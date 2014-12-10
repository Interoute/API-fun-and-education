#! /usr/bin/env python
# Python script for the Interoute Virtual Data Centre API:
#   Name: widget-check-vm-state-v2.py
#   Purpose: GUI widget to display the states of the VMs in a VDC
#   Requires: class VDCApiCall in the file vdc_api_call.py
#   
# See the repo: https://github.com/Interoute/API-fun-and-education       

# Copyright (C) Interoute Communications Limited, 2014

# This program is used in the blog post:
# http://cloudstore.interoute.com/main/knowledge-centre/blog/vdc-api-programming-fun-part-07
 
# How to use (for Linux and Mac OS):
# (0) You must have Python version 2.6 or 2.7 installed in your machine
# (1) Create a configuration file '.vdcapi' for access to the VDC API according to the instructions at
# http://cloudstore.interoute.com/main/knowledge-centre/library/vdc-api-introduction-api
# (2) Put this file and the file vdc_api_call.py in any location
# (3) You can run this file using the command 'python widget-check-vm-state-v2.py'


from Tkinter import *
import vdc_api_call as vdc
import json
import os
import datetime

class Application(Frame):
    def vmStates_update(self):
        #this method performs the API call 'listVirtualMachines'

        # Delete all current content of Text widget
        self.vmStatesText.delete(1.0, END)

        request={}
        checkTime = datetime.datetime.utcnow() # get the current time (UTC = GMT)
        try:
            result = self.api.listVirtualMachines(request)
            testdict = result['virtualmachine'][0] #this should throw exception if dictionary lookup fails
        except:
            self.vmStatesText.insert('end', "*** Error: VM data not returned by API\n***")
            return -1

        self.vmStatesText.insert('end',"%d VMs in the account '%s'\nchecked at %s" % (result['count'],result['virtualmachine'][1]['account'],checkTime.strftime("%Y-%m-%d %H:%M:%S UTC")))

        vmcounter=0
        for vm in result['virtualmachine']:
            vmcounter = vmcounter + 1
            if vm['state'] == 'Running':
               self.vmStatesText.insert('end',"\n  [%2d] %s  " % (vmcounter,vm['name']), ('stateRunning'))
            elif vm['state'] == 'Stopped':
               self.vmStatesText.insert('end',"\n  [%2d] %s  (%s)" % (vmcounter,vm['name'],vm['state']), ('stateStopped'))
            else:
               self.vmStatesText.insert('end',"\n  [%2d] %s  (%s)" % (vmcounter,vm['name'],vm['state']), ('stateOther'))

        # VM information will update after 60000 millisecs = 1 minute
        # ...set this value as you like
        self.vmStatesText.after(60000, self.vmStates_update)

    def refresh_states(self):
        #this method is called when the 'REFRESH' button is pressed
        self.vmStates_update()

    def createWidgets(self):
        self.vmStatesText = Text(self)
        self.vmStatesText["font"]=('Courier','14')
        self.vmStatesText.tag_configure('stateStopped',foreground='red')
        self.vmStatesText.tag_configure('stateRunning',foreground='green')
        self.vmStatesText.tag_configure('stateOther',foreground='blue')
        self.vmStatesText.pack({"side":"top"})
        self.vmStates_update()
        # VM information will update after 60000 millisecs = 1 minute
        # ...set this value as you like
        self.vmStatesText.after(60000, self.vmStates_update)

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
root.title("VM State Widget version 2")
app = Application(master=root)
app.mainloop()
root.destroy()
