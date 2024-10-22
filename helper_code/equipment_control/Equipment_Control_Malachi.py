# This script was generously provided by Eric Stolt (stolt@stanford.edu) to program various lab equipment.

# Edited by Malachi to include Rigol MSO5000 series oscilloscope

import serial
import time
import pyvisa
import numpy as np

#RIGOL MSO5000 series oscilloscope (we have lots of MSO5074 scopes)
class MSO5000:
    CMD_DELAY = 0.1
    TIMEOUT = 5.0
    
    def __init__(self, visa_name): # visa_name is likely something like 'USB0::0x1AB1::0x0515::MS5A243807653::INSTR'
        self.rm = pyvisa.ResourceManager()
        self.rm.list_resources()
        
        # initialize connection. Tries a few times then quits if it's not working
        self.connected = False
        for n in range(4):
            try:
                self.inst = self.rm.open_resource(visa_name)
                self.connected = True
                break # skip rest of for loop
            except pyvisa.VisaIOError:
                print("RIGOL MSO5000 connection unsuccessful. Ensure USB is connected. Trying again...")
                time.sleep(5)
        if not(self.connected):
            print("\nRIGOL MSO5000 unable to connect. Double check USB address using Ultra Sigma software, as well as USB connection, then try again.")
            raise(SystemExit)
        
        # check the IDN is correct. If not, quit
        self.devID = self.inst.query("*IDN?")
        time.sleep(self.CMD_DELAY)
        if self.devID[:26] == 'RIGOL TECHNOLOGIES,MSO5074':
            print("Rigol MSO5000 Oscilloscope Connection Successful!")
            self.fault = False
        else:
            print("\nRigol MSO5000 ID Number (from query(\"*IDN?\") not as expected.")
            print("Expected to contain: 'RIGOL TECHNOLOGIES,MSO5074'.")
            print("Actual value: " + self.devID)
            print("Double check equipment type and expected IDN, then try again")
            raise(SystemExit)
        return
    
    def sendCMD(self, cmd):
        self.inst.write(cmd)
        time.sleep(self.CMD_DELAY)
        
    def queryCMD(self, cmd):
        self.inst.write(cmd)
        time.sleep(self.CMD_DELAY)
        rxVal = self.inst.read()
        return rxVal
    
    def run(self):
        self.sendCMD("RUN")
        
    def stop(self):
        self.sendCMD("STOP")\
            
    def single(self):
        self.sendCMD("SING")
        
    def forceTrigger(self):
        self.sendCMD("TFOR")
        
    def autoscale(self):
        self.sendCMD("AUT")
        
    def clear(self):
        self.sendCMD("CLE")
        
    def turnChannelOn(self, channel_index):
        self.sendCMD(':CHANnel' + str(channel_index) + ':DISPlay ON')
        
    def turnChannelOff(self, channel_index):
        self.sendCMD(':CHANnel' + str(channel_index) + ':DISPlay OFF')
        
    def readChannel(self, channel_index):
        # reads a channel into np.array with columns for time and values
        # channel_index: 1-4
        return self.readChannelOrMath(False, channel_index)
    
    def readChannelAveraged(self, channel_index, number_of_samples):
        # reads a channel into np.array, averaged over number_of_samples
        # note: may need to ensure delay is long enough for scope to refresh
        sample1 = self.readChannel(channel_index)
        t1 = sample1[:,0] # pull out time; will be the same in all samples
        val_sum = sample1[:,1] # will sum values then divide to find average
        for index in range(number_of_samples - 1):
            time.sleep(self.CMD_DELAY) # give scope screen time to refresh
            val_sum += self.readChannel(channel_index)[:,1]
        vals = val_sum / number_of_samples # compute average
        return np.stack((t1, vals), 1)
    
    def readMathChannel(self, channel_index):
        # reads a math channel into np.array with columns for time and values
        # channel_index: 1-4
        return self.readChannelOrMath(False, channel_index)
    
    def readMathChannelAveraged(self, channel_index, number_of_samples):
        # reads a math channel into np.array, averaged over number_of_samples
        # note: may need to ensure delay is long enough for scope to refresh
        sample1 = self.readMathChannel(channel_index)
        t1 = sample1[:,0] # pull out time; will be the same in all samples
        val_sum = sample1[:,1] # will sum values then divide to find average
        for index in range(number_of_samples - 1):
            time.sleep(self.CMD_DELAY) # give scope screen time to refresh
            val_sum += self.readMathChannel(channel_index)[:,1]
        vals = val_sum / number_of_samples # compute average
        return np.stack((t1, vals), 1)
    
    def readAllChannels(self):
        # reads all channels into np.array. Column 0 is time, then channels
        self.stop()
        for n in range(4): # for all 4 channels
            data = self.readChannel(n+1)
            if n == 0: # get time from first channel
                output = data # has time and values column
            else:
                [t,ch_values] = np.hsplit(data, 2) # pull out values column
                output = np.hstack((output, ch_values)) # add new values col
        self.run()
        return output
    
    def readAllChannelsAveraged(self, number_of_samples):
        # reads all channels into np.array, averaging over number_of_samples
        # note: make sure sleep time is enough to refresh entire scope screen
        sample1 = self.readAllChannels()
        t1 = sample1[:,0] # pull out time; will be the same in all samples
        val_sum = sample1[:,1:] # will sum values then divide to find average
        for index in range(number_of_samples - 1):
            time.sleep(5*self.CMD_DELAY) # to ensure scope screen refreshes
            val_sum += self.readAllChannels()[:,1:]
        vals = val_sum / number_of_samples # compute average
        return np.concatenate((t1[:, None], vals), 1)
    
    def saveAllChannels(self, file_name_csv):
        # saves trace data from all channels into a csv
        # file_name_csv must include '.csv' in the string
        data = self.readAllChannels()
        np.savetxt(file_name_csv, data, delimiter=',')
        
