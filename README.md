# A Wearable Functional Near-Infrared Spectroscopy (fNIRS) based Brain Interface

<img src="https://github.com/user-attachments/assets/65a19ef1-c1dc-497d-811f-7cd12f50e027" alt="Device Overview" width="400"/>

## Project Overview

This project introduces a low-cost, ergonomic functional Near-Infrared Spectroscopy (fNIRS) device designed for real-time brain activity monitoring. fNIRS is a non-invasive technique that uses near-infrared light to measure changes in blood oxygenation, providing insights into neural activity based on the modified Beer-Lambert Law.

While conventional fNIRS systems are expensive, bulky, and limited to clinical environments, this system is designed to be accessible, accurate, and user-friendly—ideal for education, personal health tracking, and portable research applications.

## System Highlights

- 24 custom sensor modules:
- 16 photodiode detector boards
- 8 emitter-detector boards with dual-wavelength LEDs (660 nm & 940 nm)

## Custom ECU

- Built around a low-power STM32 microcontroller
- Interfaces with all sensor modules for synchronized control and data acquisition
- Ergonomic mechanical design for secure, comfortable wear during extended sessions
- Interactive Python-based GUI for live data visualization, serial communication, and module control
