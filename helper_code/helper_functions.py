# -*- coding: utf-8 -*-
"""
Created on Thu Jun 27 23:56:33 2024

@author: hornb
"""

import numpy as np
import time
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
from scipy import integrate
from scipy import signal

"""
General scope activation and associated functions:
-------------------------------------------------------------------------------
"""

def general_scope_activation(scope, probe_attenuations):
    # For general turn-on of the scope
    scope.run()
    # turn channels on
    scope.turnChannelOn(1)
    scope.turnChannelOn(2)
    scope.turnChannelOn(3)
    scope.turnChannelOn(4)
    set_channel_deskews(scope, 0, 0, 0, 0)
    # set up trigger on channel 3 (probing the low side gate of vout+)
    scope_trigger_setup(scope)
    # set probe attenuations and couplings
    scope.setAttenuationFactor(1, probe_attenuations[0])
    scope.setAttenuationFactor(2, probe_attenuations[1])
    scope.setAttenuationFactor(3, probe_attenuations[2])
    scope.setAttenuationFactor(4, probe_attenuations[3])
    set_probe_couplings(scope)
    # other misc scope setup stuff
    scope.clearAllMeasItems() # just to reduce clutter
    scope.setDataAcquisitionType('NORMal')
    # window probe 3 correctly since it's always on the gate
    window_probe3(scope)
    
def scope_trigger_setup(scope):
    scope.sendCMD('TRIGger:MODE EDGE') # set trigger to edge mode
    scope.sendCMD('TRIGger:COUPling DC') # set trigger to DC coupling
    scope.sendCMD('TRIGger:EDGE:SOURce CHANnel3') # trigger source to channel 3
    scope.sendCMD('TRIGger:EDGE:SLOPe POSitive') # trigger on rising edge
    scope.sendCMD('TRIGger:EDGE:LEVel 1') # sets trigger level to 1 Volt
    scope.setTimeZeroLocation(0)
    
def set_probe_couplings(scope):
    scope.setCoupling(1, 'AC')
    scope.setCoupling(2, 'AC')
    scope.setCoupling(3, 'DC') # channel 3 is gate sig: should be DC coupled
    scope.setCoupling(4, 'AC')
    
def set_channel_deskews(scope, ch1_deskew, ch2_deskew, ch3_deskew, ch4_deskew):
    scope.setChannelDeskew(1, ch1_deskew)
    scope.setChannelDeskew(2, ch2_deskew)
    scope.setChannelDeskew(3, ch3_deskew)
    scope.setChannelDeskew(4, ch4_deskew)
    
def window_probe3(scope):
    scope.setChannelScale(3, 8) # set Channel 3 to have 8 volts on the screen
    scope.setChannelZeroLocation(3, -3) # lower channel 3 to fit on screen

def window_scope(freq_MHz, v_pp, trap, probe_cdivs, scope):
    # Sets the scope window appropriately based on signal information
    # First, reset some settings the user may have changed in hardware setup
    scope_trigger_setup(scope)
    window_probe3(scope)
    # Second, set scalings to what they should be based on cdiv values
    freq = freq_MHz * 1e6
    scope.setTimeScale(1/freq * 3) # shoot for 3 wavelengths on scope
    probe1_vpp = v_pp / 2 * probe_cdivs[0] # anticipated Vpp we'll probe
    probe2_vpp = v_pp / 2 * probe_cdivs[1]
    probe4_vpp = v_pp / 2 * probe_cdivs[2]
    
    if trap:
        trap_buffer_scaling = 1.4 # room beyond nominal Vpp for overshooting
        scope.setChannelScale(1, round((probe1_vpp * trap_buffer_scaling), 5))
        scope.setChannelScale(2, round((probe2_vpp * trap_buffer_scaling), 5))
        scope.setChannelScale(4, round((probe4_vpp * trap_buffer_scaling), 5))
        
        scope.setChannelZeroLocation(1, 0) # for trap, symmetric waveform
        scope.setChannelZeroLocation(2, 0)
        scope.setChannelZeroLocation(4, 0)
    else: # Sinusoidal waveform: average value will be 2/pi times peak
        sine_buffer_scaling = 1.5 # room beyond nominal Vpp for overshooting
        scope.setChannelScale(1, round((probe1_vpp * sine_buffer_scaling), 5))
        scope.setChannelScale(2, round((probe2_vpp * sine_buffer_scaling), 5))
        scope.setChannelScale(4, round((probe4_vpp * sine_buffer_scaling), 5))
        # scaling/offset for channel 4 not strictly true but probly good enough
        scope.setChannelZeroLocation(1, (1/np.pi - 0.5) * probe1_vpp)
        scope.setChannelZeroLocation(2, (1/np.pi - 0.5) * probe2_vpp)
        scope.setChannelZeroLocation(4, (1/np.pi - 0.5) * probe4_vpp)
        
"""
Other general activation: LV_supply, arduino, and determining operating condition:
-------------------------------------------------------------------------------
"""
    
def general_LV_supply_activation(LV_supply):
    # For general setup of the LV supply
    LV_supply.disableMaster()
    LV_supply.setCH1()
    LV_supply.setVoltage(12)
    LV_supply.setCurrent(1.5) # for powering signal chain on power board
    LV_supply.setCH2()
    LV_supply.setVoltage(12)
    LV_supply.setCurrent(2.5) # for powering fans and inductor motors
    LV_supply.setCH3()
    LV_supply.setVoltage(5)
    LV_supply.setCurrent(0) # we're not using channel 3

def general_arduino_activation(arduino, freq, duty_ref, trap):
    # sets up arduino to run, but doesn't turn gate signals on
    arduino.disableGateSignals()
    arduino.setSineFreq(freq*2) # [MHz] twice because of frequency halving in DSP
    arduino.setSineAmp(5) # just max AD9913 amplitude
    arduino.setDutyCycleRefValue(duty_ref)
    if trap: arduino.enableTrapMode()
    else: arduino.enableSineMode()
        
def arduino_connectivity_check(arduino):
    # checks if the arduino is still connected
    return arduino.checkAlive()

def determine_operating_condition(freq, v_pp, trap, trap_dvdt):
    # if one of the variables is a list, then it must be a sweep variable
    # return 0 if no sweep variable, or (1|2|3) for sweeping (freq|vpp|dvdt)
    single_point = 0
    sweeping_freq = 1
    sweeping_v_pp = 2
    sweeping_dvdt = 3
    double_list_exception = "Multiple variables are lists: check freq, v_pp, trap_dvdt definitions."
    
    freq = type(freq)
    v_pp = type(v_pp)
    trap_dvdt = type(trap_dvdt)
    
    if trap:
        if freq == list: # must be sweeping frequency
            if (v_pp) == list or trap_dvdt == list:
                raise Exception(double_list_exception)
            else:
                return sweeping_freq
        if v_pp == list: # must be sweeping v_pp
            if trap_dvdt == list:
                raise Exception(double_list_exception)
            else:
                return sweeping_v_pp
        if trap_dvdt == list: # must be sweeping trap_dvdt
            return sweeping_dvdt
        else: return single_point # none of the input variables are a list
    else:
        if freq == list: # must be sweeping frequency
            if (v_pp) == list:
                raise Exception(double_list_exception)
            else:
                return sweeping_freq
        if v_pp == list: # must be sweeping frequency
            return sweeping_v_pp
        else: return single_point # none of the input variables are a list

