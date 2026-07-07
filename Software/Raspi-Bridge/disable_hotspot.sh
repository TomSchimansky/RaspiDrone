sudo systemctl stop hostapd
sudo systemctl stop dnsmasq
sudo systemctl disable hostapd
sudo systemctl disable dnsmasq
sudo cp /etc/dhcpcd.orig.conf /etc/dhcpcd.conf
sudo reboot