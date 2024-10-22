"""
Guides user through the process of setting up hardware
Used to be called setup.py, still does roughly the same things
"""

import serial
import time
import pyvisa
import numpy as np
import sys
import os

from helper_code.equipment_control.Equipment_Control_Malachi import *
from helper_code.helper_functions import *

def hardware_setup_generation(hw_file_name, scope, HV_supply, LV_supply, arduino):
    input("\nFor the following hardware setup, it is expected the user will be able to adjust scope parameters based on the waveforms if necessary. Press enter to continue.\n")
    input("Please ensure all four probes are connected to the scope and have beeen compensated. Press enter when complete.\n")
    
    # Acquire probe attenuations and set up the scope
    probe_attenuations = [0, 0, 0, 0] # to hold probe attenuation values
    for probe in range(len(probe_attenuations)):
        probe_attenuations[probe] = \
            input('Please enter the attenuation factor for probe ' + str(probe + 1) + ': ')
    print('\n') # for purdy
    general_scope_activation(scope, probe_attenuations)
    
    # Connect probes and set coupling of each probe to DC
    input("Please connect probe for Vout+ to channel 1, Vout- to channel 2, Vgate to channel 3, and Vref to channel 4. Press enter when complete.\n")
    
    # Calibrate Cref
    C_ref = float(input("Please install the reference capacitor onto the bottom slot and enter the value of C_ref [in units of pF]: "))
    C_cal = float(input("\nPlease install a low-loss capacitor of known value C_cal onto the top slot (where the DUT normally goes). Please enter the value of C_cal [in units of pF]: "))
    print('\n')
    
    # Go to a previously set operating point to calibrate cdiv ratios
    general_arduino_activation(arduino, freq=2, duty_ref=3.5, trap=True) # set the arduino up
    general_LV_supply_activation(LV_supply) # set the LV_supply up
    make_user_calibrate_inductors(LV_supply, arduino)
    set_inductor_positions(LV_supply, arduino, 2000, 2000) # pre-chosen points
    
    # First Cdiv test point: 100V trapezoid
    print('setting to 100V...')
    HV_supply.setVoltage(100)
    time.sleep(1)
    print(' done\n')
    turn_system_on(HV_supply, LV_supply, arduino)
    input('Please adjust the scope such that at least two cycles of the waveform appear, then press enter.\n')
    probe1_vamp_100 = float(scope.queryMeasItem("VAMP", 1))/100 # measured divided by true value
    probe2_vamp_100 = float(scope.queryMeasItem("VAMP", 2))/100
    probe4_vamp_100 = abs(float(scope.queryMeasItem("VAMP", 4))/(100*(C_ref - C_cal)/(C_ref + C_cal)))
    time.sleep(1)
    turn_system_off(HV_supply, LV_supply, arduino)
    
    # Second Cdiv test point: 150V trapezoid
    print('setting to 150V...')
    HV_supply.setVoltage(150)
    time.sleep(1)
    print(' done\n')
    turn_system_on(HV_supply, LV_supply, arduino)
    input('Please adjust the scope such that at least two cycles of the waveform appear, then press enter.\n')
    probe1_vamp_150 = float(scope.queryMeasItem("VAMP", 1))/150
    probe2_vamp_150 = float(scope.queryMeasItem("VAMP", 2))/150
    probe4_vamp_150 = abs(float(scope.queryMeasItem("VAMP", 4))/(150*(C_ref - C_cal)/(C_ref + C_cal)))
    time.sleep(1)
    turn_system_off(HV_supply, LV_supply, arduino)
    
    # Third Cdiv test point: 200V trapezoid
    print('setting to 200V...')
    HV_supply.setVoltage(200)
    time.sleep(1)
    print(' done\n')
    turn_system_on(HV_supply, LV_supply, arduino)
    input('Please adjust the scope such that at least two cycles of the waveform appear, then press enter.\n')
    probe1_vamp_200 = float(scope.queryMeasItem("VAMP", 1))/200
    probe2_vamp_200 = float(scope.queryMeasItem("VAMP", 2))/200
    probe4_vamp_200 = abs(float(scope.queryMeasItem("VAMP", 4))/(200*(C_ref - C_cal)/(C_ref + C_cal)))
    time.sleep(1)
    turn_system_off(HV_supply, LV_supply, arduino)
    
    probe1_Cdiv_ratio = (probe1_vamp_100+probe1_vamp_150+probe1_vamp_200)/3
    probe2_Cdiv_ratio = (probe2_vamp_100+probe2_vamp_150+probe2_vamp_200)/3
    probe4_Cdiv_ratio = (probe4_vamp_100+probe4_vamp_150+probe4_vamp_200)/3
    
    # write hardware file for future reference
    with open(hw_file_name, 'w') as file:
        file.write('Title: '+hw_file_name.split('/')[1][:-4] + '\n') # isolate name
        for probe in range(len(probe_attenuations)):
            file.write('probe' + str(probe+1) + '_attenuation: ' + \
                       str(probe_attenuations[probe]) + '\n')
        file.write('probe1_cdiv: ' + str(probe1_Cdiv_ratio) + '\n')
        file.write('probe2_cdiv: ' + str(probe2_Cdiv_ratio) + '\n')
        file.write('probe4_cdiv: ' + str(probe4_Cdiv_ratio) + '\n')
        
    print('Hardware setup file written\n')
        
    
    
    
    