"""
Full system turn-on and turn-off plus power check:
-------------------------------------------------------------------------------
"""

def turn_system_on(HV_supply, LV_supply, arduino, check_power=True):
    if arduino_connectivity_check(arduino):
        arduino.enableGateSignals()
        LV_supply.enableMaster()
        HV_supply.enableMaster()
        time.sleep(0.5) # give fans time to get going and voltage settled
        if check_power:
            check_HV_power(40, False, HV_supply, LV_supply, arduino)
    else:
        input('Arduino failed connectivity check before turn-on. Press enter to continue or ctrl+c to exit')
        turn_system_on(HV_supply, LV_supply, arduino) # if trying again, do the same thing
    
def turn_system_off(HV_supply, LV_supply, arduino):
    if arduino_connectivity_check(arduino):
        HV_supply.disableMaster()
        LV_supply.disableMaster()
        arduino.disableGateSignals()
    else:
        input('Arduino failed connectivity check before turn-off. Recommended to manually power down supplies. Press enter to continue or ctrl+c to exit')
        turn_system_off(HV_supply, LV_supply, arduino) # if trying again, do the same thing
    
def turn_system_on_minus_fans(HV_supply, LV_supply, arduino, check_power=True):
    # default power checking, but check_HV_power function can override to ignore
    if arduino_connectivity_check(arduino):
        arduino.enableGateSignals()
        LV_supply.setCH1()
        LV_supply.enableChannel()
        HV_supply.enableMaster()
        time.sleep(0.5) # give fans time to get going and voltage settled
        if check_power:
            check_HV_power(40, True, HV_supply, LV_supply, arduino)
    else:
        input('Arduino failed connectivity check before turn-on. Press enter to continue or ctrl+c to exit')
        turn_system_on_minus_fans(HV_supply, LV_supply, arduino) # if trying again, do the same thing
    
def turn_system_off_minus_fans(HV_supply, LV_supply, arduino):
    if arduino_connectivity_check(arduino):
        HV_supply.disableMaster()
        LV_supply.setCH1()
        LV_supply.disableChannel()
        arduino.disableGateSignals()
    else:
        input('Arduino failed connectivity check before turn-on. Press enter to continue or ctrl+c to exit')
        turn_system_off_minus_fans(HV_supply, LV_supply, arduino) # if trying again, do the same thing
    
def check_HV_power(power_threshold, no_fans, HV_supply, LV_supply, arduino):
    # checks if HV supply is exceeding power_threshold, and gives user option to quit if so
    time.sleep(0.5)
    volts = HV_supply.readVoltage()
    amps = HV_supply.readCurrent()
    power = volts*amps
    if power > power_threshold:
        if no_fans:
            turn_system_off_minus_fans(HV_supply, LV_supply, arduino)
        else:
            turn_system_off(HV_supply, LV_supply, arduino)
        input('HV supply was exceeding power threshold: ' + str(power) + \
              ' > ' + str(power_threshold) + '.\n' + \
              'Press enter to continue anyway, or ctrl+c to stop the run.\n')
        # if code still running, user has opted to continue, so don't check power this time
        if no_fans:
            turn_system_on_minus_fans(HV_supply, LV_supply, arduino, check_power=False)
        else:
            turn_system_on(HV_supply, LV_supply, arduino, check_power=False)
        
"""
Inductor-related functions: calibration, setting inductors, guessing values based on dv/dt:
-------------------------------------------------------------------------------
"""
    
def make_user_calibrate_inductors(LV_supply, arduino):
    input('You will now repeatedly enter the steps for inductor 1 to move until it\'s calibrated at the sharpie mark. Press enter to continue.\n')
    LV_supply.setCH2()
    LV_supply.enableChannel()
    steps = int(input('Enter number of steps to move inductor 1. Enter 0 when complete: '))
    while steps != 0:
        arduino.calInd(1, steps)
        steps = int(input('Enter number of steps to move inductor 1. Enter 0 when complete.'))
    print('\nThank you for calibrating inductor 1.\n')
    LV_supply.disableChannel()
    
    input('You will now repeatedly enter the steps for inductor 2 to move until it\'s calibrated at the sharpie mark. Press enter to continue.\n')
    LV_supply.enableChannel()
    steps = int(input('Enter number of steps to move inductor 2. Enter 0 when complete: '))
    while steps != 0:
        arduino.calInd(2, steps)
        steps = int(input('Enter number of steps to move inductor 2. Enter 0 when complete.'))
    print('\nThank you for calibrating inductor 2.\n')
    LV_supply.disableChannel()
    
def set_inductor_positions(LV_supply, arduino, l1_pos, l2_pos, supply_on=False):
    # sets inductor positions based on numbers of steps with current calibration
    # If position requested is below 0 or above 4800 (safe operating range):
        # then it rounds up/down to 0/4800 and prints message so you know
    # if supply_on is True, then doesn't do anything to LV_supply
        
    # range stuff
    min_pos = 0 # minimum inductor position
    max_pos = 4800 # maximum inductor position
    range_error = False # determines whether a range error will be printed
    range_error_message = ''
    if (l1_pos < min_pos):
        l1_pos = min_pos
        range_error_message += 'Inductor 1 tried to go below minimum position.\n'
        range_error = True
    elif (l1_pos > max_pos):
        l1_pos = max_pos
        range_error_message += 'Inductor 1 tried to go above maximum position.\n'
        range_error = True
    if (l2_pos < min_pos):
        l2_pos = min_pos
        range_error_message += 'Inductor 2 tried to go below minimum position.\n'
        range_error = True
    elif (l2_pos > max_pos):
        l2_pos = max_pos
        range_error_message += 'Inductor 2 tried to go above maximum position.\n'
        range_error = True
    if range_error:
        print(range_error_message)
    
    # actually setting the channels
    if not(supply_on):
        LV_supply.setCH2()
        LV_supply.enableChannel()
    time.sleep(0.5)
    arduino.setIndPos(1, l1_pos)
    arduino.setIndPos(2, l2_pos)
    arduino.waitForInductorsToMove()
    if not(supply_on):
        LV_supply.disableChannel()
    return range_error # so user can decide whether to break the loop above
    
    
def set_inductor_values(LV_supply, arduino, l1_val, l2_val, supply_on=False):
    # sets inductor values using LUT on the arduino - fairly rough calibration
    # inductance values are [uH]
    # arduino should automatically round out-of-range values to be in-range
    # if supply_on is True, then doesn't modify the LV_supply
    if not(supply_on):
        LV_supply.setCH2()
        LV_supply.enableChannel()
    time.sleep(0.5)
    arduino.setIndVal(1, l1_val)
    arduino.setIndVal(2, l2_val)
    arduino.waitForInductorsToMove()
    if not(supply_on):
        LV_supply.disableChannel()
    
def L_guess_trap(freq_MHz, trap_dvdt, cap):
    # Guesses the inductance value to use for a trap, also returns duty cycle
    # trap_dvdt is the fraction of a quarter-wavelength linear ramp lasts
    freq = freq_MHz * 1e6
    Thalf = 1/2/freq # half period used in trapezoidal math
    D = (2-trap_dvdt)/2 # divide by 2 b/c referenced to quarter wavelength
    Lguess = (D * (1-D) * Thalf**2) / (4 * cap * 1e-12) # PCIM paper-derived formula
    return [Lguess * 1e6, D] # return inductance in [uH]

