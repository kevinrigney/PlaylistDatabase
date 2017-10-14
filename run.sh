#!/bin/bash

#
# As a cheap way to run this as a "service", call this script from
# rc.local in a screen session.
#
# For example, I have
# su pi -c 'screen -d -m /home/pi/PlaylistDatabase/run.sh'
# in mine
#

cd /home/pi/PlaylistDatabase
script -a -f -c 'python3 main.py' /tmp/PlaylistDatabse.log 
