# -*- coding: utf-8 -*-
"""
Created on Mon Jun  3 14:45:27 2024

@author: hornb
"""
import serial 
import time 
import struct
from arduino_coss_communication import POWAM_MICRO

port = 'COM5'
arduino = POWAM_MICRO(port)

arduino.setSineFreq(2)
arduino.setSineAmp(5)
arduino.setDutyCycleRefValue(2.5)
arduino.enableTrapMode()
arduino.enableGateSignals()
print('Gate signals on for 5 seconds...')
time.sleep(5)
arduino.disableGateSignals()
print('Gate signals off')

still_working = arduino.checkAlive()
if still_working:
    print('Arduino is still working')
else:
    print('Arduino not working at end of script, address this issue')