def L_guess_sine(freq_MHz, cap):
    # Guesses the inductance value to use for a sine wave given frequency
    freq = freq_MHz * 1e6
    omega = 2 * np.pi * freq
    Lguess = 1 / (cap * omega**2) # just set resonant frequency to match switch frequency
    return Lguess

def get_true_dvdt(trap_dvdt, freq, v_pp):
    # Calculates true ST voltage slope in [V/s]
    dt = trap_dvdt * 0.25 / freq # trap_dvdt based on quarter wavelength
    return v_pp / dt

"""
Tuning inductors for trapezoidal waveform based on dv/dt:
-------------------------------------------------------------------------------
"""

def inductor_tuning_trap_scope_based(trap_dvdt, probe_cdivs, scope, HV_supply, LV_supply, arduino):
    # Tunes inductors to achieve desired dv/dt on trapezoidal waveform
    # Note total waveform dvdt should be divided by 2 before using this function
    # Uses scope PSLewrate and NSLewrate measurements to calculate current dvdt
    # Note the indexing is a bit weird because L1 corresponds to Ch2 and vice versa
    
    scope.clearAllMeasItems()
    LV_supply.setCH2()
    LV_supply.enableChannel()
        # measure_l1_l2_trap_dvdt_errors won't turn on fans anymore so do it here
    
    # Measure initial slope values
    [ch1_dvdt, ch2_dvdt, l1_error, l2_error] = measure_l1_l2_trap_dvdt_errors(
        trap_dvdt, probe_cdivs, scope, HV_supply, LV_supply, arduino)
    
    # Approach desired value from above to avoid poor non-ZVS measurements
    skip_tuning = False
    while (l1_error > 0) or (l2_error > 0): # if slope is too shallow and possibly lost ZVS
        l1_new = arduino.l1_pos
        l2_new = arduino.l2_pos
        if l1_error > 0:
            l1_new -= 100 # make it steeper, smaller transition time
        if l2_error > 0:
            l2_new -= 100 # make it steeper, smaller transition time
        range_error = set_inductor_positions(LV_supply, arduino, l1_new, l2_new, supply_on=True)
        [ch1_dvdt, ch2_dvdt, l1_error, l2_error] = measure_l1_l2_trap_dvdt_errors(
            trap_dvdt, probe_cdivs, scope, HV_supply, LV_supply, arduino)
        if range_error: # means we're hitting zero on one or both inductors
            skip_tuning = input('\nInductor range limit alert: Enter 0 to skip further tuning or anything else to continue: ')
            if skip_tuning == '0':
                skip_tuning = True # just leave the inductors where they are right now
                break
            else:
                skip_tuning = False
    
    # Set up tuning parameters
    error_tol = 0.05 # will stop when within error_tol*trap_dvdt of trap_dvdt
    error_goal = error_tol * trap_dvdt # want error less than this
    give_up_iterations = 6 # if not met error_tol, gives up after this many tries
    l1_off = abs(l1_error) > error_goal # says whether we need to tune L1
    l2_off = abs(l2_error) > error_goal # says whether we need to tune L2
    iteration_count = 0
    if not(skip_tuning): # wanted to leave the inductors alone
        while l1_off or l2_off:
            # move the inductors some steps to measure dvdt sensitivity to position
            l1_test_steps = max(arduino.l1_pos / 10, 100)
            l2_test_steps = max(arduino.l2_pos / 10, 100)
            range_error = set_inductor_positions(LV_supply, arduino,
                                   arduino.l1_pos + l1_test_steps, arduino.l2_pos + l2_test_steps,
                                   supply_on=True)
            if range_error: # means we're hitting max on one or both inductors
                skip_tuning = input('\nInductor range limit alert: Enter 0 to skip further tuning or anything else to continue: ')
                if skip_tuning == '0':
                    break
            [ch1_dvdt_100, ch2_dvdt_100] = measure_l1_l2_trap_dvdt_errors(
                trap_dvdt, probe_cdivs, scope, HV_supply, LV_supply, arduino)[0:2]
            l1_sensitivity = (ch2_dvdt_100 - ch2_dvdt) / l1_test_steps # [dvdt per step]
            l2_sensitivity = (ch1_dvdt_100 - ch1_dvdt) / l2_test_steps # [dvdt per step]
            # move the inductors to new positions based on measured sensitivity
            range_error = set_inductor_positions(LV_supply, arduino,
                                   arduino.l1_pos - l1_test_steps + l1_error / l1_sensitivity,
                                   arduino.l2_pos - l2_test_steps + l2_error / l2_sensitivity,
                                   supply_on=True)
            if range_error: # means we're hitting max on one or both inductors
                skip_tuning = input('\nInductor range limit alert: Enter 0 to skip further tuning or anything else to continue: ')
                if skip_tuning == '0':
                    break
            # measure new errors before loop ends
            [ch1_dvdt, ch2_dvdt, l1_error, l2_error] = measure_l1_l2_trap_dvdt_errors(
                trap_dvdt, probe_cdivs, scope, HV_supply, LV_supply, arduino)
            if iteration_count >= give_up_iterations:
                break
            l1_off = abs(l1_error) > error_goal # says whether we need to tune L1
            l2_off = abs(l2_error) > error_goal # says whether we need to tune L2
            iteration_count += 1
            
    # measure_l1_l2_trap_dvdt_errors won't turn off fans anymore, so do it here
    turn_system_off(HV_supply, LV_supply, arduino)
    
def measure_average_dvdt(scope, channel_index):
    # Returns the average of PSLewrate and NSLewrate for channel_index
    pslew = abs(scope.queryStatItem("AVERages", "PSLewrate", channel_index))
    nslew = abs(scope.queryStatItem("AVERages", "NSLewrate", channel_index))
    return (pslew + nslew) / 2

def measure_ch1_ch2_dvdt_w_pause_and_cdiv(scope, probe_cdivs):
    # Returns [ch1_dvdt, ch2_dvdt] with a pause to allow averaging to work well
    scope.resetMeasStats() # restart the averaging
    measure_average_dvdt(scope, 1) # turn on measurement if not already on
    measure_average_dvdt(scope, 2)
    time.sleep(3) # wait to allow some averaging to occur
    ch1_dvdt = measure_average_dvdt(scope, 1) / probe_cdivs[0] # take final measurements
    ch2_dvdt = measure_average_dvdt(scope, 2) / probe_cdivs[1]
    return [ch1_dvdt, ch2_dvdt]

def measure_l1_l2_trap_dvdt_errors(trap_dvdt, probe_cdivs, scope, HV_supply, LV_supply, arduino):
    # measures L1 and L2 errors
    # returns [ch1_dvdt, ch2_dvdt, l1_error, l2_error]
    # assumes the 12V fan/inductor supply is already on to minimize noisy distractions to lab-mates
    turn_system_on_minus_fans(HV_supply, LV_supply, arduino)
    # turn_system_on(HV_supply, LV_supply, arduino)
    [ch1_dvdt, ch2_dvdt] = measure_ch1_ch2_dvdt_w_pause_and_cdiv(scope, probe_cdivs)
    turn_system_off_minus_fans(HV_supply, LV_supply, arduino)
    # turn_system_off(HV_supply, LV_supply, arduino)
    l1_error = trap_dvdt - ch2_dvdt # Channel 2 (vout- node) corresponds to L1
    l2_error = trap_dvdt - ch1_dvdt # vice versa
    return [ch1_dvdt, ch2_dvdt, l1_error, l2_error]