# Below are helper functions for the class's main functions
    
    def readChannelOrMath(self, math_channel, channel_index):
        # reads a channel into np.array with columns for time and values
        # math_channel: True if measuring math channel, False if normal channel
        # channel_index: 1-4 for both regular and math channels
        self.sendCMD(":WAV:MODE NORMal") # reads what's on the screen
            # note: could read entire memory too, but don't think I'll need it
        self.sendCMD("WAV:FORMat ASCii") # only form VISA buffer recognizes
        self.sendCMD("WAV:POINts MAX") # all the points on the screen
        if math_channel:
            self.sendCMD(":WAV:SOURce MATH" + str(channel_index))
        else:
            self.sendCMD(":WAV:SOURce CHAN" + str(channel_index))
        
        wave_vector = self.asciiToVector(self.queryCMD("WAV:DATA?"))
        time_vector = self.getTimeVector(len(wave_vector))
        return np.stack((time_vector, wave_vector), 1)
    
    def asciiToVector(self, asc):
        asc = asc[11:-2] # remove header and footer
        values = [float(i) for i in asc.split(',')] # makes a list
        return np.asarray(values)
        
    def getTimeVector(self, num_points):
        xInc = float(self.queryCMD(":WAV:XINC?"))
        xOrigin = float(self.queryCMD(":WAV:XOR?"))
        time_vector = np.arange(0, num_points) * xInc # build vector
        return time_vector + xOrigin # set time-scale correctly

#Functions for Startup - Added May 21st, 2024
    def setAttenuationFactor(self, probe_number, attenuation_factor):
		#Sets attenuation factor of user-defined 'probe_number' to user-defined 'attenuation_factor'
        cmd = (':CHANnel' + str(probe_number) + ':PROBe ' + str(attenuation_factor))
        # print(cmd)
        self.sendCMD(cmd)

    def setCoupling(self, probe_number, coupling):
		#Sets coupling of user-defined 'probe_number' to user-defined 'coupling', which can be DC, AC or GND
        cmd = (':CHANnel' + str(probe_number) + ':COUPling ' + str(coupling))
        # print(cmd)
        self.sendCMD(cmd)

    def setDataAcquisitionType(self, typ): # type is a preset python word, so use typ
		#Sets data acquisition type, which can be: NORMal|AVERages|PEAK|HRESolution
        cmd = (':ACQuire:TYPE ' + str(typ))
        # print(cmd)
        self.sendCMD(cmd)

    def setDataAcquisitionAverage(self, count):
		#In average data acquisition mode, 'count' sets the number of cycles over which to average over
        cmd = (':ACQuire:AVERages ' + str(count))
        # print(cmd)
        self.sendCMD(cmd)
    
    def queryMeasItem(self, item, source):
        # Returns instantaneous measurement item from source
        cmd1 = 'MEASure:ITEM ' + str(item) + ',CHANnel' + str(source)
        self.sendCMD(cmd1)
        cmd2 = 'MEASure:ITEM? ' + str(item) + ',CHANnel' + str(source)
        return float(self.queryCMD(cmd2))
    
    def queryStatItem(self, typ, item, source): # type is a preset python word, so use typ
		# Obtains the value of item given the statistical type and source 
        cmd1 = (':MEASure:STATistic:ITEM ' + str(item) + ',CHANnel' + str(source))
        self.sendCMD(cmd1)
        cmd2 = (':MEASure:STATistic:ITEM? ' + str(typ) + ',' + str(item) + ',CHANnel' + str(source))
        # print(cmd2)
        value = self.queryCMD(cmd2)
        return float(value)
    
    def resetMeasStats(self):
        # Resets the statistics measurements, eg starting count from 0 again
        self.sendCMD(':MEASure:STATistic:RESet')
    
    def clearMeasItem(self, item_index):
        # Clears one of the measurements. item_index ranges from 1 to 10
        self.sendCMD(':MEASure:CLEar ITEM' + str(item_index))
        
    def clearAllMeasItems(self):
        # Clears all of the measurements from the scope screen
        self.sendCMD(':MEASure:CLEar ALL')
    
