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

sudo mkdir $HOME/data
sudo cp -a /Code ~/code
sudo cp -a /Config ~/config

sudo apt-get update

sudo add-apt-repository 'ppa:deadsnakes/ppa'

sudo apt-get install -y \
    build-essential \
    curl \
    supervisor \
    bash \
    tzdata \
    software-properties-common \
    python3-launchpadlib


sudo apt install -y python3-picamera2 --no-install-recommends

curl https://sh.rustup.rs -sSf | bash -s -- -y

export PATH="/root/.cargo/bin:${PATH}"

sudo echo "export PATH=/root/.cargo/bin:${PATH}" >> ~/.bashrc

pip install --break-system-packages -r $HOME/config/requirements.txt

sudo cp $HOME/config/65-neuromorphic-drivers.rules /etc/udev/rules.d/65-neuromorphic-drivers.rules
sudo cp $HOME/config/99-camera.rules /etc/udev/rules.d/99-camera.rules
sudo cp $HOME/config/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

sudo systemctl daemon-reload
