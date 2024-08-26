#!/bin/bash

raspi-config nonint do_spi 0
raspi-config nonint do_i2c 0
raspi-config nonint do_serial_hw 0
raspi-config nonint do_serial_cons 0
raspi-config nonint do_onewire 0
raspi-config nonint do_rgpio 0

sed -i 's/dtparam=i2c_arm=on/dtparam=i2c_arm=on,i2c_arm_baudrate=40000/g' /boot/firmware/config.txt
echo "usb_max_current_enable=1" >> /boot/firmware/config.txt

sed -i 's/#HandlePowerKey=poweroff/HandlePowerKey=ignore/g' /etc/systemd/logind.conf

echo "RuntimeWatchdogSec=15" >> /etc/systemd/system.conf
echo "RebootWatchdogSec=2min" >> /etc/systemd/system.conf

mkdir $HOME/data
cp -a Code $HOME/code
cp -a Config $HOME/config

apt-get update

add-apt-repository 'ppa:deadsnakes/ppa'

apt-get install -y \
    build-essential \
    curl \
    supervisor \
    bash \
    tzdata \
    software-properties-common \
    python3-launchpadlib \
    python3.11 \
    python3-pip


apt install -y python3-picamera2 --no-install-recommends

curl https://sh.rustup.rs -sSf | bash -s -- -y

export PATH="/root/.cargo/bin:${PATH}"

echo "export PATH=$HOME/.cargo/bin:${PATH}" >> ~/.bashrc

pip install --break-system-packages -r $HOME/config/requirements.txt

cp $HOME/config/65-neuromorphic-drivers.rules /etc/udev/rules.d/65-neuromorphic-drivers.rules
cp $HOME/config/99-camera.rules /etc/udev/rules.d/99-camera.rules
cp $HOME/config/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

systemctl daemon-reload
