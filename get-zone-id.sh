#!/bin/bash

#VDC API
#Show the id of a zone using the zone name as an input

cloudmonkey set display table

echo
printf "CHECKING ZONE INFORMATION FOR: %s\n" $1
cloudmonkey list zones filter=name,id | grep $1

cloudmonkey set display json