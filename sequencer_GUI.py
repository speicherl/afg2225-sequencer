import sys
import json
import numpy as np
from PyQt6.QtWidgets import (QLineEdit, QPushButton, QApplication, QGroupBox, QFileDialog,
                             QVBoxLayout, QDialog, QLabel, QHBoxLayout, QScrollArea, QWidget, QComboBox)
import pyvisa
from PyQt6 import QtTest
from afg2225library import AFG2225

# Aus backend_qt5agg wird backend_qtagg
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure


class MplCanvas(FigureCanvas):
    """Ein eigenständiges Widget, das ein Matplotlib-Diagramm in PyQt5 einbettet."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)
        fig.tight_layout()


class Form(QDialog):
    """Das Hauptfenster der Applikation für den AFG-2225 Rampen-Sequenzer."""

    def __init__(self, parent=None):
        super(Form, self).__init__(parent)
        self.status = 'Off'  # Status des Hardware-Ausgangs (On/Off)
        self.setWindowTitle("GW-Instek AFG-2225 - Rampen-Sequenzer Pro")
        self.setMinimumWidth(950)
        self.resize(1000, 650)

        # Liste zur dynamischen Verwaltung der Signalzeilen-Widgets
        self.signal_rows = []

        main_h_layout = QHBoxLayout()  # Horizontale Teilung: Links Steuerung, Rechts Plotter
        left_v_layout = QVBoxLayout()  # Linke Spalte für Parameter

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
        seq_group = QGroupBox("Signal-Abfolge (Konstante Steigung via Cycles)")
        seq_layout = QVBoxLayout()

        # Datei-Aktionen (Speichern & Laden)
        file_btn_layout = QHBoxLayout()
        self.btn_save_seq = QPushButton("💾 Sequenz speichern")
        self.btn_save_seq.clicked.connect(self.save_sequence_to_file)
        self.btn_load_seq = QPushButton("📂 Sequenz laden")
        self.btn_load_seq.clicked.connect(self.load_sequence_from_file)
        file_btn_layout.addWidget(self.btn_save_seq)
        file_btn_layout.addWidget(self.btn_load_seq)
        seq_layout.addLayout(file_btn_layout)

        # Scroll-Bereich für die dynamischen Signalzeilen
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.addStretch()  # Drückt die Zeilen nach oben
        self.scroll.setWidget(self.scroll_content)
        seq_layout.addWidget(self.scroll)

        # Button zum Hinzufügen neuer Zeilen (per Lambda entkoppelt)
        btn_layout = QHBoxLayout()
        self.btn_add_signal = QPushButton("+ Signal hinzufügen")
        self.btn_add_signal.setStyleSheet("background-color: #5cb85c; color: white; font-weight: bold;")
        self.btn_add_signal.clicked.connect(lambda: self.add_signal_row())
        btn_layout.addWidget(self.btn_add_signal)
        seq_layout.addLayout(btn_layout)

        seq_group.setLayout(seq_layout)
        left_v_layout.addWidget(seq_group)

        # Hardware-Aktionsbuttons
        self.button_run_seq = QPushButton("Sequenz starten (Phasenrein)")
        self.button_run_seq.setStyleSheet("background-color: #2b579a; color: white; font-weight: bold; font-size: 13px; padding: 6px;")
        self.button_on = QPushButton("Ausgang Einschalten (Start)")
        left_v_layout.addWidget(self.button_run_seq)
        left_v_layout.addWidget(self.button_on)

        main_h_layout.addLayout(left_v_layout, stretch=4)

        # --- RECHTE SPALTE (INTERAKTIVER PLOTTER) ---
        plot_group = QGroupBox("Signal-Vorschau (Interaktiv)")
        plot_layout = QVBoxLayout()
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.toolbar = NavigationToolbar(self.canvas, self)  # Zoom- & Pan-Leiste
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        plot_group.setLayout(plot_layout)

        main_h_layout.addWidget(plot_group, stretch=5)
        self.setLayout(main_h_layout)

        # Standardkonfiguration beim Start (2 Dummy-Signale)
        self.add_signal_row("1.0", "4", "0.0")
        self.add_signal_row("2.0", "2", "0.0")

        self.button_run_seq.clicked.connect(self.run_sequence)
        self.button_on.clicked.connect(self.setOnOff)
        self.plot_preview()

    def add_signal_row(self, amp="1.0", cycles="5", pause="0.0"):
        """Erzeugt dynamisch eine neue Eingabezeile für ein Signalteilsegment."""
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

        # Widget vor dem vertikalen Stretch am Ende einfügen
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
        """Löscht die ausgewählte Zeile und aktualisiert die Nummerierung."""
        if len(self.signal_rows) <= 1:
            return  # Es muss immer mindestens eine Zeile übrig bleiben
        self.signal_rows.remove(row_data)
        row_data['widget'].deleteLater()
        QtTest.QTest.qWait(10)
        self.update_row_numbers()
        self.plot_preview()

    def update_row_numbers(self):
        """Korrigiert die Indizes (S1, S2, S3...) nach dem Löschen oder Hinzufügen."""
        for idx, row in enumerate(self.signal_rows):
            row['label'].setText(f"<b>S{idx + 1}:</b>")

    def save_sequence_to_file(self):
        """Sichert die aktuelle Tabellenkonfiguration als JSON-Datei."""
        try:
            data_to_save = {
                'slope': self.edit_slope.text(),
                'offset': self.edit_offset.text(),
                'signals': []
            }
            for row in self.signal_rows:
                data_to_save['signals'].append({
                    'amp': row['amp'].text(), 'cycles': row['cycles'].text(), 'pause': row['pause'].text()
                })
            filename, _ = QFileDialog.getSaveFileName(self, "Sequenz speichern", "", "JSON Files (*.json)")
            if filename:
                if not filename.endswith('.json'):
                    filename += '.json'
                with open(filename, 'w') as f:
                    json.dump(data_to_save, f, indent=4)
                print(f"Erfolgreich gespeichert: {filename}")
        except Exception as e:
            print(f"Fehler beim Speichern: {e}")

    def load_sequence_from_file(self):
        """Lädt eine JSON-Datei und baut die Tabelle dynamisch neu auf."""
        try:
            filename, _ = QFileDialog.getOpenFileName(self, "Sequenz laden", "", "JSON Files (*.json)")
            if filename:
                with open(filename, 'r') as f:
                    loaded_data = json.load(f)

                self.edit_slope.setText(loaded_data.get('slope', '0.5'))
                self.edit_offset.setText(loaded_data.get('offset', '0.0'))

                # Alte Zeilen entfernen
                for row in list(self.signal_rows):
                    self.signal_rows.remove(row)
                    row['widget'].deleteLater()

                QtTest.QTest.qWait(50)
                # Neue Zeilen befüllen
                for sig in loaded_data.get('signals', []):
                    self.add_signal_row(amp=sig['amp'], cycles=sig['cycles'], pause=sig['pause'])
                print(f"Erfolgreich geladen: {filename}")
                self.plot_preview()
        except Exception as e:
            print(f"Fehler beim Laden: {e}")

    def generate_ramp_data(self, t_start, duration, freq_hz, amp_vpp, offset):
        """Berechnet mathematisch die Kurvenpunkte für das Vorschaufenster (X-Achsen-stetig)."""
        t = np.linspace(t_start, t_start + duration, max(2, int(duration * 50000)))
        if freq_hz <= 0:
            return t, np.zeros_like(t) + offset

        # +0.25 schiebt die Startphase für ein 50% Dreieck exakt auf den Nulldurchgang (0 Volt)
        phase = ((t - t_start) * freq_hz + 0.25) % 1.0
        y = np.zeros_like(phase)
        mask1 = phase <= 0.5
        y[mask1] = phase[mask1] / 0.5
        mask2 = phase > 0.5
        y[mask2] = (1.0 - phase[mask2]) / 0.5

        y = (y - 0.5) * amp_vpp + offset
        return t, y

    def calculate_frequency(self, slope_v_ms, amp_vpp):
        """Berechnet die benötigte Frequenz: f = m / (2 * Vpp)"""
        if amp_vpp <= 0:
            return 0.0
        slope_v_s = slope_v_ms * 1000.0
        return slope_v_s / (2.0 * amp_vpp)

    def plot_preview(self):
        """Generiert den mathematischen Soll-Verlauf und aktualisiert die matplotlib-Figur."""
        try:
            self.canvas.axes.clear()
            slope_v_ms = float(self.edit_slope.text()) if self.edit_slope.text() else 0.5
            offset = float(self.edit_offset.text()) if self.edit_offset.text() else 0.0

            t_current, t_all, y_all = 0.0, np.array([]), np.array([])

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
                    y_all = np.append(y_all, np.zeros_like(t_p) + offset)
                    t_all = np.append(t_all, t_p)
                    t_current += p

            if len(t_all) > 0:
                self.canvas.axes.plot(t_all, y_all, color='#2b579a', linewidth=2)
                self.canvas.axes.set_xlabel("Zeit (Sekunden)")
                self.canvas.axes.set_ylabel("Spannung (Volt)")
                self.canvas.axes.grid(True, linestyle='--', alpha=0.6)
                self.canvas.axes.axhline(0, color='black', linewidth=0.8)

                max_val, min_val = np.max(y_all), np.min(y_all)
                span = max(max_val - min_val, 1.0)
                self.canvas.axes.set_ylim(min_val - 0.2 * span, max_val + 0.2 * span)

            self.canvas.draw()
        except ValueError:
            pass  # Verhindert Fehlermeldungen während der Nutzertypeingabe

    def run_sequence(self):
        """Validiert alle Parameter gegen Hardwareresistenz und steuert den AFG-2225 an."""
        try:
            if not self.signal_rows:
                return

            # HARDWARE-SCHUTZGRENZEN DEFINIEREN
            MAX_SLOPE, MIN_SLOPE = 10.0, 0.001
            MAX_AMP, MIN_AMP = 10.0, 0.01
            MAX_CYCLES, MIN_CYCLES = 10000, 1
            MAX_PAUSE = 60.0

            # 1. Globalen Slope validieren
            slope_v_ms = float(self.edit_slope.text()) if self.edit_slope.text() else 0.5
            if slope_v_ms > MAX_SLOPE or slope_v_ms < MIN_SLOPE:
                slope_v_ms = max(MIN_SLOPE, min(MAX_SLOPE, slope_v_ms))
                self.edit_slope.setText(str(slope_v_ms))
                self.edit_slope.setStyleSheet("background-color: #ffcccc;")
            else:
                self.edit_slope.setStyleSheet("")

            offset = float(self.edit_offset.text()) if self.edit_offset.text() else 0.0

            print("--- Starte Hardware-Sequenzlauf ---")
            my_instrument.set_waveform("ramp")
            QtTest.QTest.qWait(100)
            my_instrument.set_ramp_symmetry(50.0)
            QtTest.QTest.qWait(100)
            my_instrument.set_offset(offset)
            QtTest.QTest.qWait(100)

            # 2. Einzelzeilen abarbeiten und Hardware-Schutz anwenden
            for idx, row in enumerate(self.signal_rows):
                a = float(row['amp'].text()) if row['amp'].text() else 1.0
                c = float(row['cycles'].text()) if row['cycles'].text() else 5.0
                p = float(row['pause'].text()) if row['pause'].text() else 0.0

                if a > MAX_AMP or a < MIN_AMP:
                    a = max(MIN_AMP, min(MAX_AMP, a))
                    row['amp'].setText(str(a))
                    row['amp'].setStyleSheet("background-color: #ffcccc;")
                else:
                    row['amp'].setStyleSheet("")

                if c > MAX_CYCLES or c < MIN_CYCLES:
                    c = max(MIN_CYCLES, min(MAX_CYCLES, c))
                    row['cycles'].setText(str(int(c)))
                    row['cycles'].setStyleSheet("background-color: #ffcccc;")
                else:
                    row['cycles'].setStyleSheet("")

                if p > MAX_PAUSE or p < 0:
                    p = max(0.0, min(MAX_PAUSE, p))
                    row['pause'].setText(str(p))
                    row['pause'].setStyleSheet("background-color: #ffcccc;")
                else:
                    row['pause'].setStyleSheet("")

                # Hardware-Übermittlung
                freq_hz = self.calculate_frequency(slope_v_ms, a)
                duration_s = c / freq_hz if freq_hz > 0 else 0.0

                print(f"[{idx+1}/{len(self.signal_rows)}] Vpp={a}V | Frequenz: {freq_hz:.2f} Hz | Zeit: {duration_s:.5f}s")

                my_instrument.set_frequency(freq_hz, "Hz")
                QtTest.QTest.qWait(100)
                my_instrument.set_amplitude(a)

                QtTest.QTest.qWait(int(duration_s * 1000))

                if p > 0:
                    my_instrument.set_amplitude(0.01)  # Ausgang absenken für Pause
                    QtTest.QTest.qWait(int(p * 1000))

            print("--- Hardware-Sequenz beendet ---")
            self.plot_preview()

        except ValueError:
            print("Fehler: Ungültige Zahlenwerte erkannt!")
        except Exception as e:
            print(f"Kritischer Fehler: {e}")

    def setOnOff(self):
        """Schaltet den Kanal-Ausgang am Gerät ein oder aus."""
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
        # Initialisierung über das stabile PyVISA-Python-Backend
        my_instrument = AFG2225.AFG2225('ASRL/dev/ttyACM0::INSTR')
        sys.exit(app.exec())
    except Exception as e:
        print("Verbindung fehlgeschlagen:", e)
