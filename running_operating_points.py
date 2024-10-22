# -*- coding: utf-8 -*-
"""
Created on Tue Jul  2 11:20:35 2024

@author: hornb
"""

"""
Used for running both trap and sine operating points alone and in sweeps
"""

import os
import numpy as np
from helper_code.helper_functions import *

def run_operating_points_Cideal(freq, v_pp, trap, trap_dvdt, probe_cdivs, cref, cideal,
                           run_doc_folder, run_comments, operating_condition,
                           scope, HV_supply, LV_supply, arduino):
    # Runs the operating point(s) with Cideal in place for loss calibration:
        # verifies that this run name doesn't exist already, errors if not to avoid overwrite
        # writes the summary file with user comments
        # based on trap/sine and sweep variable, incrementally calls correct operating point functions
        
    check_if_run_doc_dir_exists(run_doc_folder) # make sure this is a new run name
    os.makedirs(run_doc_folder) # make the directory to store run information in
    Cideal_folder = run_doc_folder + 'Cideal_runs/' # to store Cideal runs
    os.makedirs(Cideal_folder) # make the folder to store Cideal runs
    
    # write the summary file for future reference when looking at data
    with open(run_doc_folder + 'summary.txt', 'w') as file:
        if trap:
            file.write(run_comments + '\n')
            file.write('Trapezoid run with sweep type: ' + print_sweep_type(operating_condition) + '\n')
            file.write('Trap dVdt [fraction of quarter-wavelength]: ' + str(trap_dvdt) + '\n')
        else:
            file.write('Sinusoid run with sweep type: ' + print_sweep_type(operating_condition) + '\n')
        file.write('Frequency [MHz]: ' + str(freq) + '\n')
        file.write('Vpp [V]: ' + str(v_pp) + '\n')
        file.write('Reference capacitor [pF]: ' + str(cref) + '\n')
        file.write('Ideal calibration capacitor [pF]: ' + str(cideal) + '\n')
        
    # estimate the resonant capacitances seen in sine and trap modes
    c_st = ((cref*cideal) / (cref+cideal)) # [pf] sawyer tower capacitance
    c_switch = 100 # [pF] GS66504B COSS estimation (average-ish)
    c_diode = 100 # [pF] STPSC20065-Y SiC reverse diode estimation (1250-100 range)
    c_trap = 2*c_st + 2*(c_switch+c_diode) # cap seen during resonant transition
    c_sine = c_st + (c_switch+c_diode) # cap seen during resonant transition
    
    # run the actual operating points for either trap or sine
    if operating_condition == 0: # single operating point
        if trap:
            run_operating_point_Cideal_trap(freq, v_pp, trap_dvdt, probe_cdivs, cref, c_trap,
                                       Cideal_folder + 'single_operating_point.txt',
                                       Cideal_folder + 'single_operating_point.csv',
                                       scope, HV_supply, LV_supply, arduino)
        else:
            run_operating_point_Cideal_sine(freq, v_pp, probe_cdivs, cref, c_sine,
                                        Cideal_folder + 'single_operating_point.txt',
                                        Cideal_folder + 'single_operating_point.csv',
                                        scope, HV_supply, LV_supply, arduino)
    elif operating_condition == 1: # sweeping frequency
        if trap:
            for f in freq:
                run_operating_point_Cideal_trap(f, v_pp, trap_dvdt, probe_cdivs, cref, c_trap,
                                           Cideal_folder + 'freq_' + str(f) + 'MHz.txt',
                                           Cideal_folder + 'freq_' + str(f) + 'MHz.csv',
                                           scope, HV_supply, LV_supply, arduino)
        else:
            for f in freq:
                run_operating_point_Cideal_sine(f, v_pp, probe_cdivs, cref, c_sine,
                                            Cideal_folder + 'freq_' + str(f) + 'MHz.txt',
                                            Cideal_folder + 'freq_' + str(f) + 'MHz.csv',
                                            scope, HV_supply, LV_supply, arduino)
    elif operating_condition == 2: # sweeping v_pp
        if trap:
            for v in v_pp:
                run_operating_point_Cideal_trap(freq, v, trap_dvdt, probe_cdivs, cref, c_trap,
                                           Cideal_folder + 'v_pp_' + str(v) + 'V.txt',
                                           Cideal_folder + 'v_pp_' + str(v) + 'V.csv',
                                           scope, HV_supply, LV_supply, arduino)
        else:
            for v in v_pp:
                run_operating_point_Cideal_sine(freq, v, probe_cdivs, cref, c_sine,
                                           Cideal_folder + 'v_pp_' + str(v) + 'V.txt',
                                           Cideal_folder + 'v_pp_' + str(v) + 'V.csv',
                                           scope, HV_supply, LV_supply, arduino)
    else: # sweeping dvdt, only relevant for trap
        for d in trap_dvdt:
            run_operating_point_Cideal_trap(freq, v_pp, d, probe_cdivs, cref, c_trap,
                                       Cideal_folder + 'trap_dvdt_' + str(d) + '.txt',
                                       Cideal_folder + 'trap_dvdt_' + str(d) + '.csv',
                                       scope, HV_supply, LV_supply, arduino)
            
