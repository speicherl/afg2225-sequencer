import sys
from PyQt5.QtWidgets import (QLineEdit, QPushButton, QApplication,
                             QVBoxLayout, QDialog)
import pyvisa
from PyQt5 import QtTest
from afg2225library import AFG2225


class Form(QDialog):

    def __init__(self, parent=None):
        super(Form, self).__init__(parent)
        self.status = 'Off'  # output on or off

        # Create widgets with modern placeholders instead of default text
        self.edit_freq = QLineEdit()
        self.edit_freq.setPlaceholderText("Frequenz eingeben (z.B. 1.5)")

        self.edit_amp = QLineEdit()
        self.edit_amp.setPlaceholderText("Amplitude eingeben (z.B. 2.0)")

        self.button_set = QPushButton("Change Waveform")
        self.button_on = QPushButton("Start")

        # Create layout and add widgets
        layout = QVBoxLayout()
        layout.addWidget(self.edit_freq)
        layout.addWidget(self.edit_amp)
        layout.addWidget(self.button_set)
        layout.addWidget(self.button_on)

        # Set dialog layout
        self.setLayout(layout)

        # Add button signal to greetings slot
        self.button_set.clicked.connect(self.update_button_set)
        self.button_on.clicked.connect(self.setOnOff)

    def update_button_set(self):
        try:
            # TEXT IN ZAHLEN (FLOAT) UMWANDELN:
            freq_value = float(self.edit_freq.text())
            amp_value = float(self.edit_amp.text())

            # Wichtig: Im GUI-Code steht standardmäßig "MHz" als Argument,
            # deine Platzhalter sagten "kHz". Wenn du 1000 eingibst bei MHz, sind das 1000 MHz (1 GHz).
            # Ich lasse es hier auf "MHz", passe deine Eingabe im Kopf oder die Einheit hier an.
            my_instrument.set_frequency(freq_value, "kHz")

            QtTest.QTest.qWait(50) # Warten für das serielle Backend

            my_instrument.set_amplitude(amp_value)
            print(f"Erfolgreich gesetzt: {freq_value} MHz, {amp_value} V")

        except ValueError:
            print("Fehler: Bitte gültige Zahlen in die Textfelder eingeben!")

    def setOnOff(self):
        if self.status == 'Off':
            my_instrument.turn_on()
            self.button_on.setText('Stop')
            self.status = 'On'
        else:
            my_instrument.turn_off()
            self.button_on.setText('Start')
            self.status = 'Off'


if __name__ == '__main__':
    # Create the Qt Application
    app = QApplication(sys.argv)
    # Create and show the form
    form = Form()
    form.show()

    try:
        # Verbindung über unser funktionierendes ASRL/py-Backend aufbauen
        my_instrument = AFG2225.AFG2225('ASRL/dev/ttyACM0::INSTR')

        # Run the main Qt loop
        sys.exit(app.exec_())

    except Exception as e:
        print("No device connected or Error:", e)