"""
Tuning for sinusoidal waveform based on corner finding to match period of switch frequency
-------------------------------------------------------------------------------
"""

def inductor_tuning_sine_corner_find(freq_MHz, scope, HV_supply, LV_supply, arduino, duty_cycle):
    # Tunes the sine wave by finding corners in waveforms
    # Tries to get the period of the sinusoidal bumps to match the swtich frequency
    freq = freq_MHz * 1e6
    T = 1/freq # period of the switching frequency
    
    scope.clearAllMeasItems()
    
    # Measure half period of both sinusoidal bumps
    fall_time = T*duty_cycle # since the trigger is gate rising edge
        # note that fall_time is when vout+ resonant bump starts; Q turning off
    turn_system_on(HV_supply, LV_supply, arduino)
    [vp_period, vm_period] = measure_vp_vm_periods(scope, fall_time, T)
    turn_system_off(HV_supply, LV_supply, arduino)
    l1_error = vm_period - T
    l2_error = vp_period - T
    
    # define tuning parameters
    error_tol = 0.1
    error_goal = error_tol * T
    give_up_iterations = 6
    l1_off = abs(l1_error) > error_goal
    l2_off = abs(l2_error) > error_goal
    iteration_count = 0
    while l1_off or l2_off:
        l1_test_steps = max(arduino.l1_pos / 10, 100)
        l2_test_steps = max(arduino.l2_pos / 10, 100)
        range_error = set_inductor_positions(LV_supply, arduino,
                               arduino.l1_pos + l1_test_steps, arduino.l2_pos + l2_test_steps,
                               supply_on=False)
        if range_error: # means we're hitting max on one or both inductors
            skip_tuning = input('\nInductor range limit alert: Enter 0 to skip further tuning or anything else to continue: ')
            if skip_tuning == '0':
                break
        turn_system_on(HV_supply, LV_supply, arduino)
        [vp_period_100, vm_period_100] = measure_vp_vm_periods(scope, fall_time, T)
        turn_system_off(HV_supply, LV_supply, arduino)
        l1_sensitivity = (vm_period_100 - vm_period) / l1_test_steps # [dvdt per step]
        l2_sensitivity = (vp_period_100 - vp_period) / l2_test_steps # [dvdt per step]
        # move the inductors to new positions based on measured sensitivity
        range_error = set_inductor_positions(LV_supply, arduino,
                               arduino.l1_pos - l1_test_steps + l1_error / l1_sensitivity,
                               arduino.l2_pos - l2_test_steps + l2_error / l2_sensitivity,
                               supply_on=False)
        if range_error: # means we're hitting max on one or both inductors
            skip_tuning = input('\nInductor range limit alert: Enter 0 to skip further tuning or anything else to continue: ')
            if skip_tuning == '0':
                break
        # measure new errors before loop ends
        turn_system_on(HV_supply, LV_supply, arduino)
        [vp_period, vm_period] = measure_vp_vm_periods(scope, fall_time, T)
        turn_system_off(HV_supply, LV_supply, arduino)
        l1_error = vm_period - T
        l2_error = vp_period - T
        if iteration_count >= give_up_iterations:
            break
        l1_off = abs(l1_error) > error_goal # says whether we need to tune L1
        l2_off = abs(l2_error) > error_goal # says whether we need to tune L2
        iteration_count += 1
            
    # measure_l1_l2_trap_dvdt_errors won't turn off fans anymore, so do it here
    turn_system_off(HV_supply, LV_supply, arduino)
    
def measure_vp_vm_periods(scope, fall_time, T):
    scope_data = scope.readAllChannels()
    t = scope_data[:,0]
    vp = scope_data[:,1]
    vm = scope_data[:,2]
    vp_up = fall_time # vout+ up time
    vp_down = vector_find_corner_index(vp, t, fall_time + 0.75*T/2, T/30, 0, True, 0.5)
    vp_down = t[vp_down]
    vm_up = fall_time + T/2 # vout- down time
    vm_down = vector_find_corner_index(vm, t, fall_time + T/2 + 0.75*T/2, T/30, 0, True, 0.5)
    vm_down = t[vm_down]
    vp_period = 2 * (vp_down - vp_up)
    vm_period = 2 * (vm_down - vm_up)
    return[vp_period, vm_period]

"""
Duty cycle tuning: setting duty cycle, tuning for trap/sine, ensuring gate signal exists:
-------------------------------------------------------------------------------
"""

def gate_signal_exists(scope):
    # Returns boolean for whether the gate signal on channel 3 is working
    # When gate signal is flat (high or low), NDUTy and PDUTy return 9.9e37
    # If gate signal exists, the duty cycle should be less than 1
    return (abs(scope.queryMeasItem("PDUTy", 3)) < 1)

def set_half_duty_cycle(scope, LV_supply, arduino, duty_goal, vref_current):
    # Sets the duty cycle by measuring channel 3 waveform with gates running
    # Half duty cycle means realtive to half a wavelength
    print('Setting rough duty cycle...')
    error_tol = 0.05 # will stop when within error_tol*duty_goal of duty_goal
    volts_per_error = 1.5 # adjusts # volts per duty cycle error
    give_up_iterations = 10 # if not met error_tol, gives up after this many tries
    
    LV_supply.setCH1()
    LV_supply.enableChannel()
    arduino.enableGateSignals()
    duty_current = float(scope.queryMeasItem("PDUTy", 3))*2 # referenced to half period
    error = duty_goal - duty_current
    error_goal = error_tol * duty_goal # want error less than this
    iteration_count = 0
    
    while abs(error) > error_goal:
        vref_old = vref_current # keep track in case we lose the gate signal to go back
        change = volts_per_error * error # number of volts to change vref by
        vref_current += change # update current duty ref value
        arduino.setDutyCycleRefValue(vref_current)
        time.sleep(1) # wait for RC delay of duty_vref adjustment to catch up
        if not(gate_signal_exists(scope)): # lost gate signal: go back to prior step and give up
            arduino.setDutyCycleRefValue(vref_old)
            print('Could not achieve desired duty cycle without losing gate signal.\n')
            break
        duty_current = float(scope.queryMeasItem("PDUTy", 3))*2 # referenced to half period
        error = duty_goal - duty_current
        iteration_count += 1
        if iteration_count >= give_up_iterations:
            break
    print(' done')
    return vref_current # so caller function knows what duty_vref ended up at

def duty_cycle_tuning_trap(arduino, scope, HV_supply, init_duty_vref):
    # Tunes duty cycle for trap waveform to minimize Vdc supply power
    # start_duty_vref should be about 75% of theoretical D at desired dvdt:
        # Therefore can increment duty_vref up to increase D til ZVS lost
        
    print("Tuning duty cycle...\n")
    
    initial_power_exceed_threshold = 1.2 # stops increasing D when this is met
    vref_inc = 0.05 # how much to increment duty_vref by in each iteration
    vref = init_duty_vref
    arduino.setDutyCycleRefValue(vref) # just set in case something has changed
    time.sleep(1) # allow time for RC duty_vref adjustment
    supply_currents = [HV_supply.readCurrent()] # keep track of all supply currents
    threshold = initial_power_exceed_threshold * supply_currents[0] # [A]
    
    # increase D while measuring current until threshold exceeded or gate signal lost
    while supply_currents[-1] < threshold: # while we seemingly haven't lost ZVS
        vref += vref_inc
        arduino.setDutyCycleRefValue(vref)
        time.sleep(1) # allow time for RC duty_vref adjustment
        if not(gate_signal_exists(scope)): # lost gate signal, stop increasing D
            break
        supply_currents.append(HV_supply.readCurrent()) # add newest current value
    
    # set duty cycle to whatever value gave minimum current (minimum power)
    min_current_index = np.argmin(supply_currents)
    final_duty_vref = init_duty_vref + vref_inc*min_current_index
    arduino.setDutyCycleRefValue(final_duty_vref)
    time.sleep(2) # allow transients in measuring state to settle down
    print("Duty cycle tuning complete\n")
    return final_duty_vref