# Functions for setting oscillscope windowing/scaling
    def setChannelScale(self, channel_index, volt_scale):
        # Sets the vertical scale of a single channel (in Volts)
        # Takes in the full-screen scale, eg 8x what the scope will display as the scale
        # automatically sets channel in fine-tuning scale mode to allow more values
        # note if you enter a value that isn't allowed, it rounds down to nearest allowed
        scope_scale_bars = 8
        volt_scale = volt_scale / scope_scale_bars # accounts for scope using 8 scale bars
        self.sendCMD(':CHANnel' + str(channel_index) + ':VERNier ON') # allows fine adjustment
        self.sendCMD(':CHANnel' + str(channel_index) + ':SCALe ' + str(volt_scale))
        
    def setChannelZeroLocation(self, channel_index, volts):
        # Sets the zero location [Volts] of a single channel
        # Positive value moves channel up on the screen
        self.sendCMD(':CHANnel' + str(channel_index) + ':OFFSet ' + str(volts))
        
    def setTimeScale(self, time_scale):
        # Sets the horizontal time scale for all channels (in seconds)
        # Takes in the full-screen scale, eg 10x what the scope will display as the scale
        # automatically sets timebase to fine-tuning to allow more values
        # note if you enter a value that isn't allowed, it rounds down to nearest allowed
        scope_scale_bars = 10
        time_scale = time_scale / scope_scale_bars # accounts for scoe using 10 scale bars
        self.sendCMD(':TIMebase:VERNier ON')
        self.sendCMD(':TIMebase:MAIN:SCALe ' + str(time_scale))
        
    def setTimeZeroLocation(self, time):
        # Sets the zero location [seconds] on the time axis, eg where the trigger is on the screen
        # Positive value shifts trigger to the left
        self.sendCMD(':TIMebase:MAIN:OFFSet ' + str(time))
        
    def setChannelDeskew(self, channel_index, deskew):
        # Sets the deskew [seconds] of a channel relative to the other channels
        # deskew can be sci. notation (eg 5e-8) or long form (eg 0.00000005)
        self.sendCMD(':CHANnel' + str(channel_index) + ':TCALibrate ' + str(deskew))
        

#RIGOL DP832 DC Power Supply
class DP832:
	CMD_DELAY = 0.2
	TIMEOUT = 5.0

	def __init__(self, visa_name):
		self.rm = pyvisa.ResourceManager()
		self.rm.list_resources()
		self.inst = self.rm.open_resource(visa_name)
		self.devID=self.inst.query("*IDN?")
		# time delay
		time.sleep(self.CMD_DELAY)
		if (self.devID != 0):
			if "RIGOL TECHNOLOGIES,DP832A,DP8B171800380,00.01.13" in self.devID:
			#if "RIGOL TECHNOLOGIES,DP832,DP8C185151480,00.01.14" in self.devID:
				self.connected = True
				self.fault = False
				return
		self.connected = False # Malachi thinks there should be an "else" here
		self.fault = True
		return

	def sendCMD(self, cmd):
		self.inst.write(cmd)
		time.sleep(self.CMD_DELAY)

	def queryCMD(self, cmd):
		self.inst.write(cmd)
		time.sleep(self.CMD_DELAY)
		rxVal = self.inst.read()
		return rxVal

	def setCH1(self):
		cmd = 'INST CH1'
		self.sendCMD(cmd)

	def setCH2(self):
		cmd = 'INST CH2'
		self.sendCMD(cmd)

	def setCH3(self):
		cmd = 'INST CH3'
		self.sendCMD(cmd)

	def setCurrent(self, currentVal):
		cmd = ('SOUR:CURR ' + "%.3f" % currentVal)
		self.sendCMD(cmd)

	def setVoltage(self, voltageVal):
		cmd = ('SOUR:VOLT ' + "%.3f" % voltageVal)
		self.sendCMD(cmd)

	def enableChannel(self):
		cmd = 'OUTP ON'
		self.sendCMD(cmd)

	def disableChannel(self):
		cmd = 'OUTP OFF'
		self.sendCMD(cmd)

	def enableMaster(self):
		cmd = 'OUTP CH1,ON'
		self.sendCMD(cmd)
		cmd = 'OUTP CH2,ON'
		self.sendCMD(cmd)
		cmd = 'OUTP CH3,ON'
		self.sendCMD(cmd)

	def disableMaster(self):
		cmd = 'OUTP CH1,OFF'
		self.sendCMD(cmd)
		cmd = 'OUTP CH2,OFF'
		self.sendCMD(cmd)
		cmd = 'OUTP CH3,OFF'
		self.sendCMD(cmd)

	def readVoltage(self):
		cmd = 'MEAS:VOLT?'
		retVal = self.queryCMD(cmd)
		if retVal != None:
			return float(retVal)

	def readCurrent(self):
		cmd = 'MEAS:CURR?'
		retVal = self.queryCMD(cmd)
		if retVal != None:
			return float(retVal)

	def setSeriesVoltage(self, voltageVal):
		self.setCH1()
		self.setVoltage(voltageVal / 2.0)
		self.setCH2()
		self.setVoltage(voltageVal / 2.0)

	def setSeriesCurrent(self, currentVal):
		self.setCH1()
		self.setCurrent(currentVal)
		self.setCH2()
		self.setCurrent(currentVal)


