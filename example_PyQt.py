import sys
from PyQt5.QtWidgets import (QLineEdit, QPushButton, QApplication,
                             QVBoxLayout, QDialog, QLabel, QHBoxLayout)
import pyvisa
from PyQt5 import QtTest
from afg2225library import AFG2225


class Form(QDialog):

    def __init__(self, parent=None):
        super(Form, self).__init__(parent)
        self.status = 'Off'
        self.setWindowTitle("AFG-2225 - Rampen-Steuerung")
        self.setMinimumWidth(350)

        layout = QVBoxLayout()

        # 1. Info-Label
        layout.addWidget(QLabel("<b>Modus: Dreieck / Rampe (RAMP)</b>"))
        layout.addWidget(QLabel("--------------------------------------------------"))

        # 2. Symmetrie / Steigung
        layout.addWidget(QLabel("Steigung / Symmetrie (0.0% bis 100.0%):"))
        self.edit_symmetry = QLineEdit("50.0")
        self.edit_symmetry.setPlaceholderText("50.0 = Dreieck, 100.0 = Sägezahn")
        layout.addWidget(self.edit_symmetry)

        # 3. Frequenz
        layout.addWidget(QLabel("Frequenz:"))
        freq_layout = QHBoxLayout()
        self.edit_freq = QLineEdit("1.0")
        self.combo_freq_unit = QComboBox() if 'QComboBox' in globals() else None
        # Falls QComboBox nicht importiert war, fangen wir das hier kurz ab:
        from PyQt5.QtWidgets import QComboBox
        self.combo_freq_unit = QComboBox()
        self.combo_freq_unit.addItems(["Hz", "kHz", "MHz"])
        self.combo_freq_unit.setCurrentText("kHz")
        freq_layout.addWidget(self.edit_freq)
        freq_layout.addWidget(self.combo_freq_unit)
        layout.addLayout(freq_layout)

        # 4. Amplitude
        layout.addWidget(QLabel("Amplitude (Vpp):"))
        amp_layout = QHBoxLayout()
        self.edit_amp = QLineEdit("2.0")
        amp_layout.addWidget(self.edit_amp)
        amp_layout.addWidget(QLabel("V"))
        layout.addLayout(amp_layout)

        # 5. DC-Offset
        layout.addWidget(QLabel("DC-Offset:"))
        offset_layout = QHBoxLayout()
        self.edit_offset = QLineEdit("0.0")
        offset_layout.addWidget(self.edit_offset)
        offset_layout.addWidget(QLabel("V"))
        layout.addLayout(offset_layout)

        # 6. Aktions-Buttons
        self.button_set = QPushButton("Rampe auf Gerät laden")
        self.button_on = QPushButton("Ausgang Einschalten (Start)")

        layout.addWidget(self.button_set)
        layout.addWidget(self.button_on)

        self.setLayout(layout)

        # Signale verknüpfen
        self.button_set.clicked.connect(self.update_generator_settings)
        self.button_on.clicked.connect(self.setOnOff)

    def update_generator_settings(self):
        try:
            # Werte auslesen
            sym_value = float(self.edit_symmetry.text()) if self.edit_symmetry.text() else 50.0
            freq_value = float(self.edit_freq.text()) if self.edit_freq.text() else 1.0
            freq_unit = self.combo_freq_unit.currentText()
            amp_value = float(self.edit_amp.text()) if self.edit_amp.text() else 1.0
            offset_value = float(self.edit_offset.text()) if self.edit_offset.text() else 0.0

            print(f"Sende Rampe: {freq_value} {freq_unit}, {amp_value} Vpp, Symmetrie: {sym_value}%")

            # Befehle nacheinander mit 100ms Atempause an ttyACM0 senden
            my_instrument.set_waveform("ramp")
            QtTest.QTest.qWait(100)

            my_instrument.set_ramp_symmetry(sym_value)
            QtTest.QTest.qWait(100)

            my_instrument.set_frequency(freq_value, freq_unit)
            QtTest.QTest.qWait(100)

            my_instrument.set_amplitude(amp_value)
            QtTest.QTest.qWait(100)

            my_instrument.set_offset(offset_value)

            print("Rampe erfolgreich synchronisiert!")

        except ValueError:
            print("Fehler: Bitte nur gültige Zahlen eintragen.")
        except Exception as e:
            print(f"Verbindungsfehler: {e}")

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
            print(f"Fehler am Ausgang: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    form = Form()
    form.show()

    try:
        my_instrument = AFG2225.AFG2225('ASRL/dev/ttyACM0::INSTR')
        sys.exit(app.exec_())
    except Exception as e:
        print("Verbindung fehlgeschlagen:", e)
