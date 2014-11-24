#! /usr/bin/env python
# Python script for the Interoute Virtual Data Centre API:
#   Name: widget-big-red-button-v3.py
#   Purpose: Uses physical buttons to turn a virtual machine on and off
#   Requires: Raspberry Pi Model B
#   Requires: class VDCApiCall in the file vdc_api_call.py

# Copyright (C) Interoute Communications Limited, 2014

# How to use (for Linux and Mac OS):
# (0) You must have Python version 2.6 or 2.7 installed in your machine
# (1) Create a configuration file '.vdcapi' for access to the VDC API according to the instructions at
# http://cloudstore.interoute.com/main/knowledge-centre/library/vdc-api-introduction-api
# (2) Put this file and the file vdc_api_call.py in any location

# The GPIO library for Raspberry Pi may require installation (it is included in recent versions of Raspbian)

import vdc_api_call as vdc
import json
import os
import datetime
import RPi.GPIO as GPIO
import time
from Tkinter import *
from random import random

class MainWindow(Frame):
    def __init__(self, master=None):
        Frame.__init__(self)

        config_file = "/home/pi/.vdcapi"
        print("CONFIG: %s" % (config_file))
        if os.path.isfile(config_file):
            with open(config_file) as fh:
                #print("READING CONFIG")
                data = fh.read()
                config = json.loads(data)
                api_url = config['api_url']
                apiKey = config['api_key']
                secret = config['api_secret']
    
        # Create the api access object
        self.api = vdc.VDCApiCall(api_url, apiKey, secret)

        # INITIALISE THE GUI
        self.vmSelectedNumber= 0
        self.emergencyButtonState = True # Button should on ON (UP) at start

        self.pack({"fill":"both"})

        self.createWidgets()

    def emergencyMsg(self):
        if random()<0.5:
           return "HAVEN'T I TOLD YOU NOT TO PRESS \n THE EMERGENCY BUTTON?\n USE THE KEY TO RESET THE BUTTON\n AND DON'T TOUCH IT AGAIN!"
        else:
           return "THAT BUTTON IS FOR EMERGENCIES ONLY.\n DO YOU THINK THIS IS AN EMERGENCY??\n USE THE KEY TO RESET THE BUTTON\n AND DON'T TOUCH IT AGAIN!"      

    def create_window(self):
        t = Toplevel(self)
        t.wm_title("EMERGENCY STOP ALERT")
        l = Label(t, text=self.emergencyMsg(), font=('Times',36), fg="red")
        b = Button(t, text="Sorry, I won't do it again", command=t.destroy,  font=('Times',36), fg="red")
        l.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        b.pack(side="bottom")
        #Modal window - control stays here until this window is closed
        #t.focus_set()
        #t.grab_set()
        #t.wait_window()

    def get_encoder_turn(self):
        # return -1, 0, or +1
        result = 0
        new_a = GPIO.input(5)
        new_b = GPIO.input(6)
        if new_a != self.old_a or new_b != self.old_b :
           #print "a=%i b=%i" % (new_a,new_b)
           if self.old_a == 0 and new_a == 1 :
               result = (self.old_b * 2 - 1)
           elif self.old_b == 0 and new_b == 1 :
               result = -(self.old_a * 2 - 1)
        self.old_a, self.old_b = new_a, new_b
        time.sleep(0.001)
        return result
 
    def vmStates_update(self):
        self.vmStatesLabel["text"]=self.get_vm_info()
        # VM information will update after specified millisecs
        self.vmStatesLabel.after(5000, self.vmStates_update)

    def get_vm_info(self):
        #this method performs the API call 'listVirtualMachines'
        request={}
        checkTime = datetime.datetime.utcnow() # get the current time (UTC = GMT)
        try:
            result = self.api.listVirtualMachines(request)
	    ##print result
            testdict = result['virtualmachine'][0] #???this should throw exception if dictionary lookup fails
        except:
            return "***************************\nError: Cannot make connection with API\n***************************"

        self.vm={}
        self.vm['name'] = result['virtualmachine'][self.vmSelectedNumber]['name']
        self.vm['state'] = result['virtualmachine'][self.vmSelectedNumber]['state']
        self.vm['id'] = result['virtualmachine'][self.vmSelectedNumber]['id']
        self.vmCount = result['count']
        
        if self.vm['state']=='Running':
           #Turn on green LED, turn off red LED 
           GPIO.output(23,GPIO.HIGH)
           GPIO.output(24,GPIO.LOW)
           buttonMessage="PRESS THE small RED BUTTON TO STOP"
        elif self.vm['state']=='Stopped':
           #Turn off green LED, turn on red LED 
           GPIO.output(23,GPIO.LOW)
           GPIO.output(24,GPIO.HIGH)
           buttonMessage="PRESS THE GREEN BUTTON TO START"
        else:
           #Turn both LED off
           GPIO.output(23,GPIO.LOW)
           GPIO.output(24,GPIO.LOW)
           buttonMessage="BUTTONS ARE NON-OPERATIONAL"        

        return "Your selected VM is:\n[%d/%d]'%s'\nCurrent status: %s\n%s" % (self.vmSelectedNumber+1,self.vmCount,self.vm['name'],self.vm['state'],buttonMessage)

    def quit(self):
        #this method is called when the 'QUIT' button is pressed
        GPIO.cleanup()
        root.quit()

    def redButtonPressed(self,channel):
        print "test: RED BUTTON PRESSED!!"
        if self.vm['state']=='Running':
            request={'id': self.vm['id']}
            result= self.api.stopVirtualMachine(request)
            self.vmStatesLabel["text"]='**VM stopping, please wait**'      
            self.api.wait_for_job(result['jobid'])
            self.vmStatesLabel["text"]=self.get_vm_info()
    
    def greenButtonPressed(self,channel):
        print "test: GREEN BUTTON PRESSED!!"
        if self.vm['state']=='Stopped':
            request={'id': self.vm['id']}
            result= self.api.startVirtualMachine(request)
            self.vmStatesLabel["text"]='**VM starting, please wait**'      
            self.api.wait_for_job(result['jobid'])
            self.vmStatesLabel["text"]=self.get_vm_info()   

    def emergencyButtonPressed(self,channel):
       #need short time delay so that button is stable on or off when state is checked
       time.sleep(0.25) 
       if GPIO.input(26): 
          # Button state is now DOWN
          print "test: EMERGENCY BUTTON PRESSED" 
          self.create_window()

    def changeVmSelectionDown(self):
        if self.vmSelectedNumber > 0:
           self.vmSelectedNumber = self.vmSelectedNumber - 1
           self.vmStatesLabel["text"]=self.get_vm_info()

    def changeVmSelectionUp(self):
        if self.vmSelectedNumber <  self.vmCount-1 :
           self.vmSelectedNumber = self.vmSelectedNumber + 1
           self.vmStatesLabel["text"]=self.get_vm_info()
    
    def selectorTurned(self,channel):
        print("test: selectorTurned")
        change = self.get_encoder_turn()
        if change < 0 :
           self.changeVmSelectionUp()
        elif change > 0:
           self.changeVmSelectionDown()
        
    def createWidgets(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(23,GPIO.OUT) # green LED
        GPIO.setup(24,GPIO.OUT) # red LED
        GPIO.setup(17,GPIO.IN,pull_up_down=GPIO.PUD_UP) # red button
        GPIO.setup(22,GPIO.IN,pull_up_down=GPIO.PUD_UP) # green button
        GPIO.setup(5, GPIO.IN, pull_up_down=GPIO.PUD_UP) # rotary encoder A
        GPIO.setup(6, GPIO.IN, pull_up_down=GPIO.PUD_UP) # rotary encoder B
        self.old_a=0
        self.old_b=0
        GPIO.setup(26,GPIO.IN,pull_up_down=GPIO.PUD_UP) # EMERGENCY button

        GPIO.add_event_detect(17,GPIO.FALLING, callback=self.redButtonPressed, bouncetime=200)
        GPIO.add_event_detect(22,GPIO.FALLING, callback=self.greenButtonPressed, bouncetime=200)
        GPIO.add_event_detect(5,GPIO.FALLING, callback=self.selectorTurned, bouncetime=200)
        GPIO.add_event_detect(6,GPIO.FALLING, callback=self.selectorTurned, bouncetime=200)
        GPIO.add_event_detect(26,GPIO.RISING, callback=self.emergencyButtonPressed, bouncetime=200)
               
        self.vmStatesLabel = Label(self)
        self.vmStatesLabel.pack({"fill":"x","side":"top"})
        self.vmStatesLabel["font"]=('Courier','36')
        self.vmStatesLabel["justify"]=CENTER
        self.vmStatesLabel["text"]=self.get_vm_info()
        # VM information will update after 5000 millisecs
        self.vmStatesLabel.after(5000, self.vmStates_update)

        self.SELECTDOWN = Button(self)
        self.SELECTDOWN["text"] = "< VM select"
        self.SELECTDOWN["fg"] = "black"
        self.SELECTDOWN["command"]=self.changeVmSelectionDown
        self.SELECTDOWN.pack({"fill":"x","side":"left"})

        self.SELECTUP = Button(self)
        self.SELECTUP["text"] = "VM select >"
        self.SELECTUP["fg"] = "black"
        self.SELECTUP["command"]=self.changeVmSelectionUp
        self.SELECTUP.pack({"fill":"x","side":"left"})

        self.QUIT = Button(self)
        self.QUIT["text"] = "QUIT"
        self.QUIT["fg"]   = "red"
        self.QUIT["command"] =  self.quit
        self.QUIT.pack({"fill":"x","side": "right"})


if __name__ == "__main__":
   root = Tk()
   root.title("BIG RED BUTTON widget version 3")
   root.geometry("1400x240")
   main = MainWindow(root)
   root.mainloop()
