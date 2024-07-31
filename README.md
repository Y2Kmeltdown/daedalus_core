# Daedalus Core
## About
Daedalus Core is a docker image and set of scripts that handle the collection of data from sensors on a raspberry pi. Daedalus core is designed to be flexible in implementation and simple to modify. It uses supervisord to daemonise python scripts for data collection and monitor their function.

## Installation
To get started with daedalus core you will need a raspberry pi (preferable a pi 5 running raspbian lite) with docker installed on it.
You can then pull the docker image from `y2kmeltdown/daedaluscore` onto a raspberry pi then run the `dockerrun.sh` script for simple installation.
For specific installation steps you can modify these values of the docker run command.

### Environment Variables

### Volumes
A data volume must be mapped at the image runtime to ensure data is not erased when the container closes. Data is typically generated in the directory `/root/data` inside the docker container for all sensors so ensure this volume is mapped externally.

To ensure components of the raspberry pi are accessible to the docker container the udev rules need to be transferred to the container from the `/run/udev` directory. Ensure this is mapped one to one in the docker container as a read only directory, e.g. `-v /run/udev:/run/udev:ro`.

### Ports
Port mapping differs depending on configuration but generally port `9001` is used for the supervisord monitoring page and should be mapped externally. Daedalus core also makes use of mjpeg servers to stream video data out which will also require port mapping. By default the mjpeg server listens on port 8000. All ports can be modified through the environment variables as well so you can adjust your port mapping to which ever port you want to use.

### Settings

## Installation Alternative
You can also use a raspberry pi image preloaded with the docker container and the required configuration if you don't want to go through the steps of installing docker or the image. For this you can find the image [here](). Using a tool like balenaEtcher you can load an SD card with the image and insert it into a raspberry pi and have it up and running. 

**IMPORTANT NOTE:** The image is designed for raspberry pi 5 and may not be compatible with raspberry pi 4s.

## How to use


## Modifying Daedalus Core

### Adding sensors

### Adding access rules

### Modifying configuration

### Adding Requirements