#Agilent/Keysight N5771A DC Power Supply
class N5700:
	CMD_DELAY = 0.2
	TIMEOUT = 5.0

	def __init__(self, visa_name):
		self.rm = pyvisa.ResourceManager()
		self.rm.list_resources()
		self.inst = self.rm.open_resource(visa_name)
		self.devID=self.inst.query("*IDN?");
		# time delay
		time.sleep(self.CMD_DELAY)
		if (self.devID != 0):
			if "Agilent Technologies,N5771A,US13L1509M,A.05.05,REV:E" in self.devID:
				self.connected = True
				self.fault = False
				return
		self.connected = False
		self.fault = True
		return

	def sendCMD(self, cmd):
		self.inst.write(cmd)
		time.sleep(self.CMD_DELAY)

	def queryCMD(self, cmd):
		self.inst.write(cmd)
		time.sleep(self.CMD_DELAY)
		rxVal = self.inst.read()
		return rxVal

	def setCurrent(self, currentVal):
		cmd = ('CURR ' + "%.3f" % currentVal)
		self.sendCMD(cmd)

	def setVoltage(self, voltageVal):
		cmd = ('VOLT ' + "%.3f" % voltageVal)
		self.sendCMD(cmd)

	def enableMaster(self):
		cmd = 'OUTP ON'
		self.sendCMD(cmd)

	def disableMaster(self):
		cmd = 'OUTP OFF'
		self.sendCMD(cmd)

	def readVoltage(self):
		cmd = 'MEAS:VOLT?'
		retVal = self.queryCMD(cmd)
		if retVal != None:
			return float(retVal)

	def readCurrent(self):
		cmd = 'MEAS:CURR?'
		retVal = self.queryCMD(cmd)
		if retVal != None:
			return float(retVal)


#Agilent N1914A Power Meter
class N1914A:
	CMD_DELAY = 1
	TIMEOUT = 5.0

	def __init__(self, visa_name):
		self.rm = pyvisa.ResourceManager()
		self.rm.list_resources()
		self.inst = self.rm.open_resource(visa_name)
		self.devID=self.inst.query("*IDN?");
		# time delay
		time.sleep(self.CMD_DELAY)
		if (self.devID != 0):
			if "Agilent Technologies,N1914A,MY53400008,A2.01.09" in self.devID:
				self.connected = True
				self.fault = False
				return
		self.connected = False
		self.fault = True
		return

	def sendCMD(self, cmd):
		self.inst.write(cmd)
		time.sleep(self.CMD_DELAY)

	def queryCMD(self, cmd):
		self.inst.write(cmd)
		time.sleep(self.CMD_DELAY)
		rxVal = self.inst.read()
		return rxVal

	def selectTable(self, tablename):
		cmd = ('MEM:TABL:SEL \"'+tablename+'\"')
		print(cmd)
		self.sendCMD(cmd)

	def setFreq(self, f):
		cmd = ('MEM:TABL:FREQ ' + f)
		print(cmd)
		self.sendCMD(cmd)

	def setGain(self, g):
		cmd = ('MEM:TABL:GAIN ' + g)
		print(cmd)
		self.sendCMD(cmd)

#BK Precision DC Load https://bkpmedia.s3.amazonaws.com/downloads/programming_manuals/en-us/8600_Series_programming_manual.pdf
class BK8602:
	CMD_DELAY = 0.1
	TIMEOUT = 5.0

	def __init__(self, visa_name):
		self.rm = pyvisa.ResourceManager()
		self.rm.list_resources()
		self.inst = self.rm.open_resource(visa_name)
		self.devID = self.inst.query("*IDN?");
		self.devID
		# time delay
		time.sleep(self.CMD_DELAY)
		if (self.devID != 0):
			if "B&K Precision, 8602, 802201020737510010, 1.37-1.42" in self.devID:
				self.connected = True
				self.fault = False
				return
		self.connected = False
		self.fault = True
		return

	def sendCMD(self, cmd):
		self.inst.write(cmd)
		time.sleep(self.CMD_DELAY)

	def queryCMD(self, cmd):
		self.inst.write(cmd)
		time.sleep(self.CMD_DELAY)
		rxVal = self.inst.read()
		return rxVal

	def configVoltage(self):
		#lock control pannel
		cmd = 'SYST:REM'
		self.sendCMD(cmd)

		cmd = 'SOUR:INP 0'
		self.sendCMD(cmd)
		#set in voltage mode
		cmd = 'SOUR:FUNC VOLT'
		self.sendCMD(cmd)

	def configCurrent(self):
		#lock control pannel
		cmd = 'SYST:REM'
		self.sendCMD(cmd)

		cmd = 'SOUR:INP 0'
		self.sendCMD(cmd)
		#set in voltage mode
		cmd = 'SOUR:FUNC CURR'
		self.sendCMD(cmd)

	def configResistance(self):
		#lock control pannel
		cmd = 'SYST:REM'
		self.sendCMD(cmd)

		cmd = 'SOUR:INP 0'
		self.sendCMD(cmd)
		#set in voltage mode
		cmd = 'SOUR:FUNC RES'
		self.sendCMD(cmd)


	def setVoltage(self, voltage):
		cmd = ('SOUR:VOLT ' + "%.2f" % voltage)
		self.sendCMD(cmd)

	def setCurrent(self, current):
		cmd = ('SOUR:CURR ' + "%.2f" % current)
		self.sendCMD(cmd)

	def setResistance(self, resistance):
		cmd = ('SOUR:Res ' + "%.2f" % resistance)
		self.sendCMD(cmd)

	def enableOutput(self):
		cmd = 'SOUR:INP 1'
		self.sendCMD(cmd)

	def disableOutput(self):
		cmd = 'SOUR:INP 0'
		self.sendCMD(cmd)

	def readVoltage(self):
		cmd = 'MEAS:VOLT?'
		retVal = self.queryCMD(cmd)
		if retVal != None:
			return float(retVal)

	def readCurrent(self):
		cmd = 'MEAS:CURR?'
		retVal = self.queryCMD(cmd)
		if retVal != None:
			return float(retVal)

	def readPower(self):
		cmd = 'FETC:POW?'
		retVal = self.queryCMD(cmd)
		if retVal != None:
			return float(retVal)

