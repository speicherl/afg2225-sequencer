import sys
from PyQt5.QtWidgets import (QLineEdit, QPushButton, QApplication,
                             QVBoxLayout, QDialog, QComboBox, QLabel, QHBoxLayout)
import pyvisa
from PyQt5 import QtTest
from afg2225library import AFG2225


class Form(QDialog):

    def __init__(self, parent=None):
        super(Form, self).__init__(parent)
        self.status = 'Off'  # Status des Ausgangs
        self.setWindowTitle("GW-Instek AFG-2225 Steuerung")

        # Layouts erstellen
        layout = QVBoxLayout()

        # 1. Signalform-Auswahl (Dropdown)
        layout.addWidget(QLabel("Signalform:"))
        self.combo_wave = QComboBox()
        self.combo_wave.addItems(["sine", "square", "ramp", "pulse", "noise"])
        layout.addWidget(self.combo_wave)

        # 2. Frequenz (Wert + Einheit)
        layout.addWidget(QLabel("Frequenz:"))
        freq_layout = QHBoxLayout()
        self.edit_freq = QLineEdit()
        self.edit_freq.setPlaceholderText("z.B. 1.0")
        self.combo_freq_unit = QComboBox()
        self.combo_freq_unit.addItems(["Hz", "kHz", "MHz"])
        self.combo_freq_unit.setCurrentText("kHz")  # Standardmäßig kHz
        freq_layout.addWidget(self.edit_freq)
        freq_layout.addWidget(self.combo_freq_unit)
        layout.addLayout(freq_layout)

        # 3. Amplitude
        layout.addWidget(QLabel("Amplitude (Vpp):"))
        amp_layout = QHBoxLayout()
        self.edit_amp = QLineEdit()
        self.edit_amp.setPlaceholderText("z.B. 2.5")
        amp_layout.addWidget(self.edit_amp)
        amp_layout.addWidget(QLabel("V"))
        layout.addLayout(amp_layout)

        # 4. DC-Offset
        layout.addWidget(QLabel("DC-Offset:"))
        offset_layout = QHBoxLayout()
        self.edit_offset = QLineEdit()
        self.edit_offset.setPlaceholderText("z.B. 0.0")
        offset_layout.addWidget(self.edit_offset)
        offset_layout.addWidget(QLabel("V"))
        layout.addLayout(offset_layout)

        # 5. Aktions-Buttons
        self.button_set = QPushButton("Parameter anwenden")
        self.button_on = QPushButton("Ausgang Einschalten (Start)")

        layout.addWidget(self.button_set)
        layout.addWidget(self.button_on)

        # Layout zuweisen
        self.setLayout(layout)

        # Signale verknüpfen
        self.button_set.clicked.connect(self.update_generator_settings)
        self.button_on.clicked.connect(self.setOnOff)

    def update_generator_settings(self):
        try:
            # Werte aus der UI auslesen und konvertieren
            waveform = self.combo_wave.currentText()
            freq_value = float(self.edit_freq.text()) if self.edit_freq.text() else 1.0
            freq_unit = self.combo_freq_unit.currentText()
            amp_value = float(self.edit_amp.text()) if self.edit_amp.text() else 1.0
            offset_value = float(self.edit_offset.text()) if self.edit_offset.text() else 0.0

            print(f"Sende: {waveform}, {freq_value} {freq_unit}, {amp_value} Vpp, Offset: {offset_value} V")

            # Befehle nacheinander mit kurzen Pausen absetzen
            my_instrument.set_waveform(waveform)
            QtTest.QTest.qWait(50)

            my_instrument.set_frequency(freq_value, freq_unit)
            QtTest.QTest.qWait(50)

            my_instrument.set_amplitude(amp_value)
            QtTest.QTest.qWait(50)

            my_instrument.set_offset(offset_value)
            print("Parameter erfolgreich an das Gerät übertragen.")

        except ValueError:
            print("Fehler: Bitte trage gültige Zahlen in die Textfelder ein!")
        except Exception as e:
            print(f"Fehler bei der Kommunikation: {e}")

    def setOnOff(self):
        try:
            if self.status == 'Off':
                my_instrument.turn_on()
                self.button_on.setText('Ausgang Ausschalten (Stop)')
                self.status = 'On'
            else:
                my_instrument.turn_off()
                self.button_on.setText('Ausgang Einschalten (Start)')
                self.status = 'Off'
        except Exception as e:
            print(f"Fehler beim Schalten des Ausgangs: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    form = Form()
    form.show()

    try:
        # Initialisierung über das funktionierende virtuelle serielle Backend
        my_instrument = AFG2225.AFG2225('ASRL/dev/ttyACM0::INSTR')

        # Starte Qt Event-Loop
        sys.exit(app.exec_())

    except Exception as e:
        print("Verbindung zum Funktionsgenerator fehlgeschlagen:", e)
