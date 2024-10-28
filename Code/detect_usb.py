import os
import subprocess
import time
import random

# Configuration
MOUNT_POINT = '/mnt/data/pi_pic'
DEVICE_BASE_PATH = '/dev/sd'  # Base path for USB drives

def detect_device():
    """Detect connected USB drive."""
    try:
        devices = subprocess.check_output("lsblk -o NAME,TYPE -dn", shell=True).decode().strip().split('\n')
        for device in devices:
            name, dev_type = device.split()
            if dev_type == 'disk' and name.startswith('sd'):
                return f'/dev/{name}1'  # Assuming first partition
    except subprocess.CalledProcessError as e:
        print(f"Error detecting device: {e}")
    return None

def get_filesystem_type(device_path):
    """Detect filesystem type of the device."""
    try:
        fs_type = subprocess.check_output(['sudo', 'blkid', '-o', 'value', '-s', 'TYPE', device_path]).decode().strip()
        return fs_type
    except subprocess.CalledProcessError as e:
        print(f"Error detecting filesystem type for {device_path}: {e}")
        return None

def is_mounted(mount_point):
    """Check if the mount point is already mounted."""
    return os.path.ismount(mount_point)

def mount_usb(device_path, mount_point):
    """Mount the USB drive."""
    fs_type = get_filesystem_type(device_path)
    if fs_type:
        try:
            if not os.path.exists(mount_point):
                os.makedirs(mount_point)

            subprocess.run(['sudo', 'mount', '-t', fs_type, device_path, mount_point], check=True)
            print(f"Mounted {device_path} to {mount_point} with {fs_type} filesystem")
        except OSError as e:
            print(f"Error creating mount directory: {e}")
        except subprocess.CalledProcessError as e:
            print(f"Error mounting {device_path}: {e}")
    else:
        print(f"Could not detect filesystem type for {device_path}")

def unmount_usb(mount_point):
    """Unmount the USB drive."""
    try:
        subprocess.run(['sudo', 'umount', mount_point], check=True)
        print(f"Unmounted {mount_point}")
    except subprocess.CalledProcessError as e:
        print(f"Error unmounting {mount_point}: {e}")

def write_random_word(mount_point):
    """Write a random word to a text file on the mounted USB drive."""
    try:
        random_word = random.choice(['apple', 'banana', 'cherry', 'date', 'elderberry'])
        write_dir = os.path.join(mount_point, 'pi_random')
        
        if not os.path.exists(write_dir):
            os.makedirs(write_dir)

        file_path = os.path.join(write_dir, 'random_word.txt')
        with open(file_path, 'w') as f:
            f.write(random_word)

        print(f"Wrote random word '{random_word}' to {file_path}")
    except OSError as e:
        print(f"Error writing to {write_dir}: {e}")

def main():
    """Continuously monitor for USB drive connections, handle mounting/unmounting, and write random word."""
    prev_device = None

    while True:
        try:
            device_path = detect_device()

            if device_path:
                print("USB drive detected.")
                if device_path != prev_device:
                    if not is_mounted(MOUNT_POINT):
                        print("Mounting USB drive...")
                        mount_usb(device_path, MOUNT_POINT)

                    if is_mounted(MOUNT_POINT):
                        write_random_word(MOUNT_POINT)  # Write to the USB after successful mounting
                    prev_device = device_path
            else:
                print("No USB drive detected.")
                if prev_device and is_mounted(MOUNT_POINT):
                    print("Unmounting USB drive...")
                    unmount_usb(MOUNT_POINT)
                    prev_device = None

        except Exception as e:
            print(f"Unexpected error: {e}")

        # Wait before the next check
        time.sleep(2)

if __name__ == '__main__':
    main()





# import pyudev
# import os
# import time
# import subprocess
# from datetime import datetime

# # Base directories for USB and SD
# USB_MOUNT_PATH = "/mnt/data/gps"
# SD_PATH = "/usr/local/daedalus/data/gps"
# WRITE_INTERVAL = 1  # Interval for writing data in seconds

