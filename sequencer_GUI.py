import sys
import numpy as np
from PyQt5.QtWidgets import (QLineEdit, QPushButton, QApplication, QGroupBox,
                             QVBoxLayout, QDialog, QLabel, QHBoxLayout, QComboBox, QScrollArea, QWidget)
import pyvisa
from PyQt5 import QtTest
from afg2225library import AFG2225

# Matplotlib-Imports für die PyQt5-Einbettung
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class MplCanvas(FigureCanvas):
    """Ein Canvas-Widget für Matplotlib-Plots in PyQt5."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)
        fig.tight_layout()


class Form(QDialog):

    def __init__(self, parent=None):
        super(Form, self).__init__(parent)
        self.status = 'Off'
        self.setWindowTitle("AFG-2225 - Sequenzer & Signal-Plotter")
        self.setMinimumWidth(900)  # Breiter, damit der Plotter Platz hat
        self.resize(950, 600)

        # Liste für die Signalzeilen
        self.signal_rows = []

        # Hauptlayout: Horizontal (Links Steuerung, Rechts Plotter)
        main_h_layout = QHBoxLayout()

        # Linke Spalte (Steuerung)
        left_v_layout = QVBoxLayout()

        # --- GLOBALE RAMPEN-EINSTELLUNGEN ---
        glob_group = QGroupBox("Globale Rampen-Einstellungen")
        glob_layout = QVBoxLayout()
        glob_layout.addWidget(QLabel("Konstante Symmetrie / Steigung (0.0% bis 100.0%):"))
        self.edit_symmetry = QLineEdit("50.0")
        glob_layout.addWidget(self.edit_symmetry)
        glob_layout.addWidget(QLabel("Konstanter DC-Offset (V):"))
        self.edit_offset = QLineEdit("0.0")
        glob_layout.addWidget(self.edit_offset)
        glob_group.setLayout(glob_layout)
        left_v_layout.addWidget(glob_group)

        # --- DYNAMISCHE SEQUENZER SEKTION ---
        seq_group = QGroupBox("Signal-Abfolge (Sequenz)")
        seq_layout = QVBoxLayout()

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
        self.btn_add_signal.clicked.connect(self.add_signal_row)
        btn_layout.addWidget(self.btn_add_signal)
        seq_layout.addLayout(btn_layout)
        seq_group.setLayout(seq_layout)
        left_v_layout.addWidget(seq_group)

        # Buttons
        self.button_run_seq = QPushButton("Sequenz auf Gerät laden & starten")
        self.button_run_seq.setStyleSheet("background-color: #2b579a; color: white; font-weight: bold; font-size: 13px; padding: 6px;")
        self.button_on = QPushButton("Ausgang Einschalten (Start)")
        left_v_layout.addWidget(self.button_run_seq)
        left_v_layout.addWidget(self.button_on)

        # Linkes Layout dem Haupthorizontallayout hinzufügen
        main_h_layout.addLayout(left_v_layout, stretch=4)

        # --- RECHTE SPALTE (PLOTTER) ---
        plot_group = QGroupBox("Signal-Vorschau (Soll-Verlauf)")
        plot_layout = QVBoxLayout()
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        plot_layout.addWidget(self.canvas)
        plot_group.setLayout(plot_layout)

        main_h_layout.addWidget(plot_group, stretch=5)

        self.setLayout(main_h_layout)

        # Erste zwei Signale erzeugen
        self.add_signal_row()
        self.add_signal_row()

        # Signale verknüpfen
        self.button_run_seq.clicked.connect(self.run_sequence)
        self.button_on.clicked.connect(self.setOnOff)

        # Initialen Plot zeichnen
        self.plot_preview()

    def add_signal_row(self):
        row_widget = QWidget()
        row_h_layout = QHBoxLayout(row_widget)
        row_h_layout.setContentsMargins(0, 4, 0, 4)

        lbl = QLabel()
        edit_f = QLineEdit("1.0")
        edit_f.setFixedWidth(45)
        edit_f.textChanged.connect(self.plot_preview) # Bei Änderung Plot updaten

        combo_u = QComboBox()
        combo_u.addItems(["Hz", "kHz", "MHz"])
        combo_u.setCurrentText("kHz")
        combo_u.currentTextChanged.connect(self.plot_preview)

        edit_a = QLineEdit("2.0")
        edit_a.setFixedWidth(45)
        edit_a.textChanged.connect(self.plot_preview)

        edit_d = QLineEdit("2.0")
        edit_d.setFixedWidth(35)
        edit_d.textChanged.connect(self.plot_preview)

        edit_p = QLineEdit("0.0")
        edit_p.setFixedWidth(35)
        edit_p.textChanged.connect(self.plot_preview)

        btn_remove = QPushButton("X")
        btn_remove.setFixedWidth(25)
        btn_remove.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold;")

        row_h_layout.addWidget(lbl)
        row_h_layout.addWidget(QLabel("F:"))
        row_h_layout.addWidget(edit_f)
        row_h_layout.addWidget(combo_u)
        row_h_layout.addWidget(QLabel("A:"))
        row_h_layout.addWidget(edit_a)
        row_h_layout.addWidget(QLabel("V | D:"))
        row_h_layout.addWidget(edit_d)
        row_h_layout.addWidget(QLabel("s | P:"))
        row_h_layout.addWidget(edit_p)
        row_h_layout.addWidget(QLabel("s"))
        row_h_layout.addWidget(btn_remove)

        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, row_widget)

        row_data = {
            'widget': row_widget, 'label': lbl, 'freq': edit_f, 'unit': combo_u,
            'amp': edit_a, 'duration': edit_d, 'pause': edit_p
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

    def generate_ramp_data(self, t_start, duration, freq_hz, amp_vpp, offset, symmetry_pct):
        """Generiert die mathematischen X- und Y-Daten für eine Rampe/Dreieck."""
        t = np.linspace(t_start, t_start + duration, int(duration * 2000)) # 2000 Punkte pro Sekunde
        if freq_hz <= 0:
            return t, np.zeros_like(t) + offset

        # Periode berechnen
        T = 1.0 / freq_hz
        # Phase innerhalb der Periode (0 bis 1)
        phase = (t * freq_hz) % 1.0

        # Symmetrie-Punkt (0.0 bis 1.0)
        sym = symmetry_pct / 100.0

        # Dreieckform berechnen basierend auf Symmetrie
        y = np.zeros_like(phase)
        if sym > 0:
            mask1 = phase <= sym
            y[mask1] = phase[mask1] / sym
        if sym < 1:
            mask2 = phase > sym
            y[mask2] = (1.0 - phase[mask2]) / (1.0 - sym)

        # Von [0, 1] auf Peak-to-Peak Amplitude und Offset skalieren (Dreieck geht von -Vpp/2 bis +Vpp/2)
        y = (y - 0.5) * amp_vpp + offset
        return t, y

    def plot_preview(self):
        """Berechnet den gesamten Kurvenverlauf und zeichnet ihn live im GUI."""
        try:
            self.canvas.axes.clear()

            symmetry = float(self.edit_symmetry.text()) if self.edit_symmetry.text() else 50.0
            offset = float(self.edit_offset.text()) if self.edit_offset.text() else 0.0
            unit_dict = {'MHz': 10**6, 'kHz': 10**3, 'Hz': 1}

            t_current = 0.0
            t_all = np.array([])
            y_all = np.array([])

            # Gehe durch alle Zeilen und hänge die Kurven mathematisch aneinander
            for row in self.signal_rows:
                f = float(row['freq'].text()) if row['freq'].text() else 1.0
                u = row['unit'].currentText()
                a = float(row['amp'].text()) if row['amp'].text() else 0.0
                d = float(row['duration'].text()) if row['duration'].text() else 0.0
                p = float(row['pause'].text()) if row['pause'].text() else 0.0

                freq_hz = f * unit_dict[u]

                # 1. Signal-Phase generieren
                if d > 0:
                    t_sig, y_sig = self.generate_ramp_data(t_current, d, freq_hz, a, offset, symmetry)
                    t_all = np.append(t_all, t_sig)
                    y_all = np.append(y_all, y_sig)
                    t_current += d

                # 2. Pause-Phase generieren (Falls vorhanden, fällt das Signal auf 0V/Offset ab)
                if p > 0:
                    t_p = np.linspace(t_current, t_current + p, int(p * 500))
                    y_p = np.zeros_like(t_p) + offset
                    t_all = np.append(t_all, t_p)
                    y_all = np.append(y_all, y_p)
                    t_current += p

            # Plot zeichnen, falls Daten vorhanden sind
            if len(t_all) > 0:
                self.canvas.axes.plot(t_all, y_all, label="Soll-Signal", color='#2b579a', linewidth=2)
                self.canvas.axes.set_xlabel("Zeit (Sekunden)")
                self.canvas.axes.set_ylabel("Spannung (Volt)")
                self.canvas.axes.grid(True, linestyle='--', alpha=0.6)
                self.canvas.axes.axhline(0, color='black', linewidth=0.8, linestyle='-')

                # Dynamische Y-Grenzen setzen mit etwas Puffer
                max_val = np.max(y_all) if len(y_all) > 0 else 2.0
                min_val = np.min(y_all) if len(y_all) > 0 else -2.0
                span = max(max_val - min_val, 1.0)
                self.canvas.axes.set_ylim(min_val - 0.2 * span, max_val + 0.2 * span)

            self.canvas.draw()

        except ValueError:
            pass # Ignorieren, während der Nutzer tippt

    def run_sequence(self):
        try:
            if not self.signal_rows:
                return

            symmetry = float(self.edit_symmetry.text())
            offset = float(self.edit_offset.text())
            unit_dict = {'MHz': 10**6, 'kHz': 10**3, 'Hz': 1}

            print("--- Starte dynamische Signal-Abfolge ---")

            my_instrument.set_waveform("ramp")
            QtTest.QTest.qWait(100)
            my_instrument.set_ramp_symmetry(symmetry)
            QtTest.QTest.qWait(100)
            my_instrument.set_offset(offset)
            QtTest.QTest.qWait(100)

            for idx, row in enumerate(self.signal_rows):
                f = float(row['freq'].text())
                u = row['unit'].currentText()
                a = float(row['amp'].text())
                d = float(row['duration'].text())
                p = float(row['pause'].text())

                print(f"[{idx+1}/{len(self.signal_rows)}] Schalte am Gerät: {f} {u}, {a} Vpp")

                my_instrument.set_frequency(f, u)
                QtTest.QTest.qWait(100)
                my_instrument.set_amplitude(a)

                # Warte die Dauer des Signals ab
                QtTest.QTest.qWait(int(d * 1000))

                if p > 0:
                    print(f"   -> Pause für {p}s (0V)...")
                    my_instrument.set_amplitude(0.01)
                    QtTest.QTest.qWait(int(p * 1000))

            print("--- Sequenz erfolgreich beendet ---")

        except ValueError:
            print("Fehler: Bitte überprüfe alle Zahlenwerte!")
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
