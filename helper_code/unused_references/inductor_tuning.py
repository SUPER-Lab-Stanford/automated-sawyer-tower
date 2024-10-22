"""
First part of this file is the algorithm Katherine made to calculate dvdt
Second part uses the scope SlewRate measurement to calculate dvdt
Not sure which is better or it there's an appreciable difference
"""


'''
Algorithm:
1. initialize equipment
2. obtain oscilloscope data and VDC value
3. find dV/dt over the range of 0.2VDC to 0.8VDC (split into 3 cases)
   (a) case #1: oscilloscope waveform starts at -VDC/2 (done with function find_slope)
   (b) case #2: oscilloscope waveform starts at +VDC/2 (done with function find_slope)
   (c) case #3: oscilloscope waveform starts in between 0.2VDC and 0.8VDC (done with function find_slope_all_cases)
4. turn inductors to get within the ballpark of the desired user defined dV/dt
5. find tuning
'''

from decimal import *
import csv
import pyvisa
import time
import serial
import matplotlib.pyplot as plt

# For following, note file tree starts from user_run_file where this file is called from
from helper_code.equipment_control.Equipment_Control_Malachi import *
from helper_code.equipment_control.arduino_coss_communication import *

# imported functions for slewrate measurement algorithm
from helper_code.helper_functions import turn_system_on, turn_system_off, \
    check_HV_power, set_inductor_positions

"""
Start Katherine Algorithm:
"""

