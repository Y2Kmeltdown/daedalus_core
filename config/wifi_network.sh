#!/bin/bash

nmcli con delete DAEDALUS-AP
nmcli con add type wifi ifname wlan0 mode ap con-name DAEDALUS-AP ssid DAEDALUS autoconnect false
nmcli con modify DAEDALUS-AP wifi.band bg
nmcli con modify DAEDALUS-AP wifi.channel 3
nmcli con modify DAEDALUS-AP wifi.cloned-mac-address 00:12:34:56:78:9a
nmcli con modify DAEDALUS-AP wifi-sec.key-mgmt wpa-psk
nmcli con modify DAEDALUS-AP wifi-sec.proto rsn
nmcli con modify DAEDALUS-AP wifi-sec.group ccmp
nmcli con modify DAEDALUS-AP wifi-sec.pairwise ccmp
nmcli con modify DAEDALUS-AP wifi-sec.psk "daedalus"
nmcli con modify DAEDALUS-AP ipv4.method shared ipv4.address 192.168.4.1/24
nmcli con modify DAEDALUS-AP ipv6.method disabled
nmcli con modify DAEDALUS-AP connection.autoconnect yes
nmcli con up DAEDALUS-AP