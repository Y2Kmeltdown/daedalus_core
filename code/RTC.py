import os
import subprocess
import sys
import time

def update_clock_time():
    if os.geteuid() != 0:
        sys.exit("[ERROR] Please run this script with sudo (needs NET_ADMIN)")
    subprocess.run(
            ["hwclock", "-s"],
            check=True
        )
    subprocess.run(
            ["hwclock", "--verbose"],
            check=True
        )
    
while True:
    update_clock_time()
    time.sleep(60)