"""
#Initialize equipment
oscilloscope = MSO5000('USB0::0x1AB1::0x0515::MS5A243807653::INSTR')
HV_supply = GENH600("/dev/tty.usbserial-AC021RAM")
microcontroller = POWAM_MICRO('/dev/tty.usbserial-110')

#Obtain data and VDC value
user_defined_slope = float(input("Please enter desired dV/dt value [V/s]: "))
data = oscilloscope.readAllChannels()
time_waveform = [row[0] for row in data]
Vout_plus = [row[1] for row in data]
Vdc = HV_supply.readVoltage()

'''
Vdc=50
with open('/Users/katherineliang/PycharmProjects/Coss_Test/helper_code/equipment_control/test_data_16steps.csv', newline='') as csvfile:
    data = list(csv.reader(csvfile))
time_waveform = [row[0] for row in data]
Vout_plus = [row[1] for row in data]
'''


#Find dV/dt over the range of 0.2VDC to 0.8VDC
#Note: Need to consider some edge cases where the waveform starts at a value in between 0.2VDC and 0.8VDC
def find_slope(Vdc, Vout_plus, time):
    Vdc_0p2 = -(Vdc / 2) + 0.2 * Vdc  # okay to do this because channels are AC coupled
    Vdc_0p8 = Vdc / 2 - 0.2 * Vdc
    if float(Vout_plus[0]) < Vdc_0p2:  # first edge will give us rising slope
        flag = 0
        counter = 0
        for i in Vout_plus:
            i = float(i)
            if flag==0 and i>Vdc_0p2:
                rising_edge_bottom = i
                time_rising_edge_bottom = float(time[counter])
                flag=1
            elif flag==1 and i>Vdc_0p8:
                rising_edge_top = i
                time_rising_edge_top = float(time[counter])
                flag = 2
            elif flag==2 and i<Vdc_0p8:
                falling_edge_top = i
                time_falling_edge_top = float(time[counter])
                flag = 3
            elif flag==3 and i<Vdc_0p2:
                falling_edge_bottom = i
                time_falling_edge_bottom = float(time[counter])
                break
            counter +=1
    elif float(Vout_plus[0]) > Vdc_0p8:  # first edge will give us falling slope
        flag = 0
        counter = 0
        for i in Vout_plus:
            i = float(i)
            if flag==0 and i<Vdc_0p8:
                falling_edge_top = i
                time_falling_edge_top = float(time[counter])
                flag=1
            elif flag==1 and i<Vdc_0p2:
                falling_edge_bottom = i
                time_falling_edge_bottom = float(time[counter])
                flag = 2
            elif flag==2 and i>Vdc_0p2:
                rising_edge_bottom = i
                time_rising_edge_bottom = float(time[counter])
                flag = 3
            elif flag==3 and i>Vdc_0p8:
                rising_edge_top = i
                time_rising_edge_top = float(time[counter])
                break
            counter+=1

    rising_slope = (rising_edge_top - rising_edge_bottom) / (time_rising_edge_top - time_rising_edge_bottom)
    falling_slope = (falling_edge_top - falling_edge_bottom) / (time_falling_edge_top - time_falling_edge_bottom)
    return rising_slope, falling_slope

def find_slope_all_cases(Vdc, Vout_plus, time):
    Vdc_0p2 = -(Vdc / 2) + 0.2 * Vdc  # okay to do this because channels are AC coupled
    Vdc_0p8 = Vdc / 2 - 0.2 * Vdc
    if float(Vout_plus[0]) < Vdc_0p2 or float(Vout_plus[0]) > Vdc_0p8:
        rising_slope, falling_slope = find_slope(Vdc, Vout_plus, time)
    elif float(Vout_plus[0]) > Vdc_0p2 and float(Vout_plus[0]) < Vdc_0p8:
        counter = 0
        for i in Vout_plus:
            i=float(i)
            if i>Vdc_0p8 or i<Vdc_0p2:
                Vout_plus_cropped = Vout_plus[counter:]
                time_cropped = time[counter:]
                break
            counter += 1
        rising_slope, falling_slope = find_slope(Vdc, Vout_plus_cropped, time_cropped)
    return rising_slope, falling_slope


rising_slope, falling_slope = find_slope_all_cases(Vdc, Vout_plus, time_waveform)
print(rising_slope, falling_slope)



#Turn inductors to get within the ballpark of the desired user defined dV/dt
slope_change_per_4_steps = 903155
inductor1_turns = int((rising_slope - user_defined_slope)/slope_change_per_4_steps)*4
print(inductor1_turns)
microcontroller.sendCMD('m1' + str(inductor1_turns))
microcontroller.sendCMD('m2' + str(inductor1_turns))
time.sleep(7)
data = oscilloscope.readAllChannels()
time_waveform = [row[0] for row in data]
Vout_plus = [row[1] for row in data]
Vout_plus = Vout_plus
rising_slope, falling_slope = find_slope_all_cases(Vdc, Vout_plus, time_waveform)

print(rising_slope, falling_slope)


#Fine tuning
if rising_slope > user_defined_slope:
    flag = 0
else:
    flag = 1
print(flag)
threshold = 10000000
new_rising_slope = rising_slope
while True:
    if (abs((new_rising_slope - user_defined_slope)) < threshold):
        print("Inductor tuning complete")
        break
    elif flag==0 and not (abs((new_rising_slope - user_defined_slope)) > abs((rising_slope - user_defined_slope))):
        microcontroller.sendCMD('m132')
        microcontroller.sendCMD('m232')
        print('+32')
        time.sleep(5)
        new_data = oscilloscope.readAllChannels()
        new_time_waveform = [row[0] for row in new_data]
        new_Vout_plus = [row[1] for row in new_data]
        new_rising_slope, new_falling_slope = find_slope_all_cases(Vdc, new_Vout_plus, new_time_waveform)
        print(new_rising_slope, new_falling_slope)
    elif flag==1 and not (abs((new_rising_slope - user_defined_slope)) > abs((rising_slope - user_defined_slope))):
        microcontroller.sendCMD('m1-32')
        microcontroller.sendCMD('m2-32')
        print('-32')
        time.sleep(5)
        new_data = oscilloscope.readAllChannels()
        new_time_waveform = [row[0] for row in new_data]
        new_Vout_plus = [row[1] for row in new_data]
        new_rising_slope, new_falling_slope = find_slope_all_cases(Vdc, new_Vout_plus, new_time_waveform)
        print(new_rising_slope, new_falling_slope)
    elif (abs((new_rising_slope - user_defined_slope)) > abs((rising_slope - user_defined_slope))):
        if flag==1:
            flag=0
            rising_slope = 0
            print('reverse')
            continue
        elif flag==0:
            flag=1
            rising_slope = 0
            print('reverse')
            continue
        
"""

"""
End Katherine algorithm, Begin scope slewrate-based tuning algorithm
Main changes:
    - Fine-tuning threshold based on percent error from desired value, not fixed dv/dt:
        - Should give more consistent accuracy across range of dv/dt values
    - Measures d(dV/dt)/d(inductor steps) at operating point for coarse tuning:
        - More flexible than a single value depending on current conditions
Note that it must approach desired slope from above it:
    The scope slew rate measurement gets screwed up when ZVS is lost
    The duty cycle is chosen with some ZVS wiggle room but obviously there is a limit
"""

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