def run_operating_points_DUT(freq, v_pp, trap, trap_dvdt, probe_cdivs, cref,
                             run_doc_folder, operating_condition,
                             scope, HV_supply, LV_supply, arduino):
    # Runs the operating point(s) with a DUT installed:
        # creates folder for storing DUT run data
        # incrementally calls the correct operating point function based on sweep
    # Returns Ediss values from sweep as a list
    
    Cideal_folder = run_doc_folder + 'Cideal_runs/' # to read Cideal runs from earlier
    DUT_folder = run_doc_folder + 'DUT_runs/' # to store DUT run data
    os.makedirs(DUT_folder)
    
    Ediss_values = []
    # Based on operating_condition, call the correct operating point function
    if operating_condition == 0: # single operating point
        if trap:
            Ediss_values.append(run_operating_point_DUT_trap(freq, v_pp, trap_dvdt, probe_cdivs, cref,
                                    Cideal_folder + 'single_operating_point.txt',
                                    DUT_folder + 'single_operating_point.txt',
                                    DUT_folder + 'single_operating_point.csv',
                                    scope, HV_supply, LV_supply, arduino))
        else:
            Ediss_values.append(run_operating_point_DUT_sine(freq, v_pp, probe_cdivs, cref,
                                    Cideal_folder + 'single_operating_point.txt',
                                    DUT_folder + 'single_operating_point.txt',
                                    DUT_folder + 'single_operating_point.csv',
                                    scope, HV_supply, LV_supply, arduino))
    elif operating_condition == 1: # sweeping frequency
        if trap:
            for f in freq:
                Ediss_values.append(run_operating_point_DUT_trap(f, v_pp, trap_dvdt, probe_cdivs, cref,
                                        Cideal_folder + 'freq_' + str(f) + 'MHz.txt',
                                        DUT_folder + 'freq_' + str(f) + 'MHz.txt',
                                        DUT_folder + 'freq_' + str(f) + 'MHz.csv',
                                        scope, HV_supply, LV_supply, arduino))
        else:
            for f in freq:
                Ediss_values.append(run_operating_point_DUT_sine(f, v_pp, probe_cdivs, cref,
                                        Cideal_folder + 'freq_' + str(f) + 'MHz.txt',
                                        DUT_folder + 'freq_' + str(f) + 'MHz.txt',
                                        DUT_folder + 'freq_' + str(f) + 'MHz.csv',
                                        scope, HV_supply, LV_supply, arduino))
    elif operating_condition == 2: # sweeping v_pp
        if trap:
            for v in v_pp:
                Ediss_values.append(run_operating_point_DUT_trap(freq, v, trap_dvdt, probe_cdivs, cref,
                                        Cideal_folder + 'v_pp_' + str(v) + 'V.txt',
                                        DUT_folder + 'v_pp_' + str(v) + 'V.txt',
                                        DUT_folder + 'v_pp_' + str(v) + 'V.csv',
                                        scope, HV_supply, LV_supply, arduino))
        else:
            for v in v_pp:
                Ediss_values.append(run_operating_point_DUT_sine(freq, v, trap_dvdt, probe_cdivs, cref,
                                        Cideal_folder + 'v_pp_' + str(v) + 'V.txt',
                                        DUT_folder + 'v_pp_' + str(v) + 'V.txt',
                                        DUT_folder + 'v_pp_' + str(v) + 'V.csv',
                                        scope, HV_supply, LV_supply, arduino))
    else: # sweeping dvdt
        for d in trap_dvdt:
            Ediss_values.append(run_operating_point_DUT_trap(freq, v_pp, d, probe_cdivs, cref,
                                    Cideal_folder + 'trap_dvdt_' + str(d) + '.txt',
                                    DUT_folder + 'trap_dvdt_' + str(d) + '.txt',
                                    DUT_folder + 'trap_dvdt_' + str(d) + '.csv',
                                    scope, HV_supply, LV_supply, arduino))
            
    return Ediss_values
            
