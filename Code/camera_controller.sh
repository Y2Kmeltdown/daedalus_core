while true; do
    python3 /root/code/camera_controller.py
    printf 'The Pi Camera Controller crashed, wait for one second and restart\n'
    sleep 1
done