def duty_cycle_tuning_sine(arduino, scope, init_duty_vref):
    # Tunes the duty cycle for sine waves, just trying to make it as big
        # as possible to minimize reverse diode conduction
    # Just step up vref til you lose the gate signal and go back 3 steps before
        # 3 steps just to be safe; sometimes the stability is iffy close to max
        # with 0.05V step, this is a 0.15V back off from when signal was lost
    
    print("Tuning duty cycle...\n")
    
    vref_tuning_step = 0.05 # vref incremental step [V]
    back_off_steps = 3 # number of steps to back off from when gate signal lost
    vref = init_duty_vref
    arduino.setDutyCycleRefValue(vref)
    time.sleep(1)
    while gate_signal_exists(scope):
        vref += vref_tuning_step
        arduino.setDutyCycleRefValue(vref)
        time.sleep(1)
    final_vref = vref - back_off_steps*vref_tuning_step
    arduino.setDutyCycleRefValue(final_vref)
    time.sleep(2)
    duty_cycle = scope.queryMeasItem("PDUTy", 3) # measures duty cycle
    print("Duty cycle tuning complete\n")
    return [final_vref, duty_cycle]

"""
Signal processing/array manipulation stuff from malachi_plotting_functions:
-------------------------------------------------------------------------------
"""

def data_array_set_t0_at_value_crossing(data_array, t_col, d_col, cross_value, rising, jostle_buffer):
    # data_array is np.ndarray where t_col is time and d_col is the data vector
    # that you want to find zero crossing in. rising is boolean: 0 means falling
    
    # jostle_buffer determines points to ignore after first positive or negative
    # value when trying to find the zero crossing
        # eg for rising, how many points to ignore after first falling edge
        # before a positive value can be taken to indicate a rising edge?
    
    # returns data_array but with time values shifted so that the first rising
    # or falling zero crossing in d_col is at t=0
    
    t_vals = data_array[:,t_col]
    d_vals = data_array[:,d_col]
    
    if rising:
        ignore_before_index = np.argmax(d_vals<cross_value) + jostle_buffer
        zero_index = np.argmax(d_vals[ignore_before_index:-1]>cross_value) + ignore_before_index
    else:
        ignore_before_index = np.argmax(d_vals>cross_value) + jostle_buffer
        zero_index = np.argmax(d_vals[ignore_before_index:-1]<cross_value) + ignore_before_index
    
    t_near_cross = t_vals[zero_index - 1 : zero_index + 1] # 2 t-vals
    d_near_cross = d_vals[zero_index - 1 : zero_index + 1] # 2 vals: one pos and one neg
    t_shift = np.interp(cross_value, d_near_cross, t_near_cross) # interpolate time of crossing
    
    #t_shift = t_vals[zero_index]
    new_t_vals = t_vals - t_shift
    data_array[:,t_col] = new_t_vals
    return data_array

def data_array_time_shift_one_signal(data_array, t_col, d_col, shift):
    # data_array: np.ndarray of some time-based data
    # t_col: int for the index of the time column
    # d_col: int for the index of the data you want to time-shift
    # shift: amount of time you want to add to d_col: positive shifts right
    
    # note: to preserve # of points we just copy the first or last value in
        # the data as it shifts away from the edge, so don't trust edge data
    
    t = data_array[:,t_col]
    t_new = t + shift # new timebase for signal
    d = data_array[:,d_col]
    d_new = np.zeros(len(d)) # new data array that corresponds to OLD timebase
    for index in range(len(t)):
        t_val = t[index]
        if t_val < t_new[0]: # signal shifted right: unknown at early times
            d_new[index] = d[0] # just copy first value as necessary
        elif t_val > t_new[-1]: # signal shifted left: unknown later
            d_new[index] = d[-1] # just cpoy last value as necessary
        else:
            d_new[index] = np.interp(t_val, t_new, d) # interpolate value linearly
    data_array[:,d_col] = d_new
    return data_array

def gaussian_average_specifying_stdev_time(sig, t_res, t_stdev):
    # takes in sig as np.array and does gaussian averaging with t_stdev deviation
    # t_res is the time step associated with the data
    stdev_points = t_stdev / t_res
    return gaussian_filter1d(sig, stdev_points)

def vector_zero_ac_sig_to_trange_avg(t, sig, tstart, tend):
    # zeros signal of the average value between tstart and tend
    # for functionality, if tstart and tend aren't actual data points, the point
    # before tstart and after tend will be included (to avoid having no data)
    # Returns the sig vector with the zeroing completed
    
    start_index = np.argmax(t > tstart) - 1 # index of first value in averaging range
    end_index = np.argmax(t > tend) - 1 # index of last value in averaging range
    average = np.average(sig[start_index:end_index + 1])
    return sig - average

def vector_butterworth_lpf(sig, t_res, order, cutoff):
    # performs a butterworth low pass filter of twice the order specified:
        # apparently the filtfilt function filters twice, doubling order
    # inputs:
        # sig: np.array of the signal as a function of time
        # t_res [s]: the time spacing between samples. Spacings must be uniform
        # order [int]: the order of the LPF desired. Note it's doubled by filtfilt
        # cutoff [Hz]: the -3dB frequency of the butterworth filter
    
    fs = 1 / t_res # sampling frequency
    nyquist = fs / 2 # nyquist frequency: needed to determine butter parameters
    cutoff_norm = cutoff / nyquist # normalized cutoff frequency
    b, a = signal.butter(order, cutoff_norm, btype = 'low')
    filtered_signal = np.array(signal.filtfilt(b, a, sig))
    return filtered_signal

