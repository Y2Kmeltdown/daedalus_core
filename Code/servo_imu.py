import time
import board
import adafruit_icm20x
import serial
from serial.serialutil import SerialException

# Initialize the IMU
i2c = board.I2C()
icm = adafruit_icm20x.ICM20948(i2c, 0x69)

# Initialize the serial connection to Teensy
teensy_serial = serial.Serial('/dev/ttyACM1', 115200)  # Adjust port as necessary


# Low-pass filter constants for gyroscope data
alpha = 0.1  # Smoothing factor, adjust between 0 (smooth) to 1 (responsive)
gyro_x_filtered = 0
gyro_y_filtered = 0
gyro_z_filtered = 0

def calculate_servo_angles(gyro_x, gyro_y, gyro_z):
    """
    Calculate servo angles for each wing based on gyroscope rotation.
    gyro_x: pitch rotation rate (x-axis)
    gyro_y: roll rotation rate (y-axis)
    gyro_z: yaw rotation rate (z-axis)
    Returns a tuple of angles (left_servo_angle, right_servo_angle)
    """
    # Control constants
    gain_x = 50  # Control gain for pitch adjustment
    gain_z = 10  # Control gain for yaw adjustment
    base_angle = 90  # Neutral angle for stability

    # Calculate pitch and yaw adjustments, inverted for counteracting motion
    pitch_adjustment = -gain_x * gyro_x
    yaw_adjustment = -gain_z * gyro_z
    
    # Adjust each servo angle based on pitch and yaw adjustments
    left_servo_angle = base_angle + pitch_adjustment + yaw_adjustment
    right_servo_angle = base_angle + pitch_adjustment - yaw_adjustment

    # Constrain the servo angles within [0, 180]
    left_servo_angle = max(0, min(180, int(left_servo_angle)))
    right_servo_angle = max(0, min(180, int(right_servo_angle)))

    return left_servo_angle, right_servo_angle

def main():
    global gyro_x_filtered, gyro_y_filtered, gyro_z_filtered  # To hold the filtered gyro values

    try:
        while True:
            # Read raw gyroscope data
            gyro = icm.gyro
            gyro_x_raw = gyro[0]
            gyro_y_raw = gyro[1]
            gyro_z_raw = gyro[2]
            
            # Apply low-pass filter to smooth the gyro readings
            gyro_x_filtered = alpha * gyro_x_raw + (1 - alpha) * gyro_x_filtered
            gyro_y_filtered = alpha * gyro_y_raw + (1 - alpha) * gyro_y_filtered
            gyro_z_filtered = alpha * gyro_z_raw + (1 - alpha) * gyro_z_filtered

            # Calculate the servo angles based on the filtered gyro data
            left_servo, right_servo = calculate_servo_angles(gyro_x_filtered, gyro_y_filtered, gyro_z_filtered)

            # Attempt to send the calculated angles to Teensy with error handling
            try:
                teensy_serial.write(f"{left_servo},{right_servo}\n".encode())
                print(f"Sent angles - Left: {left_servo}, Right: {right_servo}")
            except SerialException as e:
                print(f"Serial write failed: {e}")
                # Attempt to close and reopen the serial connection after an error
                teensy_serial.close()
                time.sleep(1)  # Wait before trying to reconnect
                try:
                    teensy_serial.open()
                    print("Reconnected to Teensy.")
                except SerialException as e:
                    print(f"Reconnection failed: {e}")
                    break  # Exit the loop if reconnection fails

            time.sleep(0.1)  # Adjust delay for responsiveness

    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        teensy_serial.close()

if __name__ == "__main__":
    main()
