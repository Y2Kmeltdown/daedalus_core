while true; do
    python3 /root/code/record_raw_ekv4_w_temp_and_illum.py --recordings /root/data/evk4_space $SERIAL_0
    printf "EVK4 $SERIAL_0 (space) crashed, wait for one second and restart\n"
    sleep 1
done