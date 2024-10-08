# Daedalus Core
## About
Daedalus Core is a docker image and set of scripts that handle the collection of data from sensors on a raspberry pi. Daedalus core is designed to be flexible in implementation and simple to modify. It uses supervisord to daemonise python scripts for data collection and monitor their function.

## Simple Install (Preferred)
You can use a raspberry pi image preloaded with the required configuration if you don't want to go through the steps of installing all the prerequisites. For this you can contact Nic Ralph(n.ralph@westernsydney.edu.au) and he will provide you with the image. Using a tool like balenaEtcher or raspberry pi imager, you can load an SD card with the image and insert it into a raspberry pi and have it up and running. 

**IMPORTANT NOTE:** The image is designed for raspberry pi 5 and may not be compatible with raspberry pi 4s.

## Manual Installation

### Setting up the image
To get started with daedalus core you will need a raspberry pi preferably a raspberry pi 5 and a suitably sized SD card for your application. Firstly you will need to install raspbian lite. The easiest way is to use the [raspberry pi imager](https://downloads.raspberrypi.org/imager/imager_latest.exe). Make sure you modify the settings to update the hostname to whatever is most memorable and set a simple username and password. Finally you should also go to services and enable ssh using password or public key authentication, this is the easiest way to interact with the raspberry pi once raspbian lite is installed. With all the settings done you can write the image to an SD card.

### Connecting to the Pi
Plug the SD card into the Raspberry Pi and boot the pi up. To connect to the raspberry pi you have four options:
#### Direct connection
Plug in a HDMI cable and a keyboard and mouse and you will be able to access the raspberry pi terminal directly from the hardware. You will still need an internet connection to install docker and the daedalus image.
#### Ethernet connection
Connect the Raspberry Pi via ethernet to the same network as your main computer then use SSH either through putty, powershell or git bash. If you are on windows I recommend installing bonjour as it will allow you to connect to the raspberry pi via it's hostname.
#### Wi-Fi connection
If you set up wireless LAN before writing the image to the SD card you can SSH into the pi if you are connected to the same network using the same steps as ethernet connection.
#### Host computer
Finally the most ideal method is to use your main computer as a host and connect an ethernet cable directly from the raspberry pi to an ethernet port on your main device. See [Using Windows as a host device](#using-windows-as-a-host-device) for setting up your computer as a host device.

### Configuring the Pi
Once you have a method of interacting with the raspberry pi you should set up a few things. 

First you should run the following commands to ensure the repositories are up to date and git is installed:
```bash
sudo apt-get update && sudo apt install git -y
```
With git installed you can clone the repository:
```bash
git clone https://github.com/Y2Kmeltdown/daedalus_core.git
```
Then navigate to the daedalus core folder and run daedalusInstall.sh with your preferred location for data. It is important to specify the full data path, for example `/home/<USERNAME>/data` as the script has to be run as root to allow configuration of certain files on the raspberry pi. 

**IMPORTANT NOTE:** If you do not set a directory it will default to `/usr/local/daedalus/data`
```bash
cd daedalus_core
sudo bash daedalusInstall.sh </path/to/data>
```
The script sets all of the required raspberry pi configuration, moves the code and config into a permanent location, installs and starts supervisor, sets up the ethernet network as a host device then finally reboots to allow some changes to take affect. The data is stored in the specified location of the install script.

After rebooting, daedalus core should start acting as a host device making it easy to connect via ethernet while in remote locations and the status of sensors should be available at `daedalus.local`

## How to use

Daedalus Core is mostly designed to be a set and forget system once it is powered on and running it should start immediately collecting data but there are some methods of controlling the processes running on the raspberry pi. Daedalus core can be connected to via wifi. On boot, daedalus will load an access point named DAEDALUS which you can connect to to monitor it's function.

### Accessing supervisord

Once you connect to the daedalus access point you can view the supervisor webpage by navigating to `daedalus.local` or if you cannot resolve the hostname `192.168.4.1`

On the supervisord webpage you will see all sensor processes running or failing. Clicking on the processes will bring up logs which will display whatever information is being logged but most importantly if the process is failing it displays the error information.

### Accessing mjpeg server

The mjpeg server is used to display event data through a network stream to view externally from the pi. This process should only be used to view data and should not be left running while collecting long term event data. This server is primarily meant to aid in adjusting the focus of the event cameras before commencing data collection. The mjpeg servers can be accessed on `daedalus.local:8000` and `daedalus.local:8001` for each event camera connected. If you cannot resolve the hostname of the pi `192.168.4.1:8000` and `192.168.4.1:8001`. The mjpeg server is a view only webpage with a single stream of jpeg frames in the center of the page.

## How it works

Daedalus utilises supervisor to act as a daemonizer for all of your sensors. When the raspberry pi boots supervisor reads the config file `/etc/supervisor/conf.d/supervisord.conf` and launches each program in it as a seperate daemon and through either a webpage or supervisorctl you can view the processes, logs and status of each process. To add new sensors or modify how supervisor runs each sensor you can modify the configuration file or the python scritps directly which can be found in `$HOME/code`

## Modifying Daedalus Core

To modify the function of supervisord you can edit the supervisord.conf file 
```bash
sudo nano /etc/supervisor/conf.d/supervisord.conf
```

To modify the sensor files you can access them in the directory
```
cd /home/daedalus/code
```

To add new sensors you will need to install all requirements for the new sensor, add the new sensor file to the code directory then add the new service in supervisord.conf to run the sensor as a daemon.

After any changes made to the system ensure they changes are saved then reboot and test.

[camera config](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf)

## Appendix

### Installing Bonjour
Unfortunately Apple doesn't make it easy to install bonjour on windows as a standalone program. The easiest way to install it is to install [iTunes](https://secure-appldnld.apple.com/itunes12/001-80053-20210422-E8A3B28C-A3B2-11EB-BE07-CE1B67FC6302/iTunes64Setup.exe) which will include bonjour along side it. You can uninstall itunes and the other applications installed with it and it will leave bonjour installed.

### Using Windows as a host device
The best way to interact with the Raspberry Pi, is to use another computer as a network host and connect an ethernet cable directly to the raspberry pi. On windows you can do this by navigating to `control panel` then to `network and internet` then `network and sharing center` Finally to `Change Adapter Options` on the left side of control panel. From this page make note of the ethernet adapter you will be using. From this stage there are two options of how to set your computer as host.
#### Automatic Method
Navigate to the primary adapter which you use for internet connection then right click on the adapter and go to properties. In properties navigate to the sharing tab from the tabs at the top of the window. There will be a check box option that says "Allow other network users to connect through this computer's Internet connection". Check that tick box then underneath there is a drop down box that says "Home networking connection:". Select the ethernet adapter you are using for the raspberry pi in that dropdown box and now you should have a connection to the raspberry pi which you can test by typing `ipconfig /all` to find the ip address of the ethernet interface which is most likely `192.168.137.1`. Then you can type the command `arp -a` which will list all of the ip addresses connected to each interface which should include the raspberry pi. If you have bonjour installed you can also ping the raspberry pi by it's hostname `raspberrypi.local`
#### Manual Method
This method is mostly just an explanation of how windows works as a host device. From the interfaces section right click on the ethernet adapter which you will be using for the raspberry pi then go to properties. Inside the group box labelled "This connection uses the following items", locate the option "Internet Protocol Version 4 (TCP/IPv4)". Highlight the option then click properties. Change the toggle box selection from "Optain an IP address automatically" to "Use the following IP address:", then in the group box underneath enter the following values for each row:
| Field Name      | Value           |
|-----------------|-----------------|
| IP Address:     | `192.168.137.1` |
| Subnet Mask:    | `255.255.255.0` |
| Default gateway | `192.168.137.1` |

You will be forced to enter DNS addresses in the groupbox below as well. For this you can enter any DNS address you want to use. Normal DNS addresses can be something like `1.1.1.1` (Cloudflare) and `8.8.8.8` (Google)

The specific ip address `192.168.137.1` is important to windows because windows natively uses that ip address to run a dhcp server which will automatically provide ip addresses to connected devices. This is how the sharing option can actually share internet connections to connected devices.