def check_if_run_doc_dir_exists(run_doc_folder):
    # Checks if the run doc directory already exists:
        # If no, just continues
        # If yes, gives user opportunity to delete it or start over
    if os.path.isdir(run_doc_folder):
        input('This run name: \"' + run_doc_folder + '\" already exists.\n' + \
              'If you want to overwrite the existing run, delete the existing folder and press enter.\n' + \
              'If you want to rename your current run to avoid overwriting, just press enter.\n')
        if os.path.isdir(run_doc_folder):
            raise Exception('Run terminated to avoid overwriting previous run with the same name. Rename the run and try again.\n')    

def run_operating_point_Cideal_trap(freq, v_pp, trap_dvdt, probe_cdivs, cref, c_trap,
                                    op_point_file, data_save_file, scope, HV_supply, LV_supply, arduino):
    # Runs a Cideal trapezoidal operating point:
        # Guesses initial inductor values based on c_trap resonant node capacitance estimate
        # Guesses initial duty_vref based on dvdt (conservatively to avoid losing ZVS):
            # set duty cycle by just measuring it to avoid frequency-dependence
        # tune inductors to hit desired dvdt
        # tune duty cycle to minimize energy
        # tune deskew to minimize energy
        # store operating conditions in operating point file for DUT reference
    print('Running Cideal operating point:\n  ' + str(freq) + ' Mhz' + \
          '\n  ' + str(v_pp) + ' Vpp' + \
          '\n  ' + str(trap_dvdt) + ' trap_dvdt')
        
    window_scope(freq, v_pp, True, probe_cdivs, scope) # set scope window up
    set_channel_deskews(scope, 0, 0, 0, 0) # reset channel deskews to zero
    general_LV_supply_activation(LV_supply)
    HV_supply.setVoltage(v_pp/2)
    
    # set up initial inductor positions and duty cycle using formula guess
    [Lguess, duty] = L_guess_trap(freq, trap_dvdt, c_trap)
    set_inductor_values(LV_supply, arduino, Lguess, Lguess)
    initial_duty_vref = 2.5
    general_arduino_activation(arduino, freq, initial_duty_vref, True)
    duty_vref_rough = set_half_duty_cycle(scope, LV_supply, arduino, duty*0.75, initial_duty_vref)
        # smaller duty cycle to avoid losing ZVS: initial Lguess is just rough
    
    # fine-tune the inductors to reach the desired dv/dt
    print('Calibrating inductors to reach desired dV/dt...')
    true_dvdt = get_true_dvdt(trap_dvdt, freq*1e6, v_pp) # calculate true dvdt [V/s]
    inductor_tuning_trap_scope_based(true_dvdt/2, probe_cdivs,
                                            scope, HV_supply, LV_supply, arduino)
        # Note each channel should see half the true desired dvdt (differential)
    print(' Inductor calibration done.\n')
    
    # duty cycle tuning - minimizing energy seems to improve waveform quality
    turn_system_on(HV_supply, LV_supply, arduino)
    duty_vref_final = duty_cycle_tuning_trap(arduino, scope, HV_supply, duty_vref_rough)
    
    # read the waveform (which has now been somewhat optimized with Cideal)
    print('Reading channels for skew calculation...')
    time.sleep(5) # for AC channels to settle out I guess
    scope_data = scope.readAllChannelsAveraged(5)
    print(' done')
    turn_system_off(HV_supply, LV_supply, arduino)
    
    # Deskew vout+ and vout- relative to vref by minimizing mean square error
    scope_data = scale_scope_data_w_cdivs(scope_data, probe_cdivs) # scale traces by cdiv
    # [ch1_deskew, ch2_deskew] = find_deskew_for_min_MSE(scope_data, freq*1e6, trap_dvdt)
    [ch1_deskew, ch2_deskew] = find_deskew_MSE_Ediss_hybrid(
        scope_data, freq*1e6, trap_dvdt, cref*1e-12)
    
    Ediss = calculate_Ediss_trap(scope_data, freq*1e6, trap_dvdt, cref*1e-12) # may as well calculate
    
    # write the operating point to the operating point file
    with open(op_point_file, 'w') as file:
        file.write('Operating point file number of values: 9\n')
        file.write('Inductor 1 position: ' + str(arduino.l1_pos) + '\n')
        file.write('Inductor 2 position: ' + str(arduino.l2_pos) + '\n')
        file.write('Duty Vref value: ' + str(duty_vref_final) + '\n')
        file.write('Channel 1 deskew: ' + str(ch1_deskew) + '\n')
        file.write('Channel 2 deskew: ' + str(ch2_deskew) + '\n')
        file.write('Ediss without deskew applied: ' + str(Ediss) + '\n')
        file.write('Freq in MHz: ' + str(freq) + '\n')
        file.write('trap_dvdt (fraction of quarter wavelength): ' + str(trap_dvdt) + '\n')
        file.write('Cref [pF]: ' + str(cref) + '\n')
        
    np.savetxt(data_save_file, scope_data, delimiter=',') # save trace data as a .csv
    print(' Finished Cideal operating point.')
    
