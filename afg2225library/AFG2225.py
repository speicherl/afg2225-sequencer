"""
Class for controlling many basic functions of the GW-Instek AFG2225 function generator using the pyvisa library
code written by Peter Ruppen, 20.9.2019
Modified for multi-platform GUI and external Resource Manager support, 2026
"""

import pyvisa
from time import time, sleep
from numpy import format_float_scientific
import serial.tools.list_ports


class AFG2225:

    # NEU: Optionaler resource_manager-Parameter hinzugefügt
    def __init__(self, port='automatic', resource_manager=None):
        try:
            # Falls von außen (z.B. aus der GUI) ein funktionierender Manager
            # mitgegeben wird, nutzen wir diesen. Sonst erstellen wir einen Standard-Manager.
            if resource_manager is not None:
                self.rm = resource_manager
            else:
                self.rm = pyvisa.ResourceManager()

            self.port = port
            if self.port == 'automatic':
                self.port = self.select_port()

            self.instrument = self.rm.open_resource(self.port)
            self.timeout = 1
            _, self.SN = self.check_connection()
        except Exception as e:
            print("no device connected or error during init:", e)

    def select_port(self):
        """
        Function returns the name/number of the port where the AFG2225 function generator is connected via USB.
        :return port: port name (COMx) where the afg is connected
        """
        ports = serial.tools.list_ports.comports()
        for port, desc, hwid in sorted(ports):
            if "AFG" in desc:
                print("Function Generator connected to port: " + port)
                return port
        return 'automatic'

    def format_str(self, number, digits):
        """
        Function returns number in a scientific format that is equivalent to the format that is returned by the
        function generator when queried: e.g. +2.15000000000000E+06.
        """
        s = format_float_scientific(number, precision=7, exp_digits=2, trim='k')
        mantissa, exp = s.split('e')
        if float(mantissa) >= 0:
            format_number = "+" + mantissa
        else:
            format_number = mantissa

        format_number = format_number + (digits - len(format_number)) * "0" + "E" + exp
        return format_number

    def send_command(self, command, query, codeword):
        """
        Function sends command to function generator and makes sure that the command is executed.
        """
        command = command + ';*OPC?'
        query_return = self.instrument.query(query)
        timeout = time() + self.timeout
        while not (query_return.__contains__(codeword)):
            self.instrument.write(command)
            self.instrument.read()
            query_return = self.instrument.query(query)
            if time() > timeout:
                print('timeout while changing waveform')
                break

    def check_connection(self):
        """
        Checks connection by querying the function generator manufacturer, model number, serial number and firmware.
        """
        query_return = self.instrument.query('*IDN?')
        if 'GW INSTEK' in query_return:
            return 0, query_return
        else:
            return -1, ''

    def set_waveform(self, waveform='sine', channel=1):
        """
        Function to change the waveform.
        """
        waveforms = {
            "sine": "SIN",
            "square": "SQU",
            "ramp": "RAMP",
            "pulse": "PULS",
            "noise": "NOIS"}
        waveform = waveforms[waveform]
        syntax = "SOURCE" + str(channel) + ":FUNCTION"
        command = syntax + " " + waveform
        query = syntax + "?"
        self.send_command(command, query, waveform)

    def square_polarity(self, duty=0.5, channel=1):
        """
        Function to change the waveform to a square wave with alternating polarity.
        """
        resolution = 100
        length_peak = int(duty * resolution)
        command = "SOURce" + str(channel) + ":DATA:DAC VOLATILE," + length_peak * "511, " + (resolution - length_peak)\
                  * "0, " + length_peak * "-511, " + (resolution - length_peak - 1) * "0, " + "0;*OPC?"
        self.instrument.write(command)

    def arbitrary_wave(self, wave, channel=1):
        """
        Function to change the waveform to an arbitrary wave.
        """
        wave_text = str(wave).replace("[", "").replace("]", "")
        command = "SOURce" + str(channel) + ":DATA:DAC VOLATILE, 0, " + wave_text + ";*OPC?".format(channel)
        self.instrument.write(command)

    def set_frequency(self, frequency, unit="Hz", channel=1):
        """
        Function to change the frequency.
        """
        unit_dict = {'MHz': 10**6, 'kHz': 10**3, 'Hz': 1, 'mHz': 10**-3, 'uHz': 10**-6}
        syntax = "SOURCE" + str(channel) + ":FREQUENCY"
        command = syntax + " " + str(frequency) + str(unit)
        query = syntax + "?"
        codeword = self.format_str(frequency * unit_dict[unit], 16)
        self.send_command(command, query, codeword)

    def set_offset(self, offset, unit="V", channel=1):
        """
        Function to change the DC offset.
        """
        unit_dict = {'mV': 0.001, 'V': 1}
        syntax = "SOURCE" + str(channel) + ":DCOffset"
        command = syntax + " " + str(offset * unit_dict[unit])
        query = syntax + "?"
        codeword = self.format_str(offset * unit_dict[unit], 5)
        self.send_command(command, query, codeword)

    def set_amplitude(self, amplitude, unit='V', channel=1):
        """
        Function to change the peak-to-peak voltage amplitude (Vpp).
        """
        unit_dict = {'mV': 0.001, 'V': 1}
        syntax = "SOURCE" + str(channel) + ":AMPLITUDE"
        command = syntax + " " + str(amplitude*unit_dict[unit])
        query = syntax + "?"
        codeword = self.format_str(amplitude * unit_dict[unit], 6)
        self.send_command(command, query, codeword)

    def set_ramp_symmetry(self, symmetry, channel=1):
        """
        Function to change the symmetry (slope) of a ramp/triangle wave.
        """
        try:
            symmetry = max(0.0, min(100.0, float(symmetry)))
            syntax = "SOURCE" + str(channel) + ":RAMP:SYMMetry"
            command = syntax + " " + str(symmetry)
            query = syntax + "?"
            codeword = self.format_str(symmetry, 5)
            self.send_command(command, query, codeword)
        except Exception as e:
            print("Error while setting ramp symmetry:", e)

    def turn_on(self, channel=1):
        """
        Turns a channel on.
        """
        syntax = "OUTPUT" + str(channel)
        command = syntax + " ON"
        query = syntax + "?"
        codeword = "1"
        self.send_command(command, query, codeword)

    def turn_off(self, channel=1):
        """
        Turns a channel off.
        """
        syntax = "OUTPUT" + str(channel)
        command = syntax + " OFF"
        query = syntax + "?"
        codeword = "0"
        self.send_command(command, query, codeword)

    def close(self):
        """
        Closes the resource manager.
        """
        try:
            self.rm.close()
        except:
            print("device could not be closed!")


if __name__ == "__main__":
    instr = AFG2225()
    connected, SN = instr.check_connection()
    if connected == 0:
        print(SN + ' connected.')
    else:
        print('no device connected')
    instr.set_frequency(20, 'Hz')