def vector_find_corner_index(sig, t, t_in_slope, t_step, t_buff, search_direction, slope_change_threshold):
    # sig: vector signal
    # t: time vector
    # t_in_slope: a point that's in a roughly linear slopey part of sig
    # t_step: time step to jump by when looking for sufficiently large change in slope
    # t_buff: additional time to move past the corner trigger point by if you want some margin
    # search direction: True - towards higher indices, False - towards lower indices
    # slope_change_threshold: fractional change in slope necessary to have "found" corner
        # eg 0.3 for if a 30% change in slope signals a corner
        # probably want < 0.5 to avoid points straddling corner not triggering
    # note: assumes sig is uniformly spaced in time
    # returns the index at which the slope has changed enough to trigger
    
    sct = slope_change_threshold # smaller to write
    t_curr = t_in_slope # current time
    ind_curr = np.argmax(t>=t_curr) # index for current time
    if search_direction:
        t_next = t_curr + t_step # next time
    else:
        t_next = t_curr - t_step # next time
    ind_next = np.argmax(t>=t_next) # index for next time
    
    if search_direction: # looking for corner in forward direction
        slope_ref = sig[ind_next] - sig[ind_curr]
        while (t_next <= t[-1]): # as long as we're not reaching past end of vector
            t_curr = t_next
            ind_curr = np.argmax(t>=t_curr)
            t_next = t_curr + t_step
            ind_next = np.argmax(t>=t_next)
            slope_new = sig[ind_next] - sig[ind_curr]
            if (np.sign(slope_ref) != np.sign(slope_new)) or (abs(slope_new/slope_ref) < 1-sct):
                # if signs changed or slope changed
                return_t = t_next + t_buff
                return np.argmax(t>=return_t)
            else:
                slope_ref = slope_new
    else: # search_direction is False (to the left)
        slope_ref = sig[ind_next] - sig[ind_curr]
        while (t_next >= t[0]): # as long as we're not reaching past end of vector
            t_curr = t_next
            ind_curr = np.argmax(t>=t_curr)
            t_next = t_curr - t_step
            ind_next = np.argmax(t>=t_next)
            slope_new = sig[ind_next] - sig[ind_curr]
            if (np.sign(slope_ref) != np.sign(slope_new)) or (abs(slope_new/slope_ref) < 1-sct):
                # if signs changed or slope changed
                return_t = t_next - t_buff
                return np.argmax(t>=return_t)
            else:
                slope_ref = slope_new


"""
Calculating trapezoidal/sinusoidal skew values using mean square error:
-------------------------------------------------------------------------------
"""

def MSE(vector1, vector2):
    # calculates mean square error between two vectors of the same length
    return np.square(np.subtract(vector1, vector2)).mean()

def find_deskew_for_min_MSE(scope_data_og, freq, trap_dvdt):
    # Takes in:
        # scope data as a np.ndarray, returns [ch1_deskew, ch2_deskew]
        # freq in Hz
        # trap_dvdt as fraction of a quarter wavelength slope should last
    # Minimizes mean square error (MSE) to determine deskews relative to Vref
    # data is in the format [t, ch1/vout+, ch2/vout-, ch3/vgate, ch4/vref]
    # requires at least 2.5 or so wavelengths; it's set to 3 currently
    
    scope_data = scope_data_og.copy()
    
    # normalize the waveforms for comparison
    scope_data[:,1] = scope_data[:,1] / np.average([abs(x) for x in scope_data[:,1]])
    scope_data[:,2] = scope_data[:,2] / np.average([abs(x) for x in scope_data[:,2]])
    scope_data[:,4] = scope_data[:,4] / np.average([abs(x) for x in scope_data[:,4]])
    
    # parameters:
    skew_step = 0.1e-9 # skew step in seconds
    skew_range = 5e-9 # +/- range to skew vout+ and vout- by to find best alignment
    # parameters to not edit:
    t_res = scope_data[1, 0] - scope_data[0, 0]
    period_points = (1 / freq) / t_res # don't round for better math
    half_period_points = round(period_points / 2)
    half_slope_points = round((period_points / 4 * trap_dvdt) / 2) # points in half trap slope
    
    # use smoothed ch1 to find zero-crossing
    scope_smooth = scope_data.copy() # to leave scope data alone
    scope_smooth[:,1] = gaussian_average_specifying_stdev_time(
        sig = scope_smooth[:,1], t_res = t_res,
        t_stdev = 1e-9) # smooth channel 1 for t0 search: using 1 ns stdev
    scope_smooth = data_array_set_t0_at_value_crossing(
        scope_smooth, 0, 1, 0, True, 6) # find middle of first rising slope
    scope_data[:,0] = scope_smooth[:,0] # set t0 in the actual data
    t = scope_data[:,0]
    t0_index = np.argmax(t >= 0) # index of t=0 point in dataset
    
    # mean square error window includes only rising/falling slopes
    istart1 = t0_index - half_slope_points - 1
    istop1 = t0_index + half_slope_points + 1
    istart2 = istart1 + half_period_points
    istop2 = istop1 + half_period_points
    
    # sweep through the skews and keep track of MSE
    ch1_skew_mse = []
    ch2_skew_mse = []
    skew_points = np.arange(-skew_range, skew_range + skew_step/2, skew_step)
        # skew_step/2 to ensure that +skew_range is included
    for skew_val in skew_points:
        # shift channels 1 and 2
        current_data = scope_data.copy() # reset to the original data without any skew
        current_data = data_array_time_shift_one_signal(current_data, 0, 1, skew_val - 0.5/freq) # half period to align w/ vref
        current_data = data_array_time_shift_one_signal(current_data, 0, 2, skew_val)
        ch1_data = current_data[:,1]
        ch2_data = current_data[:,2]
        ch4_data = current_data[:,4]
        
        """
        Optional plotting:
        
        
        fig, ax = plt.subplots()
        ax.plot(current_data[:,0]*1e9, ch1_data, label='vout+')
        ax.plot(current_data[:,0]*1e9, ch2_data, label='vout-')
        ax.plot(current_data[:,0]*1e9, ch4_data, label='vref')
        ax.plot([current_data[istart1, 0], current_data[istart1, 0]], [-1, 1], 'r')
        ax.plot([current_data[istop1, 0], current_data[istop1, 0]], [-1, 1], 'r')
        ax.plot([current_data[istart2, 0], current_data[istart2, 0]], [-1, 1], 'r')
        ax.plot([current_data[istop2, 0], current_data[istop2, 0]], [-1, 1], 'r')
        ax.legend()
        """
        
        # isolate rising and falling edges
        ch1_data = np.concatenate([
            ch1_data[istart1:istop1+1],
            ch1_data[istart2:istop2+1]]) # take the rising and falling edges
        ch2_data = np.concatenate([
            ch2_data[istart1:istop1+1],
            ch2_data[istart2:istop2+1]]) # take the rising and falling edges
        ch4_data = np.concatenate([
            ch4_data[istart1:istop1+1],
            ch4_data[istart2:istop2+1]]) # take the rising and falling edges
        # calculate and store mean square error
        ch1_skew_mse.append(MSE(ch1_data, ch4_data))
        ch2_skew_mse.append(MSE(ch2_data, ch4_data))
    
    # find the skew corresponding to the minimum MSE
    ch1_min_index = np.argmin(ch1_skew_mse)
    ch2_min_index = np.argmin(ch2_skew_mse)
    return [skew_points[ch1_min_index], skew_points[ch2_min_index]]
    # ignore below; now positive because all deskewing happening in code
    # negative becuase the scope skew polarity is reversed
    