def run_operating_point_Cideal_sine(freq, v_pp, probe_cdivs, cref, c_sine,
                                    op_point_file, data_save_file, scope, HV_supply, LV_supply, arduino):
    # Runs a Cideal sinusoidal operating point:
        # Guesses initial inductor values based on c_sine resonant node capacitance estimate
        # Set duty cycle basically as high as it can go to minimize reverse diode conduction, though this isn't extremely important
            # At the frequency of interest, just increase until the gate signal disappears and back off to where it was okay
        # tune inductors to get a differential waveform approximating a sinusoid
            # tune each switch node independently to have a bump width of half the period
        # tune deskew to minimize energy
        # store operating conditions in operating point file for DUT reference
    print('Running Cideal operating point:\n  ' + str(freq) + ' Mhz' + \
          '\n  ' + str(v_pp) + ' Vpp')
        
    window_scope(freq, v_pp, False, probe_cdivs, scope) # set scope window up
    set_channel_deskews(scope, 0, 0, 0, 0) # reset channel deskews to zero
    general_LV_supply_activation(LV_supply)
    HV_supply.setVoltage(v_pp/2/np.pi) # since resonant bump will be pi times DC voltage
    
    # set up initial inductor positions
    Lguess = L_guess_sine(freq, c_sine)
    set_inductor_values(LV_supply, arduino, Lguess, Lguess)
    
    # set duty cycle to be large, hopefully over 40%
    initial_duty_vref = 2.5
    general_arduino_activation(arduino, freq, initial_duty_vref, False)
    [duty_vref_final, duty_cycle] = duty_cycle_tuning_sine(arduino, scope, init_duty_vref)
    
    # fine-tune the inductors to get a good sine wave approximation
    print('Calibrating inductors to approximate differential sine wave...')
    inductor_tuning_sine_corner_find(freq, scope, HV_supply, LV_supply, arduino, duty_cycle)
        # Note each channel should see half the true desired dvdt (differential)
    print(' Inductor calibration done.\n')
    
    # read the waveform (which has now been somewhat optimized with Cideal)
    turn_system_on(HV_supply, LV_supply, arduino)
    print('Reading channels for skew calculation...')
    time.sleep(5) # for AC channels to settle out I guess
    scope_data = scope.readAllChannelsAveraged(5)
    print(' done')
    turn_system_off(HV_supply, LV_supply, arduino)
    
    # Deskew vout+ and vout- relative to vref by minimizing mean square error
    scope_data = scale_scope_data_w_cdivs(scope_data, probe_cdivs) # scale traces by cdiv
    # [ch1_deskew, ch2_deskew] = find_deskew_for_min_MSE(scope_data, freq*1e6, trap_dvdt)
    """
    No need to calculate deskewing for sine since we don't use it anyway, so do this instead:
    """
    ch1_deskew = 0
    ch2_deskew = 0
    Ediss = 0
    """
    [ch1_deskew, ch2_deskew] = find_deskew_MSE_Ediss_hybrid(
        scope_data, freq*1e6, trap_dvdt, cref*1e-12)
        # this probably doesn't work for sine but no matter because we don't use this deskewing ultimately anyways
    
    Ediss = calculate_Ediss_trap(scope_data, freq*1e6, trap_dvdt, cref*1e-12) # may as well calculate
    """
    
    # write the operating point to the operating point file
    with open(op_point_file, 'w') as file:
        file.write('Operating point file number of values: 9\n')
        file.write('Inductor 1 position: ' + str(arduino.l1_pos) + '\n')
        file.write('Inductor 2 position: ' + str(arduino.l2_pos) + '\n')
        file.write('Duty Vref value: ' + str(duty_vref_final) + '\n')
        file.write('Channel 1 deskew: ' + str(ch1_deskew) + '\n')
        file.write('Channel 2 deskew: ' + str(ch2_deskew) + '\n')
        file.write('Ediss without deskew applied: ' + str(Ediss) + '\n')
        file.write('Freq in MHz: ' + str(freq) + '\n')
        file.write('trap_dvdt (fraction of quarter wavelength): ' + '0' + '\n')
        file.write('Cref [pF]: ' + str(cref) + '\n')
        
    np.savetxt(data_save_file, scope_data, delimiter=',') # save trace data as a .csv
    print(' Finished Cideal operating point.')
        
