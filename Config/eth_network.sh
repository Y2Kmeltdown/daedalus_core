#!/bin/bash

nmcli con delete DAEDALUS_ETH
nmcli con add type ethernet ifname eth0 con-name DAEDALUS_ETH
nmcli con modify DAEDALUS_ETH ipv4.method shared ipv4.address 192.168.5.1/24
nmcli con modify DAEDALUS_ETH ipv6.method disabled
nmcli con modify DAEDALUS_ETH connection.autoconnect yes
nmcli con up DAEDALUS_ETH