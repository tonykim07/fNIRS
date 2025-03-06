import serial
import csv
import time

# Serial port setup — adjust for your Mac's port
ser = serial.Serial('/dev/tty.usbmodem205D388A47311', 9600, timeout=1)

# Create and open a CSV file
csv_file = 'serial_data.csv'
with open(csv_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Timestamp (s)', 'Value'])  # CSV header

    start_time = time.time()

    try:
        print(f"Recording data to {csv_file}... Press Ctrl+C to stop.")
        while True:
            if ser.in_waiting >= 2:
                raw = ser.read(2)
                value = int.from_bytes(raw, byteorder='little', signed=False)
                timestamp = time.time() - start_time
                writer.writerow([timestamp, value])
    except KeyboardInterrupt:
        print(f"\nData recording stopped. File saved as '{csv_file}'.")

# Close serial port
ser.close()
