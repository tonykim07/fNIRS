import serial
import time

# Open the serial port
ser = serial.Serial('/dev/cu.usbmodem143303', 115200, timeout=1)  # Replace 'COMx' with your port

def read_data():
    while True:
        # Read the data from the STM32
        data = ser.read(64)  # Read up to 64 bytes (adjust as necessary)
        
        if data:
            print("Received Data:", data)

            # Decode the received bytes into a string for easier parsing
            decoded_data = data.decode('utf-8', errors='ignore')
            print("Decoded Data:", decoded_data)

            parts = decoded_data.split()
            
            if len(parts) > 1:
                # Extract group information and sensor values (assuming the format "G1 S1 S2 S3")
                group = parts[0]  # "G1", "G2", etc.
                sensor1_value = int(parts[1], 16)  # Sensor 1 value (hexadecimal conversion)
                sensor2_value = int(parts[2], 16)  # Sensor 2 value (hexadecimal conversion)
                sensor3_value = int(parts[3], 16)  # Sensor 3 value (hexadecimal conversion)
                
                # Print the parsed values
                print(f"Group: {group}")
                print(f"Sensor 1 Value: {sensor1_value}")
                print(f"Sensor 2 Value: {sensor2_value}")
                print(f"Sensor 3 Value: {sensor3_value}")
        
        time.sleep(0.1)  # Add a small delay between reads

# Run the data reading loop
if __name__ == '__main__':
    try:
        read_data()
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        ser.close()
