#!/bin/bash

su root -c raspi-config nonint do_spi 0
su root -c raspi-config nonint do_i2c 0
su root -c raspi-config nonint do_serial_hw 0
su root -c raspi-config nonint do_serial_cons 0
su root -c raspi-config nonint do_onewire 0
su root -c raspi-config nonint do_rgpio 0

su root -c sed -i 's/dtparam=i2c_arm=on/dtparam=i2c_arm=on,i2c_arm_baudrate=40000/g' /boot/firmware/config.txt
su root -c echo "usb_max_current_enable=1" >> /boot/firmware/config.txt

su root -c sed -i 's/#HandlePowerKey=poweroff/HandlePowerKey=ignore/g' /etc/systemd/logind.conf

su root -c echo "RuntimeWatchdogSec=15" >> /etc/systemd/system.conf
su root -c echo "RebootWatchdogSec=2min" >> /etc/systemd/system.conf

mkdir $1
export DAEDALUS_DATA=$1
echo "export DAEDALUS_DATA=$1" >> ~/.bashrc


cp -a Code /usr/local/code
cp -a Config /usr/local/config

sudo apt-get update

sudo apt-get install -y \
    build-essential \
    curl \
    supervisor \
    bash \
    tzdata \
    software-properties-common \
    python3-launchpadlib \
    python3.11 \
    python3-pip


sudo apt install -y python3-picamera2 --no-install-recommends

curl https://sh.rustup.rs -sSf | bash -s -- -y

export PATH="$HOME/.cargo/bin:${PATH}"
echo "export PATH=$HOME/.cargo/bin:${PATH}" >> ~/.bashrc
source ~/.bashrc

pip install --break-system-packages -r /usr/local/config/requirements.txt

su root -c cp /usr/local/config/65-neuromorphic-drivers.rules /etc/udev/rules.d/65-neuromorphic-drivers.rules
su root -c cp /usr/local/config/99-camera.rules /etc/udev/rules.d/99-camera.rules
su root -c cp /usr/local/config/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

su root -c systemctl daemon-reload
