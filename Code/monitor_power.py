import subprocess
from time import sleep
from datetime import datetime
 
while (True):
    print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
    subprocess.run(['vcgencmd', 'pmic_read_adc'])
    sleep(15)