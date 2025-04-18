# fNIRS Firmware

The firmware runs on the fNIRS ECU consisting of an STM32L476RET6 microcontroller.

## Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/tonykim07/fNIRS.git
   ```

2. **Open STM32CubeIDE using the `/firmware/STM32/` as the workspace directory**

3. **Clean the project, then click Build to compile the project**
   
4. **Connect an STLINK or STM32 Nucleo to the fNIRS ECU programming header (SWD Programming) and click Run to flash the board**