class IT8511B:
	CMD_DELAY = 0.2
	TIMEOUT = 5.0

	def __init__(self, serialfd):
		#initalize USB serial 
		self.ser = serial.Serial(serialfd, 9600, timeout=1)
		#check identity of power supply 
		self.ser.write(b'*IDN?\n') #sometimes wakeup is needed?
		self.ser.flush()
		self.ser.reset_input_buffer()
		time.sleep(self.CMD_DELAY)
		self.ser.flush()
		self.ser.write(b'*IDN?\n')
		#time delay 
		time.sleep(self.CMD_DELAY)
		if (self.ser.in_waiting != 0):
			deviceID = self.ser.read(self.ser.in_waiting)
			if "ITECH Ltd., IT8511B" in deviceID.decode():
				self.connected = True
				self.fault = False
				return 
		self.connected = False
		self.fault = True
		return

	def sendCMD(self, cmd):
		self.ser.reset_input_buffer()
		self.ser.write(cmd+b'\n')
		self.ser.flush()
		time.sleep(self.CMD_DELAY)
		if (self.ser.in_waiting != 0):
			rxVal = self.ser.read(self.ser.in_waiting)
			return rxVal
		else:
			return None

	def configVoltage(self):
		#lock control pannel
		cmd = b'SYST:REM'
		self.sendCMD(cmd)

		cmd = b'SOUR:INP 0'
		self.sendCMD(cmd)
		#set in voltage mode
		cmd = b'SOUR:FUNC VOLT'
		self.sendCMD(cmd)

	def configCurrent(self):
		#lock control pannel
		cmd = b'SYST:REM'
		self.sendCMD(cmd)

		cmd = b'SOUR:INP 0'
		self.sendCMD(cmd)
		#set in voltage mode
		cmd = b'SOUR:FUNC CURR'
		self.sendCMD(cmd)


	def setVoltage(self, voltage):
		cmd = ('SOUR:VOLT ' + "%.2f" % voltage).encode()
		self.sendCMD(cmd)

	def setCurrent(self, current):
		cmd = ('SOUR:CURR ' + "%.2f" % current).encode()
		self.sendCMD(cmd)

	def enableOutput(self):
		cmd = b'SOUR:INP 1'
		self.sendCMD(cmd)

	def disableOutput(self):
		cmd = b'SOUR:INP 0'
		self.sendCMD(cmd)

	def readVoltage(self):
		cmd = b'MEAS:VOLT?'
		retVal = self.sendCMD(cmd)
		if retVal != None:
			return float(retVal)

	def readCurrent(self):
		cmd = b'MEAS:CURR?'
		retVal = self.sendCMD(cmd)
		if retVal != None:
			return float(retVal)

	def readPower(self):
		cmd = b'MEAS:POW?'
		retVal = self.sendCMD(cmd)
		if retVal != None:
			return float(retVal)