def find_deskew_MSE_Ediss_hybrid(scope_data_og, freq, trap_dvdt, cref):
    # takes in:
        # scope_data - scope traces as np.ndarray, returns [ch1_deskew, ch2_deskew]
        # freq in Hz, trap_dvdt as fraction of 1/4 wavelength, cref in F
    # Minimizes MSE for vout- channel 2 since its ringing should line up with vref well
    # Then sweeps through skews for vout+ to minimize Ediss
    # possible improvement over the purely MSE-based deskewing process
    
    scope_data = scope_data_og.copy()
    
    # normalize the waveforms for comparison, keep track of normalization for later Ediss calculation
    ch1_norm = np.average([abs(x) for x in scope_data[:,1]])
    ch2_norm = np.average([abs(x) for x in scope_data[:,2]])
    ch4_norm = np.average([abs(x) for x in scope_data[:,4]])
    scope_data[:,1] = scope_data[:,1] / ch1_norm
    scope_data[:,2] = scope_data[:,2] / ch2_norm
    scope_data[:,4] = scope_data[:,4] / ch4_norm
    
    # parameters:
    skew_step = 0.1e-9 # skew step in seconds
    skew_range = 5e-9 # +/- range to skew vout+ and vout- by to find best alignment
    # parameters to not edit:
    t_res = scope_data[1, 0] - scope_data[0, 0]
    period_points = (1 / freq) / t_res # don't round for better math
    half_period_points = round(period_points / 2)
    half_slope_points = round((period_points / 4 * trap_dvdt) / 2) # points in half trap slope
    
    # use smoothed ch1 to find zero crossing
    scope_smooth = scope_data.copy() # to leave scope data alone
    scope_smooth[:,1] = gaussian_average_specifying_stdev_time(
        sig = scope_smooth[:,1], t_res = t_res,
        t_stdev = 1e-9) # smooth channel 1 for t0 search: using 1 ns stdev
    scope_smooth = data_array_set_t0_at_value_crossing(
        scope_smooth, 0, 1, 0, True, 6) # find middle of first rising slope
    scope_data[:,0] = scope_smooth[:,0] # set t0 in the actual data
    t = scope_data[:,0]
    t0_index = np.argmax(t >= 0) # index of t=0 point in dataset
    
    # mean square error window includes entire period:
        # note this is different than the current implementation of MSE deskewing
    istart1 = t0_index - half_slope_points - 1
    istop1 = t0_index + round(period_points)
    
    # choose channel 2 skew based on MSE minimization over entire period
    ch2_skew_mse = []
    skew_points = np.arange(-skew_range, skew_range + skew_step/2, skew_step)
        # skew_step/2 to ensure that +skew_range is included
    for skew_val in skew_points:
        # shift channel 2
        current_data = scope_data.copy() # reset to the original data without any skew
        current_data = data_array_time_shift_one_signal(current_data, 0, 2, skew_val)
        ch2_data = current_data[:,2]
        ch4_data = current_data[:,4]
        
        ch2_data = ch2_data[istart1:istop1]
        ch4_data = ch4_data[istart1:istop1]
        # calculate and store mean square error
        ch2_skew_mse.append(MSE(ch2_data, ch4_data))
    # find the skew that minimizes MSE for channel 2 (vout-), implement that deskewing
    ch2_min_index = np.argmin(ch2_skew_mse)
    ch2_skew = skew_points[ch2_min_index] # positive because no longer letting scope deskew
    scope_data = data_array_time_shift_one_signal(scope_data, 0, 2, ch2_skew) # positive again
    
    # re-normalize traces back to true levels
    scope_data[:,1] = scope_data[:,1] * ch1_norm
    scope_data[:,2] = scope_data[:,2] * ch2_norm
    scope_data[:,4] = scope_data[:,4] * ch4_norm
    
    # now find the skew for channel 1 that minimizes Ediss for ideal capacitor
    ch1_skew_Ediss = []
    for skew_val in skew_points:
        current_data = scope_data.copy()
        current_data = data_array_time_shift_one_signal(current_data, 0, 1, skew_val)
        current_Ediss = calculate_Ediss_trap(current_data, freq, trap_dvdt, cref)
        ch1_skew_Ediss.append(abs(current_Ediss)) # want minimum absolute energy level
        
    ch1_min_index = np.argmin(ch1_skew_Ediss)
    ch1_skew = skew_points[ch1_min_index] # positive because no longer letting scope deskew
    scope_data = data_array_time_shift_one_signal(scope_data, 0, 1, ch1_skew)
    
    """
    Optional plotting
    """
    fig1, ax1 = plt.subplots()
    ax1.plot(t[istart1:istop1]*1e9, scope_data[:,1][istart1:istop1])
    ax1.plot(t[istart1:istop1]*1e9, scope_data[:,2][istart1:istop1])
    ax1.plot(t[istart1:istop1]*1e9, scope_data[:,4][istart1:istop1])
    ax1.set(title = 'channel 2 deskew set via MSE minimization')
    
    return [ch1_skew, ch2_skew]
    
"""
Calculating Ediss for trap/sine given saved scope data:
-------------------------------------------------------------------------------
"""

def scale_scope_data_w_cdivs(scope_data, probe_cdivs):
    # applies cdiv ratios to channels 1, 2, 4
    
    scope_data[:,1] = scope_data[:,1] / probe_cdivs[0]
    scope_data[:,2] = scope_data[:,2] / probe_cdivs[1]
    scope_data[:,4] = scope_data[:,4] / probe_cdivs[2]
    return scope_data