# def get_usb_device():
#     """Find the first available USB device."""
#     context = pyudev.Context()
#     for device in context.list_devices(subsystem='block', DEVTYPE='partition'):
#         if 'ID_USB_DRIVER' in device:
#             return device.device_node
#     return None

# def is_usb_mounted():
#     """Check if the USB device is mounted to the specified path."""
#     return os.path.ismount(USB_MOUNT_PATH)

# def mount_usb(device):
#     """Mount the USB device to the specified path."""
#     try:
#         if is_usb_mounted():
#             print(f"USB already mounted at {USB_MOUNT_PATH}")
#             return True

#         # Check if another process is using the device
#         result = subprocess.run(['fuser', device], capture_output=True, text=True)
#         if result.stdout:
#             print(f"Device {device} is currently in use by another process.")
#             return False

#         subprocess.run(['sudo', 'mount', '-t', 'ntfs', device, USB_MOUNT_PATH], check=True)
#         print(f"Mounted {device} at {USB_MOUNT_PATH}")
#         return True

#     except subprocess.CalledProcessError as e:
#         print(f"Failed to mount {device}: {e}")
#     return False


# def unmount_usb():
#     """Unmount the USB device from the specified path."""
#     try:
#         if is_usb_mounted():
#             subprocess.run(['sudo', 'umount', '-l', USB_MOUNT_PATH], check=True)
#             print(f"Unmounted USB from {USB_MOUNT_PATH}")
#     except subprocess.CalledProcessError as e:
#         print(f"Failed to unmount USB: {e}")

# def create_new_file(base_path, prefix="data"):
#     """Create a new file with a timestamped name."""
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     file_path = os.path.join(base_path, f"{prefix}_{timestamp}.txt")
#     return file_path

# def save_data(sd_file_path, usb_file_path):
#     """Save data to SD, USB, or both, depending on availability."""
#     try:
#         with open(sd_file_path, "a") as sd_file, \
#              open(usb_file_path, "a") if usb_file_path else None as usb_file:

#             while True:
#                 if is_usb_mounted() and usb_file:
#                     data = "Data saved to both USB and SD.\n"
#                     sd_file.write(data)
#                     sd_file.flush()
#                     usb_file.write(data)
#                     usb_file.flush()
#                     print("Data saved to both USB and SD.")
#                 elif usb_file_path and not is_usb_mounted():
#                     print("USB disconnected, saving to SD only.")
#                     data = "Data saved to SD only.\n"
#                     sd_file.write(data)
#                     sd_file.flush()
#                 else:
#                     print("Saving to SD only.")
#                     data = "Data saved to SD only.\n"
#                     sd_file.write(data)
#                     sd_file.flush()

#                 time.sleep(WRITE_INTERVAL)

#                 # Stop writing to USB if unmounted
#                 if usb_file_path and not is_usb_mounted():
#                     break
#     except Exception as e:
#         print(f"Error saving data: {e}")

# def usb_monitor():
#     """Monitor USB events and handle file saving."""
#     print("Monitoring USB events in real-time...")

#     while True:
#         usb_device = get_usb_device()
#         sd_file_path = create_new_file(SD_PATH, "sd_data")
        
#         if usb_device:
#             if not is_usb_mounted() and mount_usb(usb_device):
#                 usb_file_path = create_new_file(USB_MOUNT_PATH, "usb_data")
#                 print(f"Writing to both USB and SD.")
#                 save_data(sd_file_path, usb_file_path)
#             elif is_usb_mounted():
#                 usb_file_path = create_new_file(USB_MOUNT_PATH, "usb_data")
#                 print(f"Writing to both USB and SD.")
#                 save_data(sd_file_path, usb_file_path)
#             else:
#                 print("Mount failed, retrying in 2 seconds...")
#                 time.sleep(2)  # Add delay to prevent spamming mount attempts
#         else:
#             if is_usb_mounted():
#                 unmount_usb()
#             print("USB not found, writing to SD only.")
#             save_data(sd_file_path, None)

#         # Wait 1 second before checking again
#         time.sleep(1)

# if __name__ == "__main__":
#     usb_monitor()