docker run --privileged -v /run/udev:/run/udev:ro -v /home/daedalus/daedalus_core/Data:/root/data -p 9000:9000 -p 8000:8000 -p 8001:8001 --restart always daedaluscore:latest