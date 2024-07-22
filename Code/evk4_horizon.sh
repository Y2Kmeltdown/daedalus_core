while true; do
    python3 /root/code/record_raw_ekv4_w_temp_and_illum.py --recordings /root/data/evk4_horizon $SERIAL_1
    printf "EVK4 $SERIAL_1 (horizon) crashed, wait for one second and restart\n"
    sleep 1
done