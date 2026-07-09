from afg2225library import AFG2225
import time


my_instrument = AFG2225.AFG2225('ASRL/dev/ttyACM0::INSTR') #USE COM-Port

# set waveform, frequency and amplitude, then turn channel 1 on and off, switch settings and turn on and off again
my_instrument.set_waveform('sine')  # available waveforms "sine", "square", "ramp", "pulse", "noise"
my_instrument.set_frequency(2.1, 'kHz')  # available units: "MHz", "kHz", "Hz", "mHz", "uHz"
my_instrument.set_amplitude(120, 'mV')  # available units: "V", "mV"
my_instrument.turn_on()
time.sleep(3)  # wait for 3 seconds
my_instrument.turn_off()
my_instrument.set_waveform('square')
my_instrument.set_frequency(2, 'mHz')
my_instrument.set_amplitude(3, 'V')
my_instrument.turn_on()
time.sleep(2)  # wait for 2 seconds
my_instrument.turn_off()

my_instrument.close()  # close communication (not necessary)