def calculate_Ediss_trap(scope_data_og, freq, trap_dvdt, cref):
    # Takes in:
        # scope data as np.ndarray for Ediss calculation
        # freq [Hz], trap_dvdt as fraction of quarter wavelength slope should last:
            # used to determine integration window of rising/falling edges
        # Cref [F] for calculating Qoss
    # Returns Ediss calculation
    
    scope_data = scope_data_og.copy() # leave scope_data_og alone
    
    # general parameters we'll need
    t_res = scope_data[1,0] - scope_data[0,0]
    period = 1/freq
    period_points_float = (1 / freq) / t_res # not rounded for better math
    half_slope_points = round((period_points_float / 4 * trap_dvdt) / 2) # points in half trap slope
    
    # set the t=0 point using smoothed version of channel 1:
        # (better chance of slope center point that way)
    scope_smooth = scope_data.copy() # to leave scope data alone
    scope_smooth[:,1] = gaussian_average_specifying_stdev_time(
        sig = scope_smooth[:,1], t_res = t_res,
        t_stdev = 1e-9) # smooth channel 1 in scope_smooth dataset
    scope_smooth = data_array_set_t0_at_value_crossing(
        scope_smooth, 0, 1, 0, True, 6) # find middle of first rising slope
    scope_data[:,0] = scope_smooth[:,0] # set t0 in the actual data
    t = scope_data[:,0]
    t0_index = np.argmax(t >= 0) # index of t=0 point in dataset
    
    # zero the vout+, vout-, and vref signals correctly
    vout_plus_zeroing_start = period * (3/4 - (1/4)*(2/5))
    vout_plus_zeroing_stop = period * (3/4 + (1/4)*(2/5))
    vout_minus_zeroing_start = period * (1/4 - (1/4)*(2/5))
    vout_minus_zeroing_stop = period * (1/4 + (1/4)*(2/5))
    
    vout_plus = vector_zero_ac_sig_to_trange_avg(
        t = t, sig = scope_data[:,1],
        tstart = vout_plus_zeroing_start, # should be in flat if dvdt < 1/4 wavelength
        tend = vout_plus_zeroing_stop)
    vout_minus = vector_zero_ac_sig_to_trange_avg(
        t = t, sig = scope_data[:,2],
        tstart = vout_minus_zeroing_start, # should be in flat if dvdt < 1/4 wavelength
        tend = vout_minus_zeroing_stop)
    vref = vector_zero_ac_sig_to_trange_avg( # vref has same zeroing window as vout+
        t = t, sig = scope_data[:,4],
        tstart = vout_plus_zeroing_start, # should be in flat if dvdt < 1/4 wavelength
        tend = vout_plus_zeroing_stop)
    
    # determine signals relevant for integration
    vst = vout_plus - vout_minus
    vdut = vout_plus - vref
    vcref = vref - vout_minus
    qoss = vcref*cref
    qoss = qoss - min(qoss) # zero so it's referenced to DUT not Cref
    
    # determine QV integration bounds (eg start/stop of rising and falling edges)
    buffer = 3 # number of extra points to include due to dvdt imperfections
    istart1 = t0_index - half_slope_points - buffer
    istop1 = t0_index + half_slope_points + buffer
    istart2 = t0_index + round(period_points_float/2) - half_slope_points - buffer
    istop2 = t0_index + round(period_points_float/2) + half_slope_points + buffer
    
    # perform integration
    vdut1 = vdut[istart1:istop1]
    vdut2 = vdut[istart2:istop2]
    vdut_int = np.concatenate([vdut1, vdut2])
    
    qoss1 = qoss[istart1:istop1]
    qoss2 = qoss[istart2:istop2]
    qoss_int = np.concatenate([qoss1, qoss2])
    
    t1 = t[istart1:istop1]
    t2 = t[istart2:istop2]
    t_int = np.concatenate([t1, t2])
    
    Ediss = np.trapz(y=vdut_int, x=qoss_int)
    Ediss_cum = integrate.cumtrapz(y=vdut_int, x=qoss_int)
    
    """
    Optional plotting:
    
    # overall saved data plot
    fig1, ax1 = plt.subplots()
    ax1.plot(t, scope_data[:,1], label='vout+')
    ax1.plot(t, scope_data[:,2], label='vout-')
    ax1.plot(t, scope_data[:,3], label='vgate')
    ax1.plot(t, scope_data[:,4], label='vref')
    ax1.legend()
    
    # zeroed data with red markers for integration, blue markers for zeroing
    fig2, ax2 = plt.subplots()
    fig2_max = max(vout_plus)
    fig2_min = min(vout_plus)
    ax2.plot(t, vout_plus, label='vout+')
    ax2.plot(t, vout_minus, label='vout-')
    ax2.plot(t, vref, label='vref')
    ax2.plot(np.array([1,1])*t[istart1], np.array([fig2_max, fig2_min]), 'r')
    ax2.plot(np.array([1,1])*t[istop1], np.array([fig2_max, fig2_min]), 'r')
    ax2.plot(np.array([1,1])*t[istart2], np.array([fig2_max, fig2_min]), 'r')
    ax2.plot(np.array([1,1])*t[istop2], np.array([fig2_max, fig2_min]), 'r')
    ax2.plot(np.array([vout_plus_zeroing_start, vout_plus_zeroing_stop]), np.array([-5, -5]), 'b')
    ax2.plot(np.array([vout_minus_zeroing_start, vout_minus_zeroing_stop]), np.array([-5, -5]), 'b')
    ax2.legend()
    
    # sawyer tower voltage, dut voltage, cref voltage. Red markers for intetration
    fig3, ax3 = plt.subplots()
    fig3_max = max(vst)
    fig3_min = min(vst)
    ax3.plot(t, vst, label = 'vst')
    ax3.plot(t, vdut, label = 'vdut')
    ax3.plot(t, vcref, label = 'vcref')
    ax3.plot(np.array([1,1])*t[istart1], np.array([fig3_max, fig3_min]), 'r')
    ax3.plot(np.array([1,1])*t[istop1], np.array([fig3_max, fig3_min]), 'r')
    ax3.plot(np.array([1,1])*t[istart2], np.array([fig3_max, fig3_min]), 'r')
    ax3.plot(np.array([1,1])*t[istop2], np.array([fig3_max, fig3_min]), 'r')
    ax3.legend()
    
    # Cumulative Eoss over an integration period
    fig4, ax4 = plt.subplots()
    ax4.plot(t_int[1:], Ediss_cum)
    ax4.set(title = 'Cumulative Eoss over integration time')
    
    # QV curve with Ediss value
    fig5, ax5 = plt.subplots()
    ax5.plot(qoss_int[:round(len(qoss_int)/2)], vdut_int[:round(len(qoss_int)/2)], '-*', linewidth=2, color = 'g')
    ax5.plot(qoss_int[round(len(qoss_int)/2):], vdut_int[round(len(qoss_int)/2):], '-*', linewidth=2, color = 'r')
    plt.text(0.05*max(qoss_int), 0.75*max(vdut_int), 'Ediss = ' + str(Ediss), fontsize=8)
    """ # end plotting here
    
    return Ediss

"""
File read/write stuff:
-------------------------------------------------------------------------------
"""
        
def write_run_doc_file(run_doc_write_file, l1_val, l2_val, duty_vref, deskew_vplus, deskew_vminus):
    with open(run_doc_write_file, 'w') as file:
        file.write('Run doc file number of parameters: ' + str(5) + '\n')
        file.write('Inductor 1 value: ' + str(l1_val) + '\n')
        file.write('Inductor 2 value: ' + str(l2_val) + '\n')
        file.write('Duty Vref value: ' + str(duty_vref) + '\n')
        file.write('Vplus deskew: ' + str(deskew_vplus) + '\n')
        file.write('Vminus deskew: ' + str(deskew_vminus) + '\n')
        
def save_ediss_data_csv(file_name, Ediss_values, operating_condition, freq, v_pp, trap_dvdt):
    Ediss_values = np.array(Ediss_values).reshape(len(Ediss_values), 1) # make vertical vector
    # generate vertical sweep variable vector as well
    if operating_condition == 0: # single point
        np.savetxt(file_name, Ediss_values, delimiter=',')
        return # if single point, csv file is boring
    elif operating_condition == 1: # sweping frequency
        sweep = np.array(freq).reshape(len(freq), 1)
    elif operating_condition == 2: # sweeping v_pp
        sweep = np.array(v_pp).reshape(len(v_pp), 1)
    else: # sweeping trap_dvdt
        sweep = np.array(trap_dvdt).reshape(len(trap_dvdt), 1)
        
    # write the file for all cases where there are mutliple values in sweep
    final_array = np.concatenate([sweep, Ediss_values], axis=1)
    np.savetxt(file_name, final_array, delimiter=',')
    
def read_colon_file(file):
    # reads in a file where each line is of the form:
        # 'here is a value: value\n'
    # returns a list of the values in the order they are in the file
    # note values will be strings; you can cast them into what you need later
    # first line must be of the form:
        # 'here is the number of values: N\n' where N is # of values in file
    with open(file, 'r') as f:
        num = int(get_val_after_colon(f.readline()))
        vals = []
        for n in range(num):
            vals.append(get_val_after_colon(f.readline()))
        return vals
        
def print_sweep_type(operating_condition):
    operating_conditions = ['Single point', 'Frequency', 'Vpp', 'Trap dVdt']
    return operating_conditions[operating_condition]
    
def get_val_after_colon(line):
    # takes a line (string) of form 'thing: value\n' and returns 'value'
    return line.strip().split(': ')[1] # remove \n, split on :, take value
    
def read_hardware_setup_file(hw_file):
    # reads in hardware file with probe attenuations and cdiv ratios
    with open(hw_file, 'r') as file: # open file in read mode
        title = get_val_after_colon(file.readline()) # extract title
        
        probe_attenuations = [0, 0, 0, 0]
        for probe in range(4): # pull attenuation for each probe
            probe_attenuations[probe] = int(get_val_after_colon(file.readline()))
        
        probe_cdivs = [0, 0, 0]
        for probe in range(3): # pull cdiv for each probe
            probe_cdivs[probe] = float(get_val_after_colon(file.readline()))
            
    return [probe_attenuations, probe_cdivs]







