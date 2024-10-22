'''
Algorithm:
1. get current value from HV supply
2. increase Vref until new current > old current
3. revert to last Vref value
'''

"""
Didn't use this code directly because energy(duty_cycle) function isn't monotone
(eg you could hit a local minimum that isn't the global minimum)
Still used this basic structure in the duty_cycle_tuning_trap function though
"""

import pyvisa
from equipment_control.Equipment_Control_Malachi import *
from arduino_coss_communication import *

#Initialize equipment
HV_supply = GENH600("/dev/tty.usbserial-AC021RAM")
microcontroller = POWAM_MICRO('/dev/tty.usbserial-110')

#Initialize reference voltage to 2.9
microcontroller.setDutyCycleRefValue(2.9)
Vref = 2.9
supply_current = HV_supply.readCurrent()
print(Vref, supply_current)

#Increase Vref until current value starts going up
while True:
    new_Vref = Vref + 0.1
    microcontroller.setDutyCycleRefValue(new_Vref)
    time.sleep(2)
    new_supply_current = HV_supply.readCurrent()
    print(new_Vref, new_supply_current)
    if new_supply_current <= supply_current:
        Vref = new_Vref
        supply_current = new_supply_current
    else:
        microcontroller.setDutyCycleRefValue(Vref)
        print(Vref)
        print("Duty cycle tuning complete")
        break