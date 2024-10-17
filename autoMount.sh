#!/bin/bash
USB_LABEL=PATRIOT
USB_UUID=$(lsblk -no LABEL,UUID | awk -v var="$USB_LABEL" '$1 == var {print $2}')
sudo mkdir /mnt/data
sudo echo "UUID=$USB_UUID   /mnt/data   exfat   defaults    0   2" >> /etc/fstab