def run_operating_point_DUT_trap(freq, v_pp, trap_dvdt, probe_cdivs, cref,
                                 cideal_file, op_point_file, data_write_file,
                                 scope, HV_supply, LV_supply, arduino):
   # Runs an operating point on a DUT, using calibration data from similar Cideal point:
       # Uses Cideal point to learn deskew, inductor positions, and duty Vref
       # Sets duty cycle a bit below Cideal value (probably 75%) to maintain ZVS
       # Sets inductors to Cideal values, then tunes them to match desired dvdt
       # Fine tune duty cycle to minimize HV_supply power, improving waveform
       # Measure and save data, calculate Ediss
   # Returns Ediss calculated Ediss value
   print('Running DUT operating point:\n  ' + str(freq) + ' Mhz' + \
         '\n  ' + str(v_pp) + ' Vpp' + \
         '\n  ' + str(trap_dvdt) + ' trap_dvdt')
   
   window_scope(freq, v_pp, True, probe_cdivs, scope) # set scope window
   general_LV_supply_activation(LV_supply)
   HV_supply.setVoltage(v_pp/2)
   
   # read values from cideal file
   [l1_pos_cideal, l2_pos_cideal, duty_vref_cideal,
        ch1_deskew_cideal, ch2_deskew_cideal, a, b, c, d] = read_colon_file(cideal_file)
   l1_pos_cideal = float(l1_pos_cideal) # values are read in as strings
   l2_pos_cideal = float(l2_pos_cideal)
   duty_vref_cideal = float(duty_vref_cideal)
   ch1_deskew_cideal = float(ch1_deskew_cideal)
   ch2_deskew_cideal = float(ch2_deskew_cideal)
   
   # conservatively set duty cycle for ZVS, also set cideal L-vals and skews
   set_inductor_positions(LV_supply, arduino, l1_pos_cideal, l2_pos_cideal)
   general_arduino_activation(arduino, freq, duty_vref_cideal, True)
   [Lguess_wrong, duty] = L_guess_trap(freq, trap_dvdt, 1e-12)
   duty_vref_rough = set_half_duty_cycle(scope, LV_supply, arduino, duty*0.75, duty_vref_cideal)
   set_channel_deskews(scope, 0, 0, 0, 0) # don't deskew on scope; 500ps minimum skew interval
   
   # fine-tune the inductors to reach the desired dv/dt
   print('Calibrating inductors to reach desired dV/dt...')
   true_dvdt = get_true_dvdt(trap_dvdt, freq*1e6, v_pp) # calculate true dvdt [V/s]
   inductor_tuning_trap_scope_based(true_dvdt/2, probe_cdivs,
                                    scope, HV_supply, LV_supply, arduino)
       # Note each channel should see half the true desired dvdt (differential)
   print(' Inductor calibration done\n')
   
   # duty cycle tuning - minimizing energy seems to improve waveform quality
   turn_system_on(HV_supply, LV_supply, arduino)
   duty_vref_final = duty_cycle_tuning_trap(arduino, scope, HV_supply, duty_vref_rough)
   
   # read the waveform (which has now been somewhat optimized with Cideal)
   print('Reading channels for Ediss calculation...')
   time.sleep(5) # for AC channels to settle out I guess
   scope_data = scope.readAllChannelsAveraged(5)
   print(' done')
   turn_system_off(HV_supply, LV_supply, arduino)
   
   # Calculate Ediss
   scope_data = scale_scope_data_w_cdivs(scope_data, probe_cdivs) # cdiv scaling
   scope_data_deskewed = scope_data.copy() # to leave scope_data alone during saving
   scope_data_deskewed = data_array_time_shift_one_signal(
       scope_data_deskewed, 0, 1, ch1_deskew_cideal)
   scope_data_deskewed = data_array_time_shift_one_signal(
       scope_data_deskewed, 0, 2, ch2_deskew_cideal)
   
   Ediss = calculate_Ediss_trap(scope_data_deskewed, freq*1e6, trap_dvdt, cref*1e-12)
   
   # write the operating point to the operating point file
   with open(op_point_file, 'w') as file:
       file.write('Operating point file number of values: 9\n')
       file.write('Inductor 1 position: ' + str(arduino.l1_pos) + '\n')
       file.write('Inductor 2 position: ' + str(arduino.l2_pos) + '\n')
       file.write('Duty Vref value: ' + str(duty_vref_final) + '\n')
       file.write('Channel 1 deskew: ' + str(ch1_deskew_cideal) + '\n')
       file.write('Channel 2 deskew: ' + str(ch2_deskew_cideal) + '\n')
       file.write('Ediss: ' + str(Ediss) + '\n')
       file.write('Freq in MHz: ' + str(freq) + '\n')
       file.write('trap_dvdt (fraction of quarter wavelength): ' + str(trap_dvdt) + '\n')
       file.write('Cref [pF]: ' + str(cref) + '\n')
   
   # save the trace data for future analysis
   np.savetxt(data_write_file, scope_data, delimiter=',')
   print(' Finished DUT operating point.\n')
   
   return Ediss

