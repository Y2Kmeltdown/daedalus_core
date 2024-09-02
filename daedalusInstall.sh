#!/bin/bash

sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_serial_hw 0
sudo raspi-config nonint do_serial_cons 0
sudo raspi-config nonint do_onewire 0
sudo raspi-config nonint do_rgpio 0

sudo sed -i 's/dtparam=i2c_arm=on/dtparam=i2c_arm=on,i2c_arm_baudrate=40000/g' /boot/firmware/config.txt
sudo echo "usb_max_current_enable=1" >> /boot/firmware/config.txt

sudo sed -i 's/#HandlePowerKey=poweroff/HandlePowerKey=ignore/g' /etc/systemd/logind.conf

sudo echo "RuntimeWatchdogSec=15" >> /etc/systemd/system.conf
sudo echo "RebootWatchdogSec=2min" >> /etc/systemd/system.conf

mkdir $1
export DAEDALUS_DATA=$1
echo "export DAEDALUS_DATA=$1" >> /root/.bashrc
echo "export DAEDALUS_DATA=$1" >> /home/$SUDO_USER/.bashrc
source /home/$SUDO_USER/.bashrc


sudo cp -a Code /usr/local/code
sudo cp -a Config /usr/local/config

sudo apt-get update

sudo apt-get install -y \
    python3.11 \
    python3-pip

sudo apt install -y python3-picamera2 --no-install-recommends

curl https://sh.rustup.rs -sSf | bash -s -- -y

export PATH="$HOME/.cargo/bin:${PATH}"
echo "export PATH=$HOME/.cargo/bin:${PATH}" >> ~/.bashrc

pip install --break-system-packages -r /usr/local/config/requirements.txt

sudo cp /usr/local/config/65-neuromorphic-drivers.rules /etc/udev/rules.d/65-neuromorphic-drivers.rules
sudo cp /usr/local/config/99-camera.rules /etc/udev/rules.d/99-camera.rules

sudo mkdir -p /etc/supervisor/conf.d
sudo cp /usr/local/config/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

sudo apt-get install -y \
    supervisor


sudo sed "/[service]/a Environment="DAEDALUS_DATA=$1"" /lib/systemd/system/supervisor.service
echo 'Daedalus Core Installed successfully to view running processes visit http://daedalus.local or enter the command supervisorctl status\nReconfiguring eth0 to host device and rebooting.\nPlease Wait.'
sleep 10
# nmcli con delete DAEDALUS_ETH
# nmcli con add type ethernet ifname eth0 con-name DAEDALUS_ETH
# nmcli con modify DAEDALUS_ETH ipv4.method shared ipv4.address 192.168.5.1/24
# nmcli con modify DAEDALUS_ETH ipv6.method disabled
# nmcli con modify DAEDALUS_ETH connection.autoconnect yes
# nmcli con up DAEDALUS_ETH

# sudo reboot
#su $SUDO_USER -c '/usr/bin/supervisord -c /etc/supervisor/supervisord.conf'




