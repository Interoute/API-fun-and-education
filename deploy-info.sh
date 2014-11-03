#!/bin/bash

#Convenience script to display information for deployment of a VM

cloudmonkey set display table

echo
echo "ZONES"
cloudmonkey list zones filter=name,id

echo
echo "TEMPLATES"
cloudmonkey list templates templatefilter=executable filter=name,zonename,id

echo
echo "SERVICE OFFERINGS"
cloudmonkey list serviceofferings filter=name,id

cloudmonkey set display json
