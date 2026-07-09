import sys
import json
import numpy as np
from PyQt5.QtWidgets import (QLineEdit, QPushButton, QApplication, QGroupBox, QFileDialog,
                             QVBoxLayout, QDialog, QLabel, QHBoxLayout, QScrollArea, QWidget)
import pyvisa
from PyQt5 import QtTest
from afg2225library import AFG2225

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)
        fig.tight_layout()


class Form(QDialog):

    def __init__(self, parent=None):
        super(Form, self).__init__(parent)
        self.status = 'Off'
        self.setWindowTitle("AFG-2225 - Sequenzer mit Speicherfunktion")
        self.setMinimumWidth(950)
        self.resize(1000, 650)

        self.signal_rows = []

        main_h_layout = QHBoxLayout()
        left_v_layout = QVBoxLayout()

        # --- GLOBALE RAMPEN-EINSTELLUNGEN ---
        glob_group = QGroupBox("Globale Rampen-Einstellungen")
        glob_layout = QVBoxLayout()
        glob_layout.addWidget(QLabel("<b>Gewünschte Steigung (Volt pro Millisekunde, V/ms):</b>"))
        self.edit_slope = QLineEdit("0.5")
        self.edit_slope.textChanged.connect(self.plot_preview)
        glob_layout.addWidget(self.edit_slope)
        glob_layout.addWidget(QLabel("Konstanter DC-Offset (V):"))
        self.edit_offset = QLineEdit("0.0")
        self.edit_offset.textChanged.connect(self.plot_preview)
        glob_layout.addWidget(self.edit_offset)
        glob_group.setLayout(glob_layout)
        left_v_layout.addWidget(glob_group)

        # --- DYNAMISCHE SEQUENZER SEKTION ---
        seq_group = QGroupBox("Signal-Abfolge (Konstante Steigung)")
        seq_layout = QVBoxLayout()

        # NEU: Datei-Aktionen (Speichern / Laden) ganz oben in der Sektion
        file_btn_layout = QHBoxLayout()
        self.btn_save_seq = QPushButton("💾 Sequenz speichern")
        self.btn_save_seq.clicked.connect(self.save_sequence_to_file)
        self.btn_load_seq = QPushButton("📂 Sequenz laden")
        self.btn_load_seq.clicked.connect(self.load_sequence_from_file)
        file_btn_layout.addWidget(self.btn_save_seq)
        file_btn_layout.addWidget(self.btn_load_seq)
        seq_layout.addLayout(file_btn_layout)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.addStretch()
        self.scroll.setWidget(self.scroll_content)
        seq_layout.addWidget(self.scroll)

        btn_layout = QHBoxLayout()
        self.btn_add_signal = QPushButton("+ Signal hinzufügen")
        self.btn_add_signal.setStyleSheet("background-color: #5cb85c; color: white; font-weight: bold;")
        self.btn_add_signal.clicked.connect(lambda: self.add_signal_row())
        btn_layout.addWidget(self.btn_add_signal)
        seq_layout.addLayout(btn_layout)
        seq_group.setLayout(seq_layout)
        left_v_layout.addWidget(seq_group)

        # Buttons
        self.button_run_seq = QPushButton("Sequenz mit konstanter Steigung starten")
        self.button_run_seq.setStyleSheet("background-color: #2b579a; color: white; font-weight: bold; font-size: 13px; padding: 6px;")
        self.button_on = QPushButton("Ausgang Einschalten (Start)")
        left_v_layout.addWidget(self.button_run_seq)
        left_v_layout.addWidget(self.button_on)

        main_h_layout.addLayout(left_v_layout, stretch=4)

        # --- PLOTTER ---
        plot_group = QGroupBox("Signal-Vorschau (Interaktiv)")
        plot_layout = QVBoxLayout()
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.toolbar = NavigationToolbar(self.canvas, self)
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        plot_group.setLayout(plot_layout)

        main_h_layout.addWidget(plot_group, stretch=5)
        self.setLayout(main_h_layout)

        # Startkonfiguration mit 2 Signalen
        self.add_signal_row()
        self.add_signal_row()
        if len(self.signal_rows) > 1:
            self.signal_rows[0]['amp'].setText("1.0")
            self.signal_rows[0]['cycles'].setText("4")
            self.signal_rows[1]['amp'].setText("2.0")
            self.signal_rows[1]['cycles'].setText("2")

        self.button_run_seq.clicked.connect(self.run_sequence)
        self.button_on.clicked.connect(self.setOnOff)

        self.plot_preview()

    def add_signal_row(self, amp="1.0", cycles="5", pause="0.0"):
        """Fügt eine Zeile hinzu (jetzt mit optionalen Startwerten fürs Laden)."""
        row_widget = QWidget()
        row_h_layout = QHBoxLayout(row_widget)
        row_h_layout.setContentsMargins(0, 4, 0, 4)

        lbl = QLabel()
        edit_a = QLineEdit(amp)
        edit_a.setFixedWidth(60)
        edit_a.textChanged.connect(self.plot_preview)

        edit_c = QLineEdit(cycles)
        edit_c.setFixedWidth(50)
        edit_c.textChanged.connect(self.plot_preview)

        edit_p = QLineEdit(pause)
        edit_p.setFixedWidth(50)
        edit_p.textChanged.connect(self.plot_preview)

        btn_remove = QPushButton("X")
        btn_remove.setFixedWidth(30)
        btn_remove.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold;")

        row_h_layout.addWidget(lbl)
        row_h_layout.addWidget(QLabel("Amplitude:"))
        row_h_layout.addWidget(edit_a)
        row_h_layout.addWidget(QLabel("Vpp | Cycles:"))
        row_h_layout.addWidget(edit_c)
        row_h_layout.addWidget(QLabel(" | Pause danach:"))
        row_h_layout.addWidget(edit_p)
        row_h_layout.addWidget(QLabel("s"))
        row_h_layout.addWidget(btn_remove)

        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, row_widget)

        row_data = {
            'widget': row_widget, 'label': lbl,
            'amp': edit_a, 'cycles': edit_c, 'pause': edit_p
        }
        self.signal_rows.append(row_data)
        btn_remove.clicked.connect(lambda: self.remove_signal_row(row_data))

        self.update_row_numbers()
        self.plot_preview()

    def remove_signal_row(self, row_data):
        if len(self.signal_rows) <= 1:
            return
        self.signal_rows.remove(row_data)
        row_data['widget'].deleteLater()
        QtTest.QTest.qWait(10)
        self.update_row_numbers()
        self.plot_preview()

    def update_row_numbers(self):
        for idx, row in enumerate(self.signal_rows):
            row['label'].setText(f"<b>S{idx + 1}:</b>")

    # --- NEU: SPEICHER-METHODE ---
    def save_sequence_to_file(self):
        try:
            # Bereite Datenstruktur zum Speichern vor
            data_to_save = {
                'slope': self.edit_slope.text(),
                'offset': self.edit_offset.text(),
                'signals': []
            }

            for row in self.signal_rows:
                data_to_save['signals'].append({
                    'amp': row['amp'].text(),
                    'cycles': row['cycles'].text(),
                    'pause': row['pause'].text()
                })

            # Öffne den Dateidialog zum Speichern
            filename, _ = QFileDialog.getSaveFileName(self, "Sequenz speichern", "", "JSON Files (*.json)")
            if filename:
                # Falls die Endung fehlt, hänge sie an
                if not filename.endswith('.json'):
                    filename += '.json'
                with open(filename, 'w') as f:
                    json.dump(data_to_save, f, indent=4)
                print(f"Sequenz erfolgreich unter '{filename}' gespeichert.")
        except Exception as e:
            print(f"Fehler beim Speichern der Datei: {e}")

    # --- NEU: LADE-METHODE ---
    def load_sequence_from_file(self):
        try:
            filename, _ = QFileDialog.getOpenFileName(self, "Sequenz laden", "", "JSON Files (*.json)")
            if filename:
                with open(filename, 'r') as f:
                    loaded_data = json.load(f)

                # Globale Werte setzen
                self.edit_slope.setText(loaded_data.get('slope', '0.5'))
                self.edit_offset.setText(loaded_data.get('offset', '0.0'))

                # Alle alten Zeilen rigoros weglöschen
                for row in list(self.signal_rows):
                    self.signal_rows.remove(row)
                    row['widget'].deleteLater()

                # Kurz warten, damit Qt das Layout bereinigen kann
                QtTest.QTest.qWait(50)

                # Geladene Signalzeilen neu aufbauen
                for sig in loaded_data.get('signals', []):
                    self.add_signal_row(amp=sig['amp'], cycles=sig['cycles'], pause=sig['pause'])

                print(f"Sequenz aus '{filename}' erfolgreich geladen!")
                self.plot_preview()
        except Exception as e:
            print(f"Fehler beim Laden der Datei (Evtl. beschädigtes Format): {e}")

    def generate_ramp_data(self, t_start, duration, freq_hz, amp_vpp, offset):
        t = np.linspace(t_start, t_start + duration, max(2, int(duration * 50000)))
        if freq_hz <= 0:
            return t, np.zeros_like(t) + offset

        phase = ((t - t_start) * freq_hz + 0.25) % 1.0
        y = np.zeros_like(phase)
        mask1 = phase <= 0.5
        y[mask1] = phase[mask1] / 0.5
        mask2 = phase > 0.5
        y[mask2] = (1.0 - phase[mask2]) / 0.5

        y = (y - 0.5) * amp_vpp + offset
        return t, y

    def calculate_frequency(self, slope_v_ms, amp_vpp):
        if amp_vpp <= 0:
            return 0.0
        slope_v_s = slope_v_ms * 1000.0
        return slope_v_s / (2.0 * amp_vpp)

    def plot_preview(self):
        try:
            self.canvas.axes.clear()

            slope_v_ms = float(self.edit_slope.text()) if self.edit_slope.text() else 0.5
            offset = float(self.edit_offset.text()) if self.edit_offset.text() else 0.0

            t_current = 0.0
            t_all = np.array([])
            y_all = np.array([])

            for row in self.signal_rows:
                a = float(row['amp'].text()) if row['amp'].text() else 0.0
                c = float(row['cycles'].text()) if row['cycles'].text() else 0.0
                p = float(row['pause'].text()) if row['pause'].text() else 0.0

                freq_hz = self.calculate_frequency(slope_v_ms, a)
                d = c / freq_hz if freq_hz > 0 else 0.0

                if d > 0:
                    t_sig, y_sig = self.generate_ramp_data(t_current, d, freq_hz, a, offset)
                    t_all = np.append(t_all, t_sig)
                    y_all = np.append(y_all, y_sig)
                    t_current += d

                if p > 0:
                    t_p = np.linspace(t_current, t_current + p, int(p * 1000))
                    y_p = np.zeros_like(t_p) + offset
                    t_all = np.append(t_all, t_p)
                    y_all = np.append(y_all, y_p)
                    t_current += p

            if len(t_all) > 0:
                self.canvas.axes.plot(t_all, y_all, label="Soll-Signal", color='#2b579a', linewidth=2)
                self.canvas.axes.set_xlabel("Zeit (Sekunden)")
                self.canvas.axes.set_ylabel("Spannung (Volt)")
                self.canvas.axes.grid(True, linestyle='--', alpha=0.6)
                self.canvas.axes.axhline(0, color='black', linewidth=0.8, linestyle='-')

                max_val = np.max(y_all) if len(y_all) > 0 else 2.0
                min_val = np.min(y_all) if len(y_all) > 0 else -2.0
                span = max(max_val - min_val, 1.0)
                self.canvas.axes.set_ylim(min_val - 0.2 * span, max_val + 0.2 * span)

            self.canvas.draw()

        except ValueError:
            pass

    def run_sequence(self):
        try:
            if not self.signal_rows:
                return

            # ====================================================
            # 🛡️ DEINE MAXIMAL- UND MINIMALWERTE (HIER ANPASSEN)
            # ====================================================
            MAX_SLOPE = 10.0    # Maximal 10 V/ms
            MIN_SLOPE = 0.001   # Minimal 0.001 V/ms
            MAX_AMP = 10.0      # Maximal 10 Vpp (Schutz für deine Schaltung)
            MIN_AMP = 0.01      # Minimal 10 mVpp
            MAX_CYCLES = 10000  # Maximal 10.000 Perioden am Stück
            MIN_CYCLES = 1
            MAX_PAUSE = 60.0    # Maximal 60 Sekunden Pause
            # ====================================================

            # 1. Globale Werte auslesen und validieren
            slope_v_ms = float(self.edit_slope.text()) if self.edit_slope.text() else 0.5
            if slope_v_ms > MAX_SLOPE:
                slope_v_ms = MAX_SLOPE
                self.edit_slope.setText(str(MAX_SLOPE))
                self.edit_slope.setStyleSheet("background-color: #ffcccc;") # Visuelle Warnung (Rot)
            elif slope_v_ms < MIN_SLOPE:
                slope_v_ms = MIN_SLOPE
                self.edit_slope.setText(str(MIN_SLOPE))
                self.edit_slope.setStyleSheet("background-color: #ffcccc;")
            else:
                self.edit_slope.setStyleSheet("") # Normaler Hintergrund

            offset = float(self.edit_offset.text()) if self.edit_offset.text() else 0.0

            print("--- Starte validierte Signal-Abfolge ---")

            # Grundsetup auf dem Gerät hardwareseitig vorbereiten
            my_instrument.set_waveform("ramp")
            QtTest.QTest.qWait(100)
            my_instrument.set_ramp_symmetry(50.0)
            QtTest.QTest.qWait(100)
            my_instrument.set_offset(offset)
            QtTest.QTest.qWait(100)

            # 2. Schleife über alle Zeilen mit Einzelwert-Abfang
            for idx, row in enumerate(self.signal_rows):
                a = float(row['amp'].text()) if row['amp'].text() else 1.0
                c = float(row['cycles'].text()) if row['cycles'].text() else 5.0
                p = float(row['pause'].text()) if row['pause'].text() else 0.0

                # Amplituden-Schutz
                if a > MAX_AMP:
                    a = MAX_AMP
                    row['amp'].setText(str(MAX_AMP))
                    row['amp'].setStyleSheet("background-color: #ffcccc;")
                elif a < MIN_AMP:
                    a = MIN_AMP
                    row['amp'].setText(str(MIN_AMP))
                    row['amp'].setStyleSheet("background-color: #ffcccc;")
                else:
                    row['amp'].setStyleSheet("")

                # Cycles-Schutz
                if c > MAX_CYCLES:
                    c = MAX_CYCLES
                    row['cycles'].setText(str(MAX_CYCLES))
                    row['cycles'].setStyleSheet("background-color: #ffcccc;")
                elif c < MIN_CYCLES:
                    c = MIN_CYCLES
                    row['cycles'].setText(str(MIN_CYCLES))
                    row['cycles'].setStyleSheet("background-color: #ffcccc;")
                else:
                    row['cycles'].setStyleSheet("")

                # Pausen-Schutz
                if p > MAX_PAUSE:
                    p = MAX_PAUSE
                    row['pause'].setText(str(MAX_PAUSE))
                    row['pause'].setStyleSheet("background-color: #ffcccc;")
                elif p < 0:
                    p = 0.0
                    row['pause'].setText("0.0")
                    row['pause'].setStyleSheet("background-color: #ffcccc;")
                else:
                    row['pause'].setStyleSheet("")

                # Frequenz berechnen
                freq_hz = self.calculate_frequency(slope_v_ms, a)
                duration_s = c / freq_hz if freq_hz > 0 else 0.0

                print(f"[{idx+1}/{len(self.signal_rows)}] Vpp={a}V | Frequenz: {freq_hz:.2f} Hz | Laufzeit: {duration_s:.5f}s")

                # Werte an die Library übergeben
                my_instrument.set_frequency(freq_hz, "Hz")
                QtTest.QTest.qWait(100)
                my_instrument.set_amplitude(a)

                QtTest.QTest.qWait(int(duration_s * 1000))

                if p > 0:
                    print(f"   -> Pause für {p}s...")
                    my_instrument.set_amplitude(0.01)
                    QtTest.QTest.qWait(int(p * 1000))

            print("--- Sequenz erfolgreich beendet ---")
            self.plot_preview() # Aktualisiert auch die Grafik mit den korrigierten Werten

        except ValueError:
            print("Fehler: Bitte überprüfe die Zahlenwerte!")
        except Exception as e:
            print(f"Fehler: {e}")

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