def measure_l1_l2_errors(trap_dvdt, probe_cdivs, scope, HV_supply, LV_supply, arduino):
    # measures L1 and L2 errors
    # returns [ch1_dvdt, ch2_dvdt, l1_error, l2_error]
    turn_system_on(HV_supply, LV_supply, arduino)
    check_HV_power(30, HV_supply, LV_supply, arduino)
    [ch1_dvdt, ch2_dvdt] = measure_ch1_ch2_dvdt_w_pause_and_cdiv(scope, probe_cdivs)
    turn_system_off(HV_supply, LV_supply, arduino)
    l1_error = trap_dvdt - ch2_dvdt # Channel 2 (vout- node) corresponds to L1
    l2_error = trap_dvdt - ch1_dvdt # vice versa
    return [ch1_dvdt, ch2_dvdt, l1_error, l2_error]

def inductor_tuning_trap_scope_based(trap_dvdt, probe_cdivs, scope, HV_supply, LV_supply, arduino):
    # Tunes inductors to achieve desired dv/dt on trapezoidal waveform
    # Note total waveform dvdt should be divided by 2 before using this function
    # Uses scope PSLewrate and NSLewrate measurements to calculate current dvdt
    # Note the indexing is a bit weird because L1 corresponds to Ch2 and vice versa
    
    scope.clearAllMeasItems()
    
    # Measure initial slope values
    [ch1_dvdt, ch2_dvdt, l1_error, l2_error] = measure_l1_l2_errors(
        trap_dvdt, probe_cdivs, scope, HV_supply, LV_supply, arduino)
    
    # Approach desired value from above to avoid poor non-ZVS measurements
    while (l1_error > 0) or (l2_error > 0): # if slope is too shallow and possibly lost ZVS
        l1_new = arduino.l1_pos
        l2_new = arduino.l2_pos
        if l1_error > 0:
            l1_new -= 100 # make it steeper, smaller transition time
        if l2_error > 0:
            l2_new -= 100 # make it steeper, smaller transition time
        set_inductor_positions(LV_supply, arduino, l1_new, l2_new)
        [ch1_dvdt, ch2_dvdt, l1_error, l2_error] = measure_l1_l2_errors(
            trap_dvdt, probe_cdivs, scope, HV_supply, LV_supply, arduino)
    
    # Set up tuning parameters
    error_tol = 0.05 # will stop when within error_tol*trap_dvdt of trap_dvdt
    error_goal = error_tol * trap_dvdt # want error less than this
    give_up_iterations = 10 # if not met error_tol, gives up after this many tries
    l1_off = abs(l1_error) > error_goal # says whether we need to tune L1
    l2_off = abs(l2_error) > error_goal # says whether we need to tune L2
    iteration_count = 0
    while l1_off or l2_off:
        # move the inductors 100 steps to measure dvdt sensitivity to position
        set_inductor_positions(LV_supply, arduino,
                               arduino.l1_pos + 100, arduino.l2_pos + 100)
        [ch1_dvdt_100, ch2_dvdt_100] = measure_l1_l2_errors(
            trap_dvdt, probe_cdivs, scope, HV_supply, LV_supply, arduino)[0:2]
        l1_sensitivity = (ch2_dvdt_100 - ch2_dvdt) / 100 # [dvdt per step]
        l2_sensitivity = (ch1_dvdt_100 - ch1_dvdt) / 100 # [dvdt per step]
        # move the inductors to new positions based on measured sensitivity
        set_inductor_positions(LV_supply, arduino,
                               arduino.l1_pos - 100 + l1_error / l1_sensitivity,
                               arduino.l2_pos - 100 + l2_error / l2_sensitivity)
        # measure new errors before loop ends
        [ch1_dvdt, ch2_dvdt, l1_error, l2_error] = measure_l1_l2_errors(
            trap_dvdt, probe_cdivs, scope, HV_supply, LV_supply, arduino)
        if iteration_count >= give_up_iterations:
            break
        l1_off = abs(l1_error) > error_goal # says whether we need to tune L1
        l2_off = abs(l2_error) > error_goal # says whether we need to tune L2
        iteration_count += 1
        
    
    
    
    