def run_operating_point_DUT_sine(freq, v_pp, probe_cdivs, cref,
                                 cideal_file, op_point_file, data_write_file,
                                 scope, HV_supply, LV_supply, arduino):
   # Runs an operating point on a DUT, using calibration data from similar Cideal point:
       # Uses Cideal point to learn deskew, inductor positions, and duty Vref
       # retunes inductors to get close to differential sinusoid
       # Measure and save data, calculate Ediss
   # Returns Ediss calculated Ediss value
   print('Running DUT operating point:\n  ' + str(freq) + ' Mhz' + \
         '\n  ' + str(v_pp) + ' Vpp')
   
   window_scope(freq, v_pp, False, probe_cdivs, scope) # set scope window
   general_LV_supply_activation(LV_supply)
   HV_supply.setVoltage(v_pp/2/np.pi)
   
   # read values from cideal file
   [l1_pos_cideal, l2_pos_cideal, duty_vref_cideal,
        ch1_deskew_cideal, ch2_deskew_cideal, a, b, c, d] = read_colon_file(cideal_file)
   l1_pos_cideal = float(l1_pos_cideal) # values are read in as strings
   l2_pos_cideal = float(l2_pos_cideal)
   duty_vref_cideal = float(duty_vref_cideal)
   ch1_deskew_cideal = float(ch1_deskew_cideal)
   ch2_deskew_cideal = float(ch2_deskew_cideal)
   
   # conservatively set duty cycle for ZVS, also set cideal L-vals and skews
   set_inductor_positions(LV_supply, arduino, l1_pos_cideal, l2_pos_cideal)
   general_arduino_activation(arduino, freq, duty_vref_cideal, False)
   arduino.setDutyCycleRefValue(duty_vref_cideal)
   set_channel_deskews(scope, 0, 0, 0, 0) # don't deskew on scope; 500ps minimum skew interval
   
   # fine-tune the inductors to get a good sine wave approximation
   print('Calibrating inductors to approximate differential sine wave...')
   inductor_tuning_sine_corner_find(freq, scope, HV_supply, LV_supply, arduino, duty_cycle)
       # Note each channel should see half the true desired dvdt (differential)
   print(' Inductor calibration done.\n')
   
   # read the waveform (which has now been somewhat optimized with Cideal)
   turn_system_on(HV_supply, LV_supply, arduino)
   print('Reading channels for Ediss calculation...')
   time.sleep(5) # for AC channels to settle out I guess
   scope_data = scope.readAllChannelsAveraged(5)
   print(' done')
   turn_system_off(HV_supply, LV_supply, arduino)
   
   # Calculate Ediss
   scope_data = scale_scope_data_w_cdivs(scope_data, probe_cdivs) # cdiv scaling
   scope_data_deskewed = scope_data.copy() # to leave scope_data alone during saving
   scope_data_deskewed = data_array_time_shift_one_signal(
       scope_data_deskewed, 0, 1, ch1_deskew_cideal)
   scope_data_deskewed = data_array_time_shift_one_signal(
       scope_data_deskewed, 0, 2, ch2_deskew_cideal)
   
   """
   No need to calculate Ediss since we don't use it anyways, so do this instead:
   """
   Ediss = 0
   """
   Ediss = calculate_Ediss_trap(scope_data_deskewed, freq*1e6, trap_dvdt, cref*1e-12)
   """
   # write the operating point to the operating point file
   with open(op_point_file, 'w') as file:
       file.write('Operating point file number of values: 9\n')
       file.write('Inductor 1 position: ' + str(arduino.l1_pos) + '\n')
       file.write('Inductor 2 position: ' + str(arduino.l2_pos) + '\n')
       file.write('Duty Vref value: ' + str(duty_vref_final) + '\n')
       file.write('Channel 1 deskew: ' + str(ch1_deskew_cideal) + '\n')
       file.write('Channel 2 deskew: ' + str(ch2_deskew_cideal) + '\n')
       file.write('Ediss: ' + str(Ediss) + '\n')
       file.write('Freq in MHz: ' + str(freq) + '\n')
       file.write('trap_dvdt (fraction of quarter wavelength): ' + '0' + '\n')
       file.write('Cref [pF]: ' + str(cref) + '\n')
   
   # save the trace data for future analysis
   np.savetxt(data_write_file, scope_data, delimiter=',')
   print(' Finished DUT operating point.\n')
   
   return Ediss
    
    
    
    
    
    
    



