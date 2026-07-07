#!/bin/bash
# This script will be executed on boot of the Pi
# (hooked up via crontab of the pi user: "@reboot /home/pi/autostart.sh")

# wait until the MultiWii board (USB serial) has enumerated, max 60 secs
for i in $(seq 1 30); do
    [ -e /dev/ttyACM0 ] && break
    sleep 2
done

/usr/local/bin/python3.11 /home/pi/drone/main.py > /tmp/drone_main.log 2>&1 &
