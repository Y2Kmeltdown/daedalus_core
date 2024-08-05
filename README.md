# Daedalus Core
## About
Daedalus Core is a docker image and set of scripts that handle the collection of data from sensors on a raspberry pi. Daedalus core is designed to be flexible in implementation and simple to modify. It uses supervisord to daemonise python scripts for data collection and monitor their function.

## Installation
To get started with daedalus core you will need a raspberry pi (preferable a pi 5 running raspbian lite) with docker installed on it.
You can then pull the docker image from `y2kmeltdown/daedaluscore` onto a raspberry pi then run the `dockerrun.sh` script for simple installation.
For specific installation steps you can modify these values of the docker run command.

### Environment Variables
```docker
    HOME=/root \
	DEBIAN_FRONTEND=noninteractive \
	LANG=en_US.UTF-8 \
	LANGUAGE=en_US.UTF-8 \
	LC_ALL=C.UTF-8 \
    SERIAL_0=00042412 \
    SERIAL_1=00050591 \
    I2C_0=0x69 \
    I2C_1=0x68 \
    SUPERVISORD_PORT=9000 \
    MJPEG_PORT=8000
```
### Volumes
A data volume must be mapped at the image runtime to ensure data is not erased when the container closes. Data is typically generated in the directory `/root/data` inside the docker container for all sensors so ensure this volume is mapped externally.

To ensure components of the raspberry pi are accessible to the docker container the udev rules need to be transferred to the container from the `/run/udev` directory. Ensure this is mapped one to one in the docker container as a read only directory, e.g. `-v /run/udev:/run/udev:ro`.

### Ports
Port mapping differs depending on configuration but generally port `9000` is used for the supervisord monitoring page and should be mapped externally. Daedalus core also makes use of mjpeg servers to stream video data out which will also require port mapping. By default the mjpeg server listens on port `8000`. All ports can be modified through the environment variables as well so you can adjust your port mapping to which ever port you want to use.

### Settings
To operate properly the dokcer container must be run in privileged mode. This ensures that all interfaces are exposed to the container such as i2c, CSI, USB and SPI. ensure the `--privileged` tag is used when running the container.

To ensure that the container stays active in the event a script causes the container to crash the restart tag should be used and the setting always should be used e.g. `--restart always`.

The final docker run command should look something like this

```bash
docker run --privileged -v /run/udev:/run/udev:ro -v /home/daedalus/daedalus_core Data:/root/data -p 9001:9001 -p 8000:8000 -p 8001:8001 --restart always daedaluscore:latest
```

## Installation Alternative
**NOT IMPLEMENTED YET**

You can also use a raspberry pi image preloaded with the docker container and the required configuration if you don't want to go through the steps of installing docker or the image. For this you can find the image [here](). Using a tool like balenaEtcher you can load an SD card with the image and insert it into a raspberry pi and have it up and running. 

**IMPORTANT NOTE:** The image is designed for raspberry pi 5 and may not be compatible with raspberry pi 4s.

## How to use

The best way to interact with the processes running on the Raspberry Pi, is to use another computer as a network host and connect an ethernet cable directly to the raspberry pi. On windows you can do this by navigating to `control panel` then to `network and internet` then `network and sharing center` Finally to `Change Adapter Options` on the left side of control panel. From this page make note of the ethernet adapter you will be using. From this stage there are two options of how to set your computer as host.
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
