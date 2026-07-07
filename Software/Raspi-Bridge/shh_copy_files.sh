#!/bin/bash
# Deploy workflow: edit the files here in the repo first, then run this script
# to copy them to the Pi. Restart the drone program (or reboot) to load them.
USER="pi"
HOSTNAME="raspi-cm4.local"  # resolves via mDNS on any shared WiFi and on the hotspot
#HOSTNAME="192.168.4.1"  # with Access Point (fallback if mDNS fails)

# home directory scripts (grouped scp -> one password prompt per call)
scp enable_hotspot.sh disable_hotspot.sh autostart.sh $USER@$HOSTNAME:~/

# drone program
scp drone/main.py drone/gps.py drone/pid.py drone/msp.py drone/camera.py \
    drone/timer.py drone/aruco_test.py drone/requirements.txt $USER@$HOSTNAME:~/drone/

echo "done - restart the drone program to load the new code:"
echo "  ssh $USER@$HOSTNAME 'pkill -x python3.11; ~/autostart.sh'"
