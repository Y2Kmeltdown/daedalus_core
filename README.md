# Daedalus Core
## About
Daedalus Core is a docker image and set of scripts that handle the collection of data from sensors on a raspberry pi. Daedalus core is designed to be flexible in implementation and simple to modify. It uses supervisord to daemonise python scripts for data collection and monitor their function.

## Installation

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
Once you have a method of interacting with the raspberry pi you should set up a few things. First you should enable a few interfaces. Run the command `sudo raspi-config` then navigate to `Interface Options` then enable `SPI`, `I2C`, `Serial Port`, `1-Wire` and `Remote GPIO` then reboot the Raspberry Pi.

Next you will need to update some values in `/boot/firmware/config.txt`.
Enter the command:
```bash
sudo nano /boot/firmware/config.txt
```
Find the parameter:
```bash
dtparam=i2c_arm=on
```
Then change it to:
```bash
dtparam=i2c_arm=on,i2c_arm_baudrate=40000
```
This will increase the data rate of i2c which is necessary for some i2c devices.

Next navigate to the bottom of `config.txt` and add the line:
```bash
usb_max_current_enable=1
```
This will increase the current capacity of the usb ports from 600mA to 1.6A which is important for certain devices.

Save the changes made to `/boot/firmware/config.txt` by clicking `ctrl-o` then exit by clicking `ctrl-x`.

The last config change is only necessary for raspberry pi 5's. Type the following:
```bash
sudo nano /etc/systemd/logind.conf
```
then change the following:
```bash
#HandlePowerKey=poweroff
```
to the following:
```bash
HandlePowerKey=ignore
```
This will disable the power button on the pi preventing accidental power downs.
Save the changes by clicking `ctrl-o` then exit by clicking `ctrl-x`

After these changes reboot the pi using `sudo reboot`

### Installing Docker
Next You can install Docker using the following commands:
```bash
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/raspbian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/raspbian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

# Install Docker Packages
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```
After installation, test the install by running:
```bash
sudo docker run hello-world
```
To run docker as non root user use the following commands to add a docker group:
```
sudo groupadd docker
```
Then add your current user to the group:
```
sudo usermod -aG docker $USER
```
Reboot and you should be able to run docker without the sudo command.
If it is successful you can install the daedalus core image.
You can then pull the docker image from `y2kmeltdown/daedaluscore` onto a raspberry pi using the command:
```bash
docker pull y2kmeltdown/daedaluscore:latest
```
Before running the container you should make a directory on the pi which will be used to store the data generated by the container.
```bash
sudo mkdir data
```
Now you can run the following command for simple installation.
```bash
docker run --privileged -v /run/udev:/run/udev:ro -v /home/daedalus/data:/root/data -p 9000:9000 -p 8000:8000 -p 8001:8001 --restart always y2kmeltdown/daedaluscore:latest
```
## Installation Alternative
**NOT IMPLEMENTED YET**

You can also use a raspberry pi image preloaded with the docker container and the required configuration if you don't want to go through the steps of installing docker or the image. For this you can find the image [here](). Using a tool like balenaEtcher you can load an SD card with the image and insert it into a raspberry pi and have it up and running. 

**IMPORTANT NOTE:** The image is designed for raspberry pi 5 and may not be compatible with raspberry pi 4s.
## Container Configuration
### Environment Variables
| Environment Variable | Default | Description |
|----------------------|---------|-------------|
| **HOME**                  | /root          | Home Directory of docker user |
| **DEBIAN_FRONTEND**       | noninteractive | Specify for an automatic installation with no interactions |
| **SERIAL_0**              | 00050869           | Serial number of event camera 0 |
| **SERIAL_1**              | 00050591           | Serial number of event camera 1 |
| **I2C_0**                 | 0x69           | i2c address of accelerometer 0  |
| **I2C_1**                 | 0x68           | i2c address of accelerometer 0  |
| **SUPERVISORD_PORT**      | 9000           | Supervisord web port            |
| **MJPEG_PORT_0**          | 8000           | Video stream port of mjpeg server 0 |
| **MJPEG_PORT_1**          | 8001           | Video stream port of mjpeg server 1 |

### Volumes
A data volume must be mapped at the image runtime to ensure data is not erased when the container closes. Data is typically generated in the directory `/root/data` inside the docker container for all sensors so ensure this volume is mapped externally.

To ensure components of the raspberry pi are accessible to the docker container the udev rules need to be transferred to the container from the `/run/udev` directory. Ensure this is mapped one to one in the docker container as a read only directory, e.g. `-v /run/udev:/run/udev:ro`.

### Ports
Port mapping differs depending on configuration but generally port `9000` is used for the supervisord monitoring page and should be mapped externally. Daedalus core also makes use of mjpeg servers to stream video data out which will also require port mapping. By default the mjpeg servers listen on ports `8000` and `8001`. All ports can be modified through the environment variables as well so you can adjust your port mapping to which ever port you want to use.

### Settings
To operate properly the dokcer container must be run in privileged mode. This ensures that all interfaces are exposed to the container such as i2c, CSI, USB and SPI. ensure the `--privileged` tag is used when running the container.

To ensure that the container stays active in the event a script causes the container to crash the restart tag should be used and the setting always should be used e.g. `--restart always`.
## How to use

Daedalus Core is mostly designed to be a set and forget system once it is powered on and running it should start immediately collecting data but there are some methods of controlling the processes running on the raspberry pi. To connect to the pi easily see [Using Windows as a host device](#using-windows-as-a-host-device).

### Accessing supervisord

Once you have connected to the same network as the raspberry pi you can access supervisord web interface on either `raspberrypi.local:9000` or if you cannot resolve the hostname of the pi you can use the pi's ip address `{Pi IP address}:9000`.

On the supervisord webpage you will see all sensor processes running or failing. Clicking on the processes will bring up logs which will display whatever information is being logged but most importantly if the process is failing it displays the error information.

### Accessing mjpeg server

The mjpeg server is used to display event data through a network stream to view externally from the pi. This process should only be used to view data and should not be left running while collecting long term event data. This server is primarily meant to aid in adjusting the focus of the event cameras before commencing data collection. The mjpeg servers can be accessed on `raspberrypi.local:8000` and `raspberrypi.local:8001` for each event camera connected. If you cannot resolve the hostname of the pi `{Pi IP address}:8000` and `{Pi IP address}:8001`. The mjpeg server is a view only webpage with a single stream of jpeg frames in the center of the page.

## Modifying Daedalus Core

### Adding sensors

### Adding access rules

### Modifying configuration

[camera config](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf)

### Adding Requirements

### Building the docker image

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