class HMC8042:
	CMD_DELAY = 0.2
	TIMEOUT = 5.0

	def __init__(self, serialfd):
		#initalize USB serial 
		self.ser = serial.Serial(serialfd, 9600, timeout=1)
		#check identity of power supply 
		self.ser.write(b'*IDN?\n') #sometimes wakeup is needed?
		self.ser.flush()
		self.ser.reset_input_buffer()
		time.sleep(self.CMD_DELAY)
		self.ser.flush()
		self.ser.write(b'*IDN?\n')
		#time delay 
		time.sleep(self.CMD_DELAY)
		if (self.ser.in_waiting != 0):
			deviceID = self.ser.read(self.ser.in_waiting)
			if "Rohde&Schwarz,HMC8042" in deviceID.decode():
				self.connected = True
				self.fault = False
				return 
		self.connected = False
		self.fault = True
		return

	def sendCMD(self, cmd):
		self.ser.reset_input_buffer()
		self.ser.write(cmd+b'\n')
		#self.ser.flush()
		time.sleep(self.CMD_DELAY)
		if (self.ser.in_waiting != 0):
			rxVal = self.ser.read(self.ser.in_waiting)
			return rxVal
		else:
			return None

	def setCH1(self):
		cmd = b'INST OUT1'
		self.sendCMD(cmd)

	def setCH2(self):
		cmd = b'INST OUT2'
		self.sendCMD(cmd)

	def setCurrent(self, currentVal):
		cmd = ('SOUR:CURR ' + "%.3f" % currentVal).encode()
		self.sendCMD(cmd)

	def setVoltage(self, voltageVal):
		cmd = ('SOUR:VOLT ' + "%.3f" % voltageVal).encode()
		self.sendCMD(cmd)

	def enableChannel(self):
		cmd = b'OUTP:CHAN 1'
		self.sendCMD(cmd)

	def disableChannel(self):
		cmd = b'OUTP:CHAN 0'
		self.sendCMD(cmd)

	def enableMaster(self):
		cmd = b'OUTP:MAST 1'
		self.sendCMD(cmd)

	def disableMaster(self):
		cmd = b'OUTP:MAST 0'
		self.sendCMD(cmd)

	def readVoltage(self):
		cmd = b'MEAS:VOLT?'
		retVal = self.sendCMD(cmd)
		if retVal != None:
			return float(retVal)

	def setSeriesVoltage(self, voltageVal):
		self.setCH1()
		self.setVoltage(voltageVal/2.0)
		self.setCH2()
		self.setVoltage(voltageVal/2.0)

	def setSeriesCurrent(self, currentVal):
		self.setCH1()
		self.setCurrent(currentVal)
		self.setCH2()
		self.setCurrent(currentVal)


	def readCurrent(self):
		cmd = b'MEAS:CURR?'
		retVal = self.sendCMD(cmd)
		if retVal != None:
			return float(retVal)

class Controller:
	CMD_DELAY = 0.1
	TIMEOUT = 1.0

	def __init__(self, serialfd):
		#initalize USB serial 
		self.ser = serial.Serial(serialfd, 38400, timeout=1)
		time.sleep(1)
		#check identity of power supply 
		# self.ser.write(b'*IDN?\n') #sometimes wakeup is needed?
		# self.ser.flush()
		# self.ser.reset_input_buffer()
		#time.sleep(self.CMD_DELAY)
		# self.ser.flush()
		self.ser.write(b'*IDN?\n')
		#time delay 
		time.sleep(self.CMD_DELAY)
		if (self.ser.in_waiting != 0):
			deviceID = self.ser.read(self.ser.in_waiting)
			if "PIEZO CTRL V1.0" in deviceID.decode():
				self.connected = True
				self.fault = False
				return 
		self.connected = False
		self.fault = True
		return

	def sendCMD(self, cmd):
		#self.ser.write(cmd+b'\n')
		#self.ser.flush()
		line = cmd+b'\n'
		for i in line:
			self.ser.write(i.to_bytes(1,'big'))
			#time.sleep(0.5)
		time.sleep(self.CMD_DELAY)


	def sendQUERY(self, cmd):
		self.ser.write(cmd+b'\n')
		#self.ser.flush()
		time.sleep(self.CMD_DELAY)
		rxVal = self.ser.readline()

		if (rxVal != b''):
			return rxVal
		else:
			return None

	def enableOutput(self):
		cmd = b'OUTP:EN'
		self.sendCMD(cmd)
	
	def disableOutput(self):
		cmd = b'OUTP:DIS'
		self.sendCMD(cmd)

	def setFreq(self, frequency):
		#print(('SET:FREQ ' + '%d' % frequency).encode())
		cmd = ('SET:FREQ ' + '%d' % frequency).encode()
		self.sendCMD(cmd)

	def measureFreq(self):
		cmd = 'SET:FREQ?'.encode()
		retVal = self.sendQUERY(cmd)
		if retVal != None:
			try:
				int(retVal)
			except ValueError:
				retVal = 0
			return int(retVal)

	def incFreq(self):
		cmd = b'+'
		self.sendCMD(cmd)

	def decFreq(self):
		cmd = b'-'
		self.sendCMD(cmd)

	def setReg(self, reg, value):
		if((reg<9) and (value<256)):
			cmd = ('SET:REG ' + '%d' % reg + ' %d' % value).encode('utf-8')
			self.sendCMD(cmd)

	def setMix(self, reg, value):
		if((reg<3) and (value<257)):
			cmd = ('SET:MIX ' + '%d' % reg + ' %d' % value).encode('utf-8')
			self.sendCMD(cmd)

	def readReg(self, reg):
		if(reg<9):
			cmd = ('SET:REG? ' + '%d' % reg).encode('utf-8')
			res = self.sendQUERY(cmd)
			if res != None:
				return int(res)

