# -*- coding: utf-8 -*-
"""
Created on Mon Jun 24 11:44:23 2024

@author: hornb
"""

from helper_code.equipment_control.Equipment_Control_Malachi import MSO5000, GENH600, DP832
from helper_code.equipment_control.arduino_coss_communication import POWAM_MICRO
from helper_code.helper_functions import *
from hardware_setup_generation import *
from running_operating_points import *
import os
import numpy as np

"""
-------------------------------------------------------------------------------
BEGIN USER-DEFINED VARIABLES:
-------------------------------------------------------------------------------
"""

"""
Hardware addresses and instrument instantiation:
"""
scope = MSO5000('USB0::0x1AB1::0x0515::MS5A243807653::INSTR')
HV_supply = GENH600('COM7')
LV_supply = DP832('USB0::0x1AB1::0x0E11::DP8C193504111::INSTR')
arduino = POWAM_MICRO('COM5')


"""
Either calibrate for a new hardware setup, or use an existing calibration:
"""
create_new_hardware_setup = False # boolean for whether to calibrate new setup
hw_setup_file = '0719_gs66504b_sweep_cal' # file to either create or use


"""
Name the run so its operating points can be stored in a run documentation file
"""
run_doc_folder = '0801_gs66504b_trap_450v_2mhz'
run_comments = 'Just running to get some videos of the automation.'
    # Add any comments to be included in the summary file (eg DUT name)


"""
General sweep or single measurement point parameters:
    For single measurement point, enter parameters as you would like
    For sweep, make the desired variable a list, eg [val1, val2, ...]
"""
freq = 2 # [MHz] output waveform frequency
v_pp = 450 # [V] Sawyer Tower voltage pp amplitude: 0 to 1200 Volts
cref = 516 # [pF] Reference capacitor value (under DUT in ST circuit)
cideal = 204 # [pF] Ideal capacitor used for loss calibrations:
    # (Should be similar to the average COSS value on the DUT)
trap = True # True for trapezoidal waveform, False for sinusoidal

# Trapezoidal waveform variables: can be set to whatever if running sine
trap_dvdt = [0.3, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7] # Fraction of a quarter-wavelength trap transisiton should last
    # eg "1" means the overall differential waveform will be:
        # 25% of the time Vcc
        # 25% of the time ramping down
        # 25% of the time -Vcc
        # 25% of the time ramping up
    # recommended to not really go below 0.2-3 or above 0.7-8; reduces waveform quality

"""
-------------------------------------------------------------------------------
END USER-DEFINED VARIABLES
-------------------------------------------------------------------------------
"""

"""
Hardware file generation and/or read-in (probe attenuation and cdiv ratios):
"""
# Either create or read in hardware file
hw_setup_file = 'hardware_setup_files/' + hw_setup_file + '.txt'
if create_new_hardware_setup: # do calibration, write hardware setup file
    hardware_setup_generation(hw_setup_file,
                              scope, HV_supply, LV_supply, arduino)
else: # not creating a hardware setup file
    make_user_calibrate_inductors(LV_supply, arduino) # ensure inductors good
    general_LV_supply_activation(LV_supply) # set the LV_supply up
# read in data from the hardware setup file
[probe_attenuations, probe_cdivs] = read_hardware_setup_file(hw_setup_file)
    # probe attenuations is [probe1, probe2, probe3, probe4] (20, 20, 10, 20 for us)
    # probe cdivs is [probe1, probe2, probe4] (probe 3 on gate has no cdiv)
general_scope_activation(scope, probe_attenuations)

"""
Generate sweep parameters: determine which (if any) variable is sweeping
"""
# determine whether we're sweeping a variable or running a single operating point
operating_condition = determine_operating_condition(freq, v_pp, trap, trap_dvdt)
    # 0 = single point ; 1 = sweep freq ; 2 = sweep v_pp ; 3 = sweep trap_dvdt


"""
Measurement stage 1: Use ideal capacitor to calibrate deskewing:
"""
input('Place the ideal capacitor of value ' + str(cideal) + 'pF in place of the DUT. Press enter to continue.\n')
run_doc_folder = 'run_documentation_files/' + run_doc_folder + '/'
run_operating_points_Cideal(freq, v_pp, trap, trap_dvdt, probe_cdivs, cref, cideal,
                          run_doc_folder, run_comments, operating_condition,
                          scope, HV_supply, LV_supply, arduino)


"""
Measurement stage 2: Measure waveforms at same operating points with DUT
"""
input('\nReplace the ideal capacitor with the DUT for COSS loss measurements. Press enter to continue.\n')
Ediss_values = run_operating_points_DUT(freq, v_pp, trap, trap_dvdt, probe_cdivs, cref,
                         run_doc_folder, operating_condition,
                         scope, HV_supply, LV_supply, arduino)
save_ediss_data_csv(run_doc_folder + 'Ediss_data.csv', Ediss_values, operating_condition, freq, v_pp, trap_dvdt)


"""
Possibly some post-processing or something like that here. Make some trend plots
"""









