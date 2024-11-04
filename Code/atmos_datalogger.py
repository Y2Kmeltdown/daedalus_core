from smbus2 import SMBus
import csv
import argparse
import os
import sys
from datetime import datetime, timedelta
import time
import decimal

i2cbus = SMBus(1)
time.sleep(1)

r_dict = {
    "reset_REG":        0xE0,
    "status_REG":       0xF3,
    "ctrl_hum_REG":     0xF2,
    "ctrl_meas_REG":    0xF4,
    "config_REG":       0xF5,
    "press_msb_REG":    0xF7,
    "press_lsb_REG":    0xF8,
    "press_xlsb_REG":   0xF9,
    "temp_msb_REG":     0xFA,
    "temp_lsb_REG":     0xFB,
    "temp_xlsb_REG":    0xFC,
    "hum_msb_REG":      0xFD,
    "hum_lsb_REG":      0xFE,
}

reset_WORD = 0xB6

def atmosInit(t_sample:int = 1, p_sample:int = 1, h_sample:int = 1, mode:str = "Normal", stnby:float = 20, filter_coef:int = 0):
    allowed_vals = [0,1,2,4,8,16]
    if t_sample not in allowed_vals or p_sample not in allowed_vals or h_sample not in allowed_vals:
        raise ValueError("sample rate for t_sample, p_sample and h_sample must be one of the following integers\n0, 1, 2, 4, 8, 16")
    
    allowed_modes = ["Sleep", "Normal", "Forced"]
    if mode not in allowed_modes:
        raise ValueError("Mode for device must be one of the following strings \n'Sleep', 'Normal' or 'Forced'")
    
    allowed_stnby = [0.5, 62.5, 125, 250, 500, 1000, 10, 20]
    if stnby not in allowed_stnby:
        raise ValueError("Standby time must be one of the following float values measured in ms\n0.5, 10, 20, 62.5, 125, 250, 500, 1000")
    
    allowed_filter = [0, 2, 4, 8, 16]
    if filter_coef not in allowed_filter:
        raise ValueError("Filter coefficient must be one of the following integers\n 0, 2, 4, 8, 16")

    def sampleBin(sample):
        if sample == 0:
            binSample = "000"
        elif sample == 1:
            binSample = "001"
        elif sample == 2:
            binSample = "010"
        elif sample == 4:
            binSample = "011"
        elif sample == 8:
            binSample = "100"
        elif sample == 16:
            binSample = "101"
        return binSample

    if mode == "Sleep":
        modeBin = "00"
    elif mode == "Forced":
        modeBin = "01"
    elif mode == "Normal":
        modeBin = "11"

    if stnby == 0.5:
        stnbyBin = "000"
    elif stnby == 62.5:
        stnbyBin = "001"
    elif stnby == 125:
        stnbyBin = "010"
    elif stnby == 250:
        stnbyBin = "011"
    elif stnby == 500:
        stnbyBin = "100"
    elif stnby == 1000:
        stnbyBin = "101"
    elif stnby == 10:
        stnbyBin = "110"
    elif stnby == 20:
        stnbyBin = "111"

    if filter_coef == 0:
        filterBin = "000"
    elif filter_coef == 2:
        filterBin = "001"
    elif filter_coef == 4:
        filterBin = "010"
    elif filter_coef == 8:
        filterBin = "011"
    elif filter_coef == 16:
        filterBin = "100"

    t_binSample = sampleBin(t_sample)
    p_binSample = sampleBin(p_sample)
    h_binSample = sampleBin(h_sample)
    ctrl_meas_Bin = t_binSample + p_binSample + modeBin
    ctrl_meas_WORD = int(ctrl_meas_Bin, 2)

    ctrl_hum_WORD = int(h_binSample, 2)

    config_Bin = stnbyBin + filterBin + "0"
    config_WORD = int(config_Bin, 2)

    t_typ = (1 + (2*t_sample) + (2*p_sample + 0.5) + (2*h_sample + 0.5))/1000
    t_max = (1 + (2.3*t_sample) + (2.3*p_sample + 0.575) + (2.3*h_sample + 0.575))/1000

    measurement_T = t_typ + stnby/1000

    return ctrl_meas_WORD, ctrl_hum_WORD, config_WORD, measurement_T

def readAtmos(i2c_address,ctrl_meas_WORD, ctrl_hum_WORD, config_WORD, measurement_T, data_path, backup_path):

    # Ensure directories exist
    ensure_directory_exists(data_path)
    ensure_directory_exists(backup_path)

    index = 1
    data_file_sd = generate_file_name(data_path, index)
    data_file_usb = generate_file_name(backup_path, index)

    buffer = []
    last_save_time = datetime.now()
    buffer_save_interval = timedelta(seconds=10)  # Save buffer every 10 seconds
    last_buffer_save = datetime.now()
    usb_connected = True

    print("Starting data logging...")

    i2cbus.write_byte_data(i2c_address,r_dict["reset_REG"],reset_WORD)

    i2cbus.write_byte_data(i2c_address,r_dict["config_REG"],config_WORD)

    i2cbus.write_byte_data(i2c_address,r_dict["ctrl_hum_REG"],ctrl_hum_WORD)
    i2cbus.write_byte_data(i2c_address,r_dict["ctrl_meas_REG"],ctrl_meas_WORD)
    
    try:
        while(True):
            status_data = i2cbus.read_byte_data(i2c_address,r_dict["status_REG"])
            #print(bin(status_data))
            time.sleep(measurement_T)
            if status_data == 0:
                pressure = i2cbus.read_i2c_block_data(i2c_address, r_dict["press_msb_REG"], 3)
                pressureBinary = "".join([format(val, '#010b')[2:] for val in pressure])[0:-4]
                pressureInt = int(pressureBinary, 2)
                #  perform compensation
                
                
                temperature = i2cbus.read_i2c_block_data(i2c_address, r_dict["temp_msb_REG"], 3)
                temperatureBinary = "".join([format(val, '#010b')[2:] for val in temperature])[0:-4]
                temperatureInt = int(temperatureBinary, 2)
                #  perform compensation
                

                humidity = i2cbus.read_i2c_block_data(i2c_address, r_dict["hum_msb_REG"], 2)
                humidityBinary = "".join([format(val, '#010b')[2:] for val in humidity])
                humidityInt = int(humidityBinary, 2)
                #  perform compensation

                buffer.append(f"{pressureInt},{temperatureInt},{humidityInt}")

                # Save buffer to files every 10 seconds
                if datetime.now() - last_buffer_save >= buffer_save_interval and buffer:
                    print(f"[INFO] Writing buffer at {datetime.now().strftime('%H:%M:%S')}...")
                    
                    # Save to SD
                    save_buffer_to_sd(data_file_sd, buffer)

                    # Save to USB if connected
                    if usb_connected:
                        usb_connected = save_buffer_to_usb(data_file_usb, buffer)

                    buffer.clear()  # Clear buffer after writing
                    last_buffer_save = datetime.now()

                # Create a new file every 5 minutes
                if (datetime.now() - last_save_time).total_seconds() >= 60:
                    print(f"\n[INFO] Creating new file at {datetime.now().strftime('%H:%M:%S')}")
                    last_save_time = datetime.now()
                    index += 1
                    data_file_sd = generate_file_name(data_path, index)
                    data_file_usb = generate_file_name(backup_path, index)
    except (ValueError, IOError) as err:
        print(f"[ERROR] {err}")
            
            
def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def generate_file_name(base_dir, index):
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"gps_data_{current_time}_{index}.txt"
    return os.path.join(base_dir, file_name)

def save_buffer_to_sd(file_path_sd, buffer):
    try:
        with open(file_path_sd, 'ab') as f_sd:
            f_sd.writelines(buffer)
            f_sd.flush()
        print(f"[INFO] Finished writing buffer to SD ({file_path_sd}).")
    except Exception as e:
        print(f"[ERROR] Failed to save data to SD: {e}")

def save_buffer_to_usb(file_path_usb, buffer):
    try:
        with open(file_path_usb, 'ab') as f_usb:
            f_usb.writelines(buffer)
            f_usb.flush()
        print(f"[INFO] Finished writing buffer to USB ({file_path_usb}).")
        return True
    except Exception:
        print("[WARNING] USB connection lost. Data will be saved to SD only.")
        return False


if __name__ == "__main__":

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("i2c", help="i2c address for atmospheric sensor", type=str)
    parser.add_argument(
            "--data",
            default="/usr/local/daedalus/data",
            help="Path of the directory where recordings are stored",
        )
    parser.add_argument(
            "--backup",
            default="/mnt/data",
            help="Path of the directory where recordings are backed up",
        )
    args = parser.parse_args()
    ctrl_meas_WORD, ctrl_hum_WORD, config_WORD, measurement_T = atmosInit()
    
    print(measurement_T)
    
    readAtmos(int(args.i2c, 16), args.data, args.backup, ctrl_meas_WORD, ctrl_hum_WORD, config_WORD, measurement_T)