class GENH600: # updated to close serial after use leaving available for future
	CMD_DELAY = 0.1
	TIMEOUT = 5.0

	def __init__(self, serialfd):
		#initalize USB serial
		self.serialfd = serialfd
		with serial.Serial(self.serialfd, 19200, timeout=1) as ser:
            # check identity of power supply
			ser.write(b'ADR 6\r') #sometimes wakeup is needed?
			ser.flush()
			ser.write(b'RST\r') #reset supply
			ser.flush()
			ser.write(b'IDN?\r') #sometimes wakeup is needed?
			ser.flush()
			time.sleep(self.CMD_DELAY)
			ser.reset_input_buffer()
			time.sleep(self.CMD_DELAY)
			ser.flush()
			ser.write(b'IDN?\r')
			#time delay
			time.sleep(self.CMD_DELAY)
			if (ser.in_waiting != 0):
				deviceID = ser.read(ser.in_waiting)
				if "LAMBDA,GEN600-1.3-USB" in deviceID.decode():
	
					self.connected = True
					self.fault = False
					return
			self.connected = False
			self.fault = True
			return

	def sendCMD(self, cmd):
		with serial.Serial(self.serialfd, 19200, timeout=1) as ser:
			ser.reset_input_buffer()
			ser.write(cmd+b'\r')
			#self.ser.flush()
			time.sleep(self.CMD_DELAY)
			if (ser.in_waiting != 0):
				rxVal = ser.read(ser.in_waiting)
				return rxVal
			else:
				return None

	def setVoltage(self, voltageVal):
		cmd = ('PV ' + "%.3f" % voltageVal).encode()
		self.sendCMD(cmd)

	def readVoltage(self):
		cmd = b'MV?'
		retVal = self.sendCMD(cmd)
		if retVal != None:
			return float(retVal)

	def setCurrent(self, currentVal):
		cmd = ('PC ' + "%.3f" % currentVal).encode()
		self.sendCMD(cmd)

	def readCurrent(self):
		cmd = b'MC?'
		retVal = self.sendCMD(cmd)
		if retVal != None:
			return float(retVal)

	def enableMaster(self):
		cmd = b'OUT 1'
		self.sendCMD(cmd)

	def disableMaster(self):
		cmd = b'OUT 0'
		self.sendCMD(cmd)


#CHROMA 63804
class CHROMA:
	CMD_DELAY = 0.25
	TIMEOUT = 5.0

	def __init__(self, serialfd):

		#initalize USB serial
		self.ser = serial.Serial(serialfd, 57600, timeout=1)
		time.sleep(1)
		self.ser.write(b'*IDN?\n')
		#time delay
		time.sleep(self.CMD_DELAY)
		if (self.ser.in_waiting != 0):
			deviceID = self.ser.read(self.ser.in_waiting)
			#print(deviceID.decode())
			if "Chroma,63804" in deviceID.decode():
				self.connected = True
				self.fault = False
				return
		self.connected = False
		self.fault = True
		return

	def sendCMD(self, cmd):
		self.ser.reset_input_buffer()
		self.ser.write(cmd + b'\n')

	def queryCMD(self, cmd):
		self.ser.reset_input_buffer()
		self.ser.write(cmd + b'\n')
		# self.ser.flush()
		time.sleep(self.CMD_DELAY)
		if (self.ser.in_waiting != 0):
			rxVal = self.ser.read(self.ser.in_waiting)
			return rxVal
		else:
			return None

	def configVoltage(self):
		cmd = b':SYST:DEF:RECA ON'
		self.sendCMD(cmd)
		time.sleep(2)
		cmd = b':SYST:SET:MODE DC'
		self.sendCMD(cmd)
		cmd = b':LOAD:MODE VOLT'
		self.sendCMD(cmd)

	def configCurrent(self):
		cmd = b':SYST:SET:MODE DC'
		self.sendCMD(cmd)
		cmd = b':LOAD:MODE CURR'
		self.sendCMD(cmd)

	def setVoltage(self, voltage):
		cmd = (':LOAD:VOLT:DC ' + "%.2f" % voltage).encode()
		self.sendCMD(cmd)

	def setCurrent(self, current):
		cmd = (':LOAD:CURR:DC ' + "%.2f" % current).encode()
		self.sendCMD(cmd)

	def setCurrentLim(self, current):
		cmd = (':LOAD:CURR:MAX:DC ' + "%.2f" % current).encode()
		self.sendCMD(cmd)

	def enableOutput(self):
		cmd = b':LOAD ON'
		self.sendCMD(cmd)

	def disableOutput(self):
		cmd = b':LOAD OFF'
		self.sendCMD(cmd)

	def readVoltage(self):
		cmd = b':MEAS:VOLT?'
		retVal = self.queryCMD(cmd)
		if retVal != None:
			return float(retVal)

	def readSetVoltage(self):
		cmd = b':VOLT:DC?'
		retVal = self.queryCMD(cmd)
		if retVal != None:
			return float(retVal)

	def readCurrent(self):
		cmd = b':MEAS:CURR?'
		retVal = self.queryCMD(cmd)
		if retVal != None:
			return float(retVal)

	def readPower(self):
		cmd = b':MEAS:POW?'
		retVal = self.queryCMD(cmd)
		if retVal != None:
			return float(retVal)

