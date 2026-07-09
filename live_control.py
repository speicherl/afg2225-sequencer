import sys
from time import sleep
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QLineEdit, QComboBox, QPushButton)

class LiveControlDialog(QDialog):
    def __init__(self, instrument, parent=None):
        super(LiveControlDialog, self).__init__(parent)
        self.my_instrument = instrument

        self.setWindowTitle("🎛️ Live-Direktansteuerung")
        self.setFixedWidth(350)

        layout = QVBoxLayout()

        # Status-Anzeige
        self.lbl_status = QLabel("<b>Status: Live-Modus aktiv</b>")
        self.lbl_status.setStyleSheet("color: #2b579a;")
        layout.addWidget(self.lbl_status)

        # Frequenz-Einstellung
        freq_group = QGroupBox("Frequenz")
        freq_layout = QHBoxLayout()
        self.edit_freq = QLineEdit("100")
        self.combo_freq_unit = QComboBox()
        self.combo_freq_unit.addItems(["Hz", "kHz", "MHz"])
        self.btn_set_freq = QPushButton("Senden")
        freq_layout.addWidget(self.edit_freq)
        freq_layout.addWidget(self.combo_freq_unit)
        freq_layout.addWidget(self.btn_set_freq)
        freq_group.setLayout(freq_layout)
        layout.addWidget(freq_group)

        # Amplitude-Einstellung
        amp_group = QGroupBox("Amplitude (Vpp)")
        amp_layout = QHBoxLayout()
        self.edit_amp = QLineEdit("1.0")
        self.btn_set_amp = QPushButton("Senden")
        amp_layout.addWidget(self.edit_amp)
        amp_layout.addWidget(self.btn_set_amp)
        amp_group.setLayout(amp_layout)
        layout.addWidget(amp_group)

        # Offset-Einstellung
        offset_group = QGroupBox("DC-Offset (V)")
        offset_layout = QHBoxLayout()
        self.edit_offset = QLineEdit("0.0")
        self.btn_set_offset = QPushButton("Senden")
        offset_layout.addWidget(self.edit_offset)
        offset_layout.addWidget(self.btn_set_offset)
        offset_group.setLayout(offset_layout)
        layout.addWidget(offset_group)

        # Signalform-Auswahl
        wave_group = QGroupBox("Signalform")
        wave_layout = QHBoxLayout()
        self.combo_wave = QComboBox()
        self.combo_wave.addItems(["sine", "square", "ramp", "pulse", "noise"])
        wave_layout.addWidget(self.combo_wave)
        wave_group.setLayout(wave_layout)
        layout.addWidget(wave_group)

        # Sondermodi (Burst & Co ausschalten)
        mode_group = QGroupBox("Sondermodi (Burst / Sweep)")
        mode_layout = QVBoxLayout()
        self.btn_disable_modes = QPushButton("💥 Burst / Sweep / Mod komplett AUS")
        self.btn_disable_modes.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold; padding: 4px;")
        mode_layout.addWidget(self.btn_disable_modes)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        self.setLayout(layout)

        # Event-Verknüpfungen
        self.btn_set_freq.clicked.connect(self.update_frequency)
        self.edit_freq.returnPressed.connect(self.update_frequency)

        self.btn_set_amp.clicked.connect(self.update_amplitude)
        self.edit_amp.returnPressed.connect(self.update_amplitude)

        self.btn_set_offset.clicked.connect(self.update_offset)
        self.edit_offset.returnPressed.connect(self.update_offset)

        self.combo_wave.currentTextChanged.connect(self.update_waveform)
        self.btn_disable_modes.clicked.connect(self.disable_special_modes)

    def update_frequency(self):
        if self.my_instrument:
            try:
                freq = float(self.edit_freq.text())
                unit = self.combo_freq_unit.currentText()
                self.my_instrument.set_frequency(freq, unit)
                print(f"[Live] Frequenz auf {freq} {unit} geändert.")
            except Exception as e:
                print(f"[Live] Fehler Frequenz: {e}")

    def update_amplitude(self):
        if self.my_instrument:
            try:
                amp = float(self.edit_amp.text())
                self.my_instrument.set_amplitude(amp)
                print(f"[Live] Amplitude auf {amp} Vpp geändert.")
            except Exception as e:
                print(f"[Live] Fehler Amplitude: {e}")

    def update_offset(self):
        if self.my_instrument:
            try:
                offset = float(self.edit_offset.text())
                self.my_instrument.set_offset(offset)
                print(f"[Live] Offset auf {offset} V geändert.")
            except Exception as e:
                print(f"[Live] Fehler Offset: {e}")

    def update_waveform(self, wave_type):
        if self.my_instrument:
            try:
                self.my_instrument.set_waveform(wave_type)
                print(f"[Live] Signalform auf {wave_type} geändert.")
            except Exception as e:
                print(f"[Live] Fehler Signalform: {e}")

    def disable_special_modes(self):
        if self.my_instrument and hasattr(self.my_instrument, 'instrument'):
            try:
                for ch in [1, 2]:
                    self.my_instrument.instrument.write(f"SOURce{ch}:BURSt:STATe OFF")
                    self.my_instrument.instrument.write(f"SOURce{ch}:SWEep:STATe OFF")
                    self.my_instrument.instrument.write(f"SOURce{ch}:MODUlation:STATe OFF")
                print("[Live] Burst, Sweep und Modulationen erfolgreich deaktiviert.")
            except Exception as e:
                print(f"[Live] Fehler beim Deaktivieren der Modi: {e}")
