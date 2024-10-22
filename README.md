# automated-sawyer-tower



## Overview

Code to interface with hybrid converter and control system for Sawyer-Tower Coss loss measurements.

The setup includes a hyrbid converter connected to a control board. The control board communicates with a computer running this directory in python. Additionally the computer controls the two 12V supplies and 600V supply needed for operation, along with an oscilloscope to facilitate automated tuning and data collection.

Following are brief explanations the files and folders in this main directory:

## helper_code

This is the default directory for storing functions.

*   **equipment_control**: contains classes and files associated with equipment control
    *   **arduino_coss_communication** for ATMEGA328P running the code
    *   **arduino_coss_communication_example** is a short example of how to interact with the ATMEGA328P microcontroller in code
    *   **Equipment_Control_Malachi** for equipment control objects
    *   **equipment_control_notes.txt** has some notes on required python libraries, debugging, programming manuals, etc.
    *   **rigol_mso5074_setup+example** is an example of how to interact with the rigols scope
*   **unused_references**: a collection of not currently used code but may be useful for alternate implementations
    *   **duty_cycle_tuning** was an old version of the trapezoidal duty cycle tuning code
    *   **inductor_tuning.py** has the old code for tuning inductors that later evolved into the algorithm actually used
    *   **skew_optimization** is the original code for optimizing skew using minimum mean square error method
*   **helper_functions**: The primary file that holds the majority of the functions needed to make this program work, organized by each function's purpose
    

## data_analysis_(sine/trap)_butter.py

Files for analyzing scope data for sine and trap waveforms. They let you play with the processing parameters and generate lots of useful plots with a fairly simple set of controls at the top of the files. They use butterworth low-pass filters to smooth the data, hence the butter in the name.

## data_analysis_trap.py

Same as data_analysis_trap_butter but uses gaussian averaging instead of butterworth low-pass filter.

## running_operating_points.py

Called by user_run_file.py to run a set of operating points given specified parameters.

## user_run_file.py

**This is the main file users should interact with.** Allows you to calibrate hardware, set sweep parameters, and run them. It will step you through basically all the measurements steps:

*   Input things like hardware addresses and run parameters. All you should need to edit is in the user-defined variables section of the code
*   Calibrate your hardware setup by zeroing rolling inductors, probe attenuation, capacitor division ratios, etc. and store that information in a hardware setup file so you only have to do the calibration once per setup
*   Run every operating point in the sweep with an ideal capacitor installed in the Sawyer Tower circuit. The ideal capacitor should be similar in value to what the DUT will present to the circuit, with the caveat that due to C~OSS~ nonlinearity you can never get a perfect match. This is intended to do two main things:
*   Get an idea of what inductor positions will result in the desired waveform so that when the DUT goes on you have a decent starting point for tuning. This should help avoid subjecting the DUT to extreme waveforms that might damage it as it's less robust and more expensive than a simple capacitor
*   Calculate the deskewing that should be applied to two of the channels (the top and bottom switch nodes in this case) for the given voltage waveform excitation. This is done by aligning one of the switch node waveforms to the middle node of the ST circuit graphically (eg minimization of mean square error or some other method) and then sweeping the skew of the other switch node until the calculated Ediss is very close to zero (as would be expected for a high-Q capacitor). Then in theory you use the same deskewing values when the DUT is installed and get an accurate Ediss calculation. We do the deskewing calculation for every operating point since deskewing can depend on things like voltage, frequency, waveform, and so on.
*   Calculate Ediss, store run parameters in a text file, and save scope waveforms to the appropriate folder in run_documentation_files.
    
## user_input_and_run_files

*   Contains files that the user can edit to adjust the state of the converter