# http://mikrosys.prz.edu.pl/KeySight/34410A_Quick_Reference.pdf
class DMM34411A:
	CMD_DELAY = 0.1
	TIMEOUT = 5.0
	def __init__(self, visa_name):
		self.rm = pyvisa.ResourceManager()
		self.rm.list_resources()
		self.inst = self.rm.open_resource(visa_name)
		self.devID = self.inst.write("*RST")
		time.sleep(1)
		self.devID = self.inst.query("*IDN?")
		#print(self.devID)
		# time delay
		time.sleep(self.CMD_DELAY)
		if (self.devID != 0):
			if "Agilent Technologies,344" in self.devID:
				self.connected = True
				self.fault = False
				return
		self.connected = False
		self.fault = True
		self.configV()
		return

	def sendCMD(self, cmd):
		self.inst.write(cmd)
		time.sleep(self.CMD_DELAY)

	def queryCMD(self, cmd):
		self.inst.write(cmd)
		time.sleep(self.CMD_DELAY)
		rxVal = self.inst.read()
		return rxVal

	def measVDC(self):
		cmd = 'MEAS:VOLT:DC?'
		retVal = self.queryCMD(cmd)
		if retVal != None:
			return float(retVal)

	def measIDC(self):
		cmd = 'MEAS:CURR:DC?'
		retVal = self.queryCMD(cmd)
		if retVal != None:
			return float(retVal)

	def measIDC2(self):
		cmd = 'MEAS:VOLT:DC?'
		retVal = self.queryCMD(cmd)
		if retVal != None:
			return 1000*float(retVal)

	def configV(self):
		self.sendCMD('VOLT:NPLC 10')

	def configI(self):
		self.sendCMD('CURR:NPLC 1')

#https://www.keysight.com/us/en/assets/9018-04842/service-manuals/9018-04842.pdf
class DMM34450A:
	CMD_DELAY = 0.4
	TIMEOUT = 5.0
	def __init__(self, visa_name):
		self.rm = pyvisa.ResourceManager()
		self.rm.list_resources()
		self.inst = self.rm.open_resource(visa_name)
		self.devID = self.inst.write("*RST")
		time.sleep(1)
		self.devID = self.inst.query("*IDN?")
		#print(self.devID)
		# time delay
		time.sleep(self.CMD_DELAY)
		if (self.devID != 0):
			if "Agilent Technologies,34450" in self.devID:
				self.connected = True
				self.fault = False
				return
		self.connected = False
		self.fault = True
		return

	def sendCMD(self, cmd):
		self.inst.write(cmd)
		time.sleep(self.CMD_DELAY)

	def queryCMD(self, cmd):
		self.inst.write(cmd)
		time.sleep(self.CMD_DELAY)
		rxVal = self.inst.read()
		return rxVal

	def measVDC(self):
		cmd = 'MEAS:VOLT:DC?'
		retVal = self.queryCMD(cmd)
		if retVal != None:
			return float(retVal)

	def measIDC(self):
		cmd = 'MEAS:CURR:DC? 10,3.0e-5'
		retVal = self.queryCMD(cmd)
		if retVal != None:
			return float(retVal)


#MAGNA-POWER  https://magna-power.com/assets/files/manuals/ts_49297.pdf
class TSA1000:
	CMD_DELAY = 0.4
	TIMEOUT = 5.0

	def __init__(self, serialfd):
		#initalize USB serial
		self.ser = serial.Serial(serialfd, 19200, timeout=1)
		time.sleep(self.CMD_DELAY)
		self.ser.write(b'*RST\n')
		time.sleep(self.CMD_DELAY)
		#check identity of power supply
		self.ser.write(b'*IDN?\n')
		#time delay
		time.sleep(self.CMD_DELAY)
		if (self.ser.in_waiting != 0):
			deviceID = self.ser.read(self.ser.in_waiting)
			#print(deviceID)
			if "Magna-Power Electronics Inc." in deviceID.decode():
				self.connected = True
				self.fault = False
				self.sendCMD(b'CONF:SETPT 3\n')
				return
		self.connected = False
		self.fault = True
		return

	def sendCMD(self, cmd):
		self.ser.reset_input_buffer()
		self.ser.write(cmd+b'\n')

	def queryCMD(self, cmd):
		self.ser.reset_input_buffer()
		self.ser.write(cmd+b'\n')
		#self.ser.flush()
		time.sleep(self.CMD_DELAY)
		if (self.ser.in_waiting != 0):
			rxVal = self.ser.read(self.ser.in_waiting)
			return rxVal
		else:
			return None

	def setVoltage(self, voltageVal):
		cmd = ('VOLT ' + "%.1f" % voltageVal).encode()
		self.sendCMD(cmd)

	def readVoltage(self):
		cmd = b'MEAS:VOLT?'
		retVal = self.queryCMD(cmd)
		if retVal != None:
			return float(retVal)

	def setCurrent(self, currentVal):
		cmd = ('CURR ' + "%.1f" % currentVal).encode()
		self.sendCMD(cmd)

	def readCurrent(self):
		cmd = b'MEAS:CURR?'
		retVal = self.queryCMD(cmd)
		if retVal != None:
			return float(retVal)

	def enableMaster(self):
		cmd = b'OUTP:START'
		self.sendCMD(cmd)

	def disableMaster(self):
		cmd = b'OUTP:STOP'
		self.sendCMD(cmd)
