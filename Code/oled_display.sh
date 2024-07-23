while true; do
    python3 /root/code/fsize_delta_disp_v2.py
    printf 'The OLED controller crashed, wait for one second and restart\n'
    sleep 1
done