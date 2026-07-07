sudo cp /etc/dhcpcd.access_point.conf /etc/dhcpcd.conf
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq
sudo reboot 