# -*- coding: utf-8 -*-
"""
Created on Fri May 17 21:39:18 2024

@author: hornb
"""

"""
Instructions overview:
    Each instruction is a string consisting of a letter, second character, then number.
    The letter tells arduino which type of instruction to execute, second character
    tells it more info about the instruction, and then the number may tell is more
    information if necessary. The number can be basically anything; integers, negative
    numbers, decimals, etc. are fair game (assuming they make sense in the context
    of the instruction). If the second character could be anything, meaning it doesn't
    affect the instruction execution, it's noted as 'X'. If the number could be anything
    it's noted as '_XX'
Current acceptable instructions:
    'i1___' - Analog reference value: only 1 channel now. ___ is value 0-5V
    'l#___' - move inductor # to inductance value ___ (characterization likely not very accurate)
    'm#___' - move inductor # by ___ steps (could be negative)
    'c#___' - move inductor # by ___ steps and "zero" off of final position
    'p#___' - move inductor # to position ___ based on current calibration
    'w#_XX' - where is the inductor: prints out position of inductor #
    'rX_XX' - ready? Returns 1 if inductors done moving, 0 if not done yet
    'aa___' - change AD9913 current amplitude to ___ (4.58mA max, but it will round down if needed)
    'af___' - change AD9913 frequency to ___ (Hz, so probably has lots of zeros like my credit card bill)
    'aX_XX' - general reset and update of AD9913 if bad communication cycle. X can be anything
    'zX_XX' - test connection to the arduino board. Returns 'ATMEGA328P is still alive' if working
    't#_XX' - set sine or trap mode; # is 0 or 1. 0 means sine, 1 means trap
    'e#_XX' - set gate signal enable; # is 0 or 1. 0 turns all gates off, 1 allows them to switch
"""

import serial 
import time 
import struct

#Class for the arduino uno ATMEGA328P on poweramerica control board
class POWAM_MICRO:
    CMD_DELAY = 0.1
    TIMEOUT = 5.0
    BAUDRATE = 115200 # happens to be what the arduino is configured for
    
    def __init__(self, port_name): # port_name is likely something like '/dev/ttyUSB0' on linux, 'COM5' on windows
        self.port_name = port_name
        with serial.Serial(port=self.port_name, baudrate=self.BAUDRATE, timeout=self.CMD_DELAY) as comm:
        # "with" statement means the serial connection will close when finished
        # Test that the connection is working, or throw an error if not
            trash = comm.readline() # empty out serial connection just in case
            connection_test_cmd = '\'' + 'z' + '\'' # '' needed apparently :(
            # For some reason, using 'z1' or str('z1') doesn't work... idk
            for n in range(len(connection_test_cmd)):
                comm.write(bytes(connection_test_cmd[n], 'utf-8'))
            comm.write(bytes('\n', 'utf-8'))
            time.sleep(self.CMD_DELAY)
            return_data = comm.readline().decode('utf-8')
        # serial connection closes here, freeing up port for future use
        if return_data != 'ATMEGA328P is still alive\n':
            print('\nArduino Uno failed connectivity test\n' + 
                  'Reply received: ' + str(return_data) + '\n' + 
                  'Reply expected: ' + 'ATMEGA328P is still alive\n')
            raise(SystemExit)
        print('Arduino Uno connected successfully.')
        self.l1_pos = 0 # going to store inductor positions in object as well
        self.l2_pos = 0 # assume inductors are calibrated
    
    def sendCMD(self, cmd):
        # sends command (a string) directly to arduino. Recieves no response
        self.__serial_send_receive__(cmd)
        
    def queryCMD(self, cmd):
        # sends command (a string) directly to arduino and returns the response
        rxVal = self.__serial_send_receive__(cmd)
        return rxVal
    
    def __serial_send_receive__(self, cmd):
        # note for private methods, must include __ when calling as well
        cmd = '\'' + str(cmd) + '\'' # adding '' makes it work oof
        with serial.Serial(port=self.port_name, baudrate=self.BAUDRATE, timeout=self.CMD_DELAY) as comm:
            for n in range(len(cmd)):
                comm.write(bytes(cmd[n], 'utf-8'))
            comm.write(bytes('\n', 'utf-8'))
            time.sleep(self.CMD_DELAY)
            return comm.readline().decode('utf-8')
        # serial connection closes here, freeing up port for future use
        
    def troubleshootConnection(self):
        with serial.Serial(port=self.port_name, baudrate=self.BAUDRATE, timeout=self.CMD_DELAY) as comm:
            stringy = '\'' + 'z' + '\''
            for n in range(len(stringy)):
                comm.write(bytes(stringy[n], 'utf-8'))
            comm.write(bytes('\n', 'utf-8'))
            time.sleep(0.05)
            data = comm.readline()
            print('Troubleshoot received: ')
            print(data)
        
    def checkAlive(self):
        # returns True if arduino responds as expected, False if not
        response = self.queryCMD('z')
        if response == 'ATMEGA328P is still alive\n':
            return True
        else: return False
        
    def updateIndPositionsFromArduino(self):
        # pulls inductor values of the arduino
        self.l1_pos = int(self.queryCMD('w1'))
        self.l2_pos = int(self.queryCMD('w2'))
        
    def waitForInductorsToMove(self):
        # literally just delays until the inductors are finished moving
        print('Moving inductors...')
        time.sleep(0.5) # wait just a bit in case
        ready = self.queryCMD('r')
        while not(bool(int(ready[0]))): # pulls 1 or 0 out from ready string
            time.sleep(1) # wait a second and try again
            ready = self.queryCMD('r')
        print(' done\n')
                
    def setDutyCycleRefValue(self, val):
        # Sets analog reference value that gets compared with sine for duty cycle
        # val can be from 0 to 5
        self.sendCMD('i1' + str(val))
        
    def setIndVal(self, ind_number, val_uh):
        # Sets inductor number to value in micro Henrys (characterization not so accurate)
        self.sendCMD('l' + str(ind_number) + str(val_uh))
        self.updateIndPositionsFromArduino()
        
    def moveInd(self, ind_number, steps):
        # Moves inductor number by steps number of steps (200 steps per rotation)
        self.sendCMD('m' + str(ind_number) + str(steps))
        self.updateIndPositionsFromArduino()
        
    def calInd(self, ind_number, steps):
        # Moves inductor number by steps and calibrates that new position as "zero"
        self.sendCMD('c' + str(ind_number) + str(steps))
        self.updateIndPositionsFromArduino()
        
    def setIndPos(self, ind_number, pos):
        self.sendCMD('p' + str(ind_number) + str(pos))
        self.updateIndPositionsFromArduino()
        
    def setSineAmp(self, val_mA):
        # max is 4.58mA, so typically use value 0-4.58. Higher vals default to max
        self.sendCMD('aa' + str(val_mA / 1e3))
        
    def setSineFreq(self, freq_MHz):
        # sets frequency of AD9913 DDS. Value is in MHz, above ~40 probably too high
        # arduino code accounts for current PLL, so the frequency will be correct
        
        # currently automatically uses PLL of 14 (overclocking by 40%) if freq > 5 MHz:
            # if I would like this to not happen, here is easiest place to change it
        if freq_MHz > 5:
            self.setSinePLL(14) # overclocking, but seems to work consistently so far
        else: self.setSinePLL(10) # normal clocking rate
        
        self.sendCMD('af' + str(round(freq_MHz * 1e6)))
        
    def setSinePLL(self, pll_multiplier):
        # sets PLL multiplier of AD9913 DDS. Takes integer from 1 to 31
        # default value is 10 for normal operation at 250MHz based on 25MHz clock
        # after calling this function, call setSineFreq again to correct the frequency
        self.sendCMD('ax' + str(pll_multiplier))
        
    def resetSine(self):
        # Resets AD9913 with current stored instructions in case of glitch
        self.sendCMD('a1')
        
    def enableSineMode(self):
        # enables current source class E sine mode operation
        self.sendCMD('t1')
        
        """
        TODO: verify sine mode and trap mode commands work with both boards
        """
        
    def enableTrapMode(self):
        # enables voltage mode class D trapezoiddal mode operation
        self.sendCMD('t0')
        
    def enableGateSignals(self):
        # turns on gate signals headed to zikang hybrid converter
        self.sendCMD('e1')
        
    def disableGateSignals(self):
        # turns off gate signals headed to zikang hybrid converter
        self.sendCMD('e0')
    
    
    
    
    
    
    
    


