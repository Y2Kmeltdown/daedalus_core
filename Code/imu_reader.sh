while true; do
    python3 /root/code/imu_reader_adafruit.py
    printf 'The IMU controller crashed, wait for one second and restart\n'
    sleep 1
done