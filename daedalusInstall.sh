#!/bin/bash

## CONFIGURATION
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_serial_hw 0
sudo raspi-config nonint do_serial_cons 0
sudo raspi-config nonint do_rgpio 0

sudo sed -i 's/dtparam=i2c_arm=on/dtparam=i2c_arm=on,i2c_arm_baudrate=400000/g' /boot/firmware/config.txt
sudo echo "usb_max_current_enable=1" >> /boot/firmware/config.txt

sudo sed -i 's/#HandlePowerKey=poweroff/HandlePowerKey=ignore/g' /etc/systemd/logind.conf

sudo echo "RuntimeWatchdogSec=15" >> /etc/systemd/system.conf
sudo echo "RebootWatchdogSec=2min" >> /etc/systemd/system.conf

## DIRECTORY SETUP
if [ -z "${1}" ]; then
    DAEDALUS_DIR=/mnt/data
else
    DAEDALUS_DIR=$1
    mkdir -p /usr/local/daedalus/data
    touch /usr/local/daedalus/data/where_are_my_files.txt
    echo "Data Files have been set to $1 during installation" >> /usr/local/daedalus/data/where_are_my_files.txt
fi
mkdir -p $DAEDALUS_DIR

sudo mkdir /mnt/data
sudo echo "/dev/sda1  /mnt/data  auto  noatime,rw,nofail,noauto,sync,x-systemd.automount" >> /etc/fstab

sudo mkdir -p /usr/local/daedalus
sudo cp -a Code /usr/local/daedalus/code
sudo cp -a Config /usr/local/daedalus/config

sudo sed -i "s@/usr/local/daedalus/data@$DAEDALUS_DIR@g" /usr/local/daedalus/config/supervisord.conf

## REPOSITORY FETCH
sudo apt-get update

## I2C Tools install
sudo apt-get install -y \
    i2c-tools

## RUST INSTALLATION
curl https://sh.rustup.rs -sSf | bash -s -- -y

export PATH="$HOME/.cargo/bin:${PATH}"
echo "export PATH=$HOME/.cargo/bin:${PATH}" >> ~/.bashrc

## PYTHON INSTALLATION
sudo apt-get install -y \
    python3.11 \
    python3-pip

sudo apt install -y python3-picamera2 --no-install-recommends
pip install --break-system-packages -r /usr/local/daedalus/config/requirements.txt

## DRIVER INSTALLATION
sudo cp /usr/local/daedalus/config/65-neuromorphic-drivers.rules /etc/udev/rules.d/65-neuromorphic-drivers.rules
sudo cp /usr/local/daedalus/config/99-camera.rules /etc/udev/rules.d/99-camera.rules

## WATCHDOG INSTALLATION
wget https://github.com/joan2937/lg/archive/master.zip
unzip master.zip
cd lg-master
sudo make install
cd ~

sudo apt-get install -y \
    ttf-wqy-zenhei

sudo cp /usr/local/daedalus/config/external_watchdog.service /lib/systemd/system/external_watchdog.service
sudo chmod 644 /lib/systemd/system/external_watchdog.service
sudo systemctl daemon-reload
sudo systemctl enable external_watchdog.service

## Buzzer installation
sudo cp /usr/local/daedalus/config/buzzer.service /lib/systemd/system/buzzer.service
sudo chmod 644 /lib/systemd/system/buzzer.service
sudo systemctl daemon-reload
sudo systemctl enable buzzer.service


## SUPERVISOR INSTALLATION
sudo mkdir -p /etc/supervisor/conf.d
sudo cp /usr/local/daedalus/config/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

sudo apt-get install -y \
    supervisor

## NETWORK SET UP AND FINALISATION
echo -e "Daedalus Core Installed successfully to view running processes visit http://daedalus.local or enter the command supervisorctl status\nReconfiguring eth0 to host device and rebooting.\nPlease Wait."
sleep 10
nmcli con delete DAEDALUS_ETH
nmcli con add type ethernet ifname eth0 con-name DAEDALUS_ETH
nmcli con modify DAEDALUS_ETH ipv4.method shared ipv4.address 192.168.5.1/24
nmcli con modify DAEDALUS_ETH ipv6.method disabled
nmcli con modify DAEDALUS_ETH connection.autoconnect yes
nmcli con up DAEDALUS_ETH

sudo chmod -R 777 $DAEDALUS_DIR

sudo reboot