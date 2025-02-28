import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# Configure your serial port
import serial
from serial.tools.list_ports import comports

# for port in comports():
#     print(port)

# Configure your serial port
ser = serial.Serial('/dev/cu.usbmodem143303', 115200, timeout=1)  # Replace 'COMx' with your port

# Initialize data list
data = []

# ser.open()

# Update function for real-time plotting
def update(frame):
    global data
    if ser.in_waiting:
        try:
            # Read ADC value
            line = ser.readline().decode('utf-8').strip()
            value = int(line)
            data.append(value)
            print("VALUE: ", value)
            
            # Limit the length of the data list
            if len(data) > 100:
                data.pop(0)
            
            # Clear and plot the new data
            plt.cla()
            plt.plot(data, label="ADC Value")
            plt.legend(loc="upper right")
            plt.xlabel("Sample")
            plt.ylabel("ADC Value")
            plt.ylim(0, 4095)  # For 12-bit ADC
        except ValueError:
            pass  # Ignore invalid data

# Configure the plot
fig, ax = plt.subplots()
ani = FuncAnimation(fig, update, interval=100)  # Adjust interval for your sampling rate
plt.show()

ser.close()

# ser = serial.Serial(
#     port='usbmodem141303', #/dev/tty.usbmodem141303
#     baudrate=115200,
#     parity=serial.PARITY_NONE,
#     stopbits=serial.STOPBITS_ONE,
#     bytesize=serial.EIGHTBITS
# )

# while(True):
#     print(ser.readline())

# ser.close()