import sys
import json
import platform
import numpy as np
from PyQt6.QtWidgets import (QLineEdit, QPushButton, QApplication, QGroupBox, QFileDialog,
                             QVBoxLayout, QDialog, QLabel, QHBoxLayout, QScrollArea, QWidget, QComboBox)
import pyvisa
from PyQt6 import QtTest
from afg2225library import AFG2225
from live_control import LiveControlDialog

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
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
        self.my_instrument = None  # Wird erst nach Klick auf "Verbinden" initialisiert
        
        # PyVISA Resource Manager starten (erzwingt plattformübergreifend das stabile Python-Backend)
        try:
            self.rm = pyvisa.ResourceManager('@py')
        except Exception as e:
            self.rm = pyvisa.ResourceManager()

        self.setWindowTitle("GW-Instek AFG-2225 - Sequenzer Pro (Auto-Connect)")
        self.setMinimumWidth(950)
        self.resize(1000, 680)
        
        self.signal_rows = []
        
        main_h_layout = QHBoxLayout()
        left_v_layout = QVBoxLayout()
        
        # ==========================================
        # 1. ERSTELLUNG ALLER WIDGETS & BUTTONS
        # ==========================================
        
        # --- Hardware-Verbindung ---
        conn_group = QGroupBox("🔌 Hardware-Verbindung")
        conn_layout = QHBoxLayout()
        
        self.combo_ports = QComboBox()
        self.btn_refresh = QPushButton("🔄 Aktualisieren")
        self.btn_connect = QPushButton("⚡ Verbinden")
        self.btn_connect.setStyleSheet("background-color: #5bc85c; color: white; font-weight: bold;")
        
        conn_layout.addWidget(QLabel("Port:"))
        conn_layout.addWidget(self.combo_ports, stretch=2)
        conn_layout.addWidget(self.btn_refresh)
        conn_layout.addWidget(self.btn_connect)
        conn_group.setLayout(conn_layout)
        
        # --- Globale Buttons (Live, Run, On/Off) ---
        self.btn_open_live = QPushButton("🎛️ Live-Direktansteuerung öffnen")
        self.btn_open_live.setStyleSheet("background-color: #e3a21a; color: white; font-weight: bold; padding: 5px;")
        self.btn_open_live.setEnabled(False)  # Erst aktiv, wenn verbunden!
        
        self.button_run_seq = QPushButton("Sequenz mit konstanter Steigung starten")
        self.button_run_seq.setStyleSheet("background-color: #2b579a; color: white; font-weight: bold; font-size: 13px; padding: 6px;")
        self.button_run_seq.setEnabled(False)  # Deaktiviert, bis Verbindung steht
        
        self.button_on = QPushButton("Ausgang Einschalten (Start)")
        self.button_on.setEnabled(False)  # Deaktiviert, bis Verbindung steht
        
        # ==========================================
        # 2. POSITIONIERUNG IM LINKEN LAYOUT
        # ==========================================
        
        # Erst die Verbindung, dann die globalen Kontroll-Buttons
        left_v_layout.addWidget(conn_group)
        left_v_layout.addWidget(self.btn_open_live)
        left_v_layout.addWidget(self.button_run_seq)
        left_v_layout.addWidget(self.button_on)
        
        # --- GLOBALE RAMPEN-EINSTELLUNGEN ---
        glob_group = QGroupBox("Globale Rampen-Einstellungen")
        glob_layout = QVBoxLayout()
        glob_layout.addWidget(QLabel("<b>Gewünschte Steigung (Volt pro Millisekunde, V/ms):</b>"))
        self.edit_slope = QLineEdit("0.5")
        glob_layout.addWidget(self.edit_slope)
        glob_layout.addWidget(QLabel("Konstanter DC-Offset (V):"))
        self.edit_offset = QLineEdit("0.0")
        glob_layout.addWidget(self.edit_offset)
        glob_group.setLayout(glob_layout)
        left_v_layout.addWidget(glob_group)
        
        # --- DYNAMISCHE SEQUENZER SEKTION ---
        seq_group = QGroupBox("Signal-Abfolge (Konstante Steigung)")
        seq_layout = QVBoxLayout()
        
        file_btn_layout = QHBoxLayout()
        self.btn_save_seq = QPushButton("💾 Sequenz speichern")
        self.btn_load_seq = QPushButton("📂 Sequenz laden")
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
        btn_layout.addWidget(self.btn_add_signal)
        seq_layout.addLayout(btn_layout)
        seq_group.setLayout(seq_layout)
        
        left_v_layout.addWidget(seq_group)
        
        main_h_layout.addLayout(left_v_layout, stretch=4)
        
        # --- PLOTTER (RECHTES LAYOUT) ---
        plot_group = QGroupBox("Signal-Vorschau (Interaktiv)")
        plot_layout = QVBoxLayout()
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.toolbar = NavigationToolbar(self.canvas, self)
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        plot_group.setLayout(plot_layout)
        
        main_h_layout.addWidget(plot_group, stretch=5)
        self.setLayout(main_h_layout)
        
        # ==========================================
        # 3. SIGNAL-SLOT CONNECTIONS (EVENTS)
        # ==========================================
        self.btn_refresh.clicked.connect(self.refresh_ports)
        self.btn_connect.clicked.connect(self.toggle_connection)
        self.btn_open_live.clicked.connect(self.open_live_control)
        
        self.edit_slope.textChanged.connect(self.plot_preview)
        self.edit_offset.textChanged.connect(self.plot_preview)
        
        self.btn_save_seq.clicked.connect(self.save_sequence_to_file)
        self.btn_load_seq.clicked.connect(self.load_sequence_from_file)
        self.btn_add_signal.clicked.connect(lambda: self.add_signal_row())
        
        self.button_run_seq.clicked.connect(self.run_sequence)
        self.button_on.clicked.connect(self.setOnOff)
        
        # ==========================================
        # 4. INITIALISIERUNG BEIM START
        # ==========================================
        self.add_signal_row("1.0", "4", "0.0")
        self.add_signal_row("2.0", "2", "0.0")
        
        self.refresh_ports()
        self.plot_preview()

    def refresh_ports(self):
        """Scannt das System nach verfügbaren VISA-Geräten und befüllt das Dropdown."""
        self.combo_ports.clear()
        try:
            resources = self.rm.list_resources()
            for r in resources:
                # Bereinigung der Anzeige für den Nutzer
                display_name = r
                if "ASRL/dev/" in r:
                    # Linux-Darstellung verschönern: ASRL/dev/ttyACM0::INSTR -> /dev/ttyACM0
                    display_name = r.replace("ASRL", "").replace("::INSTR", "")
                elif "ASRL" in r and "::INSTR" in r:
                    # Windows-Darstellung verschönern: ASRL10::INSTR -> COM10
                    port_num = r.replace("ASRL", "").replace("::INSTR", "")
                    display_name = f"COM{port_num}"
                
                self.combo_ports.addItem(display_name, r) # Anzeigename, echter VISA-String
                
            if self.combo_ports.count() == 0:
                self.combo_ports.addItem("Keine Geräte gefunden")
                self.btn_connect.setEnabled(False)
            else:
                self.btn_connect.setEnabled(True)
        except Exception as e:
            self.combo_ports.addItem(f"Fehler beim Scannen: {e}")
            self.btn_connect.setEnabled(False)

    def toggle_connection(self):
        """Stellt die Verbindung her oder trennt sie wieder."""
        if self.my_instrument is None:
            visa_resource = self.combo_ports.currentData()
            if not visa_resource:
                return
            try:
                print(f"Verbinde mit: {visa_resource}")
                
                # 1. Objekt erstellen
                instance = AFG2225.AFG2225(visa_resource, resource_manager=self.rm)
                
                # 2. PRÜFUNG: Hat die Library intern überhaupt ein Instrument öffnen können?
                if not hasattr(instance, 'instrument') or instance.instrument is None:
                    # Wenn nicht, werfen wir absichtlich einen Fehler, damit wir im except-Block landen
                    raise RuntimeError("Schnittstelle konnte nicht geöffnet werden (Kein Gerät antwortet).")
                
                # Erst wenn der Test bestanden ist, weisen wir es endgültig zu
                self.my_instrument = instance
                
                # GUI auf "Verbunden" umstellen
                self.btn_connect.setText("🛑 Trennen")
                self.btn_connect.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold;")
                self.combo_ports.setEnabled(False)
                self.btn_refresh.setEnabled(False)
                self.button_run_seq.setEnabled(True)
                self.button_on.setEnabled(True)
                self.btn_open_live.setEnabled(True)
                print("⚡ Verbindung erfolgreich hergestellt!")
                
            except Exception as e:
                print(f"❌ Verbindungsfehler abgefangen: {e}")
                self.my_instrument = None
                # Dem Nutzer kurzes Feedback in der GUI geben (optional)
                self.btn_connect.setText("⚡ Verbinden fehlgeschlagen")
                QtTest.QTest.qWait(1500)
                self.btn_connect.setText("⚡ Verbinden")

        else:
            # Trennen
            self.my_instrument = None
            self.btn_connect.setText("⚡ Verbinden")
            self.btn_connect.setStyleSheet("background-color: #5cb85c; color: white; font-weight: bold;")
            self.combo_ports.setEnabled(True)
            self.btn_refresh.setEnabled(True)
            self.button_run_seq.setEnabled(False)
            self.button_on.setEnabled(False)
            self.btn_open_live.setEnabled(False)
            print("Verbindung getrennt.")

    def add_signal_row(self, amp="1.0", cycles="5", pause="0.0"):
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

    def save_sequence_to_file(self):
        try:
            data_to_save = {
                'slope': self.edit_slope.text(), 'offset': self.edit_offset.text(), 'signals': []
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
        except Exception as e:
            print(f"Fehler beim Speichern: {e}")

    def load_sequence_from_file(self):
        try:
            filename, _ = QFileDialog.getOpenFileName(self, "Sequenz laden", "", "JSON Files (*.json)")
            if filename:
                with open(filename, 'r') as f:
                    loaded_data = json.load(f)
                self.edit_slope.setText(loaded_data.get('slope', '0.5'))
                self.edit_offset.setText(loaded_data.get('offset', '0.0'))
                for row in list(self.signal_rows):
                    self.signal_rows.remove(row)
                    row['widget'].deleteLater()
                QtTest.QTest.qWait(50)
                for sig in loaded_data.get('signals', []):
                    self.add_signal_row(amp=sig['amp'], cycles=sig['cycles'], pause=sig['pause'])
                self.plot_preview()
        except Exception as e:
            print(f"Fehler beim Laden: {e}")

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
            pass

    def run_sequence(self):
        if not self.my_instrument:
            return
        try:
            if not self.signal_rows:
                return

            MAX_SLOPE, MIN_SLOPE = 10.0, 0.001
            MAX_AMP, MIN_AMP = 10.0, 0.01
            MAX_CYCLES, MIN_CYCLES = 10000, 1
            MAX_PAUSE = 60.0

            slope_v_ms = float(self.edit_slope.text()) if self.edit_slope.text() else 0.5
            if slope_v_ms > MAX_SLOPE or slope_v_ms < MIN_SLOPE:
                slope_v_ms = max(MIN_SLOPE, min(MAX_SLOPE, slope_v_ms))
                self.edit_slope.setText(str(slope_v_ms))
                self.edit_slope.setStyleSheet("background-color: #ffcccc;")
            else:
                self.edit_slope.setStyleSheet("")

            offset = float(self.edit_offset.text()) if self.edit_offset.text() else 0.0
                        
            print("--- Starte Hardware-Sequenzlauf ---")
            self.my_instrument.set_waveform("ramp")
            QtTest.QTest.qWait(100)
            self.my_instrument.set_ramp_symmetry(50.0)
            QtTest.QTest.qWait(100)
            self.my_instrument.set_offset(offset)
            QtTest.QTest.qWait(100)
            
            # WICHTIG: Hier oben KEIN vorzeitiges turn_on() mehr!
            
            for idx, row in enumerate(self.signal_rows):
                a = float(row['amp'].text()) if row['amp'].text() else 1.0
                c = float(row['cycles'].text()) if row['cycles'].text() else 5.0
                p = float(row['pause'].text()) if row['pause'].text() else 0.0
                
                # (Deine Amplituden-/Cycles-Validierung...)
                if a > MAX_AMP or a < MIN_AMP: a = max(MIN_AMP, min(MAX_AMP, a)); row['amp'].setText(str(a))
                if c > MAX_CYCLES or c < MIN_CYCLES: c = max(MIN_CYCLES, min(MAX_CYCLES, c)); row['cycles'].setText(str(int(c)))
                if p > MAX_PAUSE or p < 0: p = max(0.0, min(MAX_PAUSE, p)); row['pause'].setText(str(p))

                freq_hz = self.calculate_frequency(slope_v_ms, a)
                duration_s = c / freq_hz if freq_hz > 0 else 0.0
                
                # === 1. EINSTELLUNGEN IM HINTERGRUND MACHEN (Ausgang ist noch AUS oder vom vorherigen Schritt im Pause-Zustand) ===
                print(f"[{idx+1}/{len(self.signal_rows)}] Konfiguriere Parameter im Hintergrund...")
                self.my_instrument.set_frequency(freq_hz, "Hz")
                QtTest.QTest.qWait(100)
                self.my_instrument.set_amplitude(a)
                QtTest.QTest.qWait(100) # Dem Generator Zeit geben, die Relais intern zu schalten
                
                # === 2. ERST JETZT DEN AUSGANG EINSCHALTEN ===
                print(f"[{idx+1}/{len(self.signal_rows)}] Parameter stabil. Schalte Ausgang AN...")
                self.my_instrument.turn_on()
                self.status = 'On'
                self.button_on.setText('Ausgang Ausschalten (Stop)')
                QtTest.QTest.qWait(50)
                
                print(f"[{idx+1}/{len(self.signal_rows)}] Signal läuft: Vpp={a}V | Frequenz: {freq_hz:.2f} Hz")
                
                # Signaldauer abwarten
                QtTest.QTest.qWait(int(duration_s * 1000))
                
                # --- PAUSEN-LOGIK: AUSGANG AUSSCHALTEN ---
                if p > 0:
                    print(f"[{idx+1}/{len(self.signal_rows)}] Pause aktiv: Schalte Ausgang für {p}s AUS...")
                    self.my_instrument.turn_off()
                    QtTest.QTest.qWait(int(p * 1000))
            
            # --- AM ENDE DER SEQUENZ: AUSGANG FINAL AUSSCHALTEN ---
            print("--- Sequenz beendet: Schalte Ausgang final AUS ---")
            self.my_instrument.turn_off()
            self.status = 'Off'
            self.button_on.setText('Ausgang Einschalten (Start)')
            
            self.plot_preview()
            
        except ValueError:
            print("Fehler: Ungültige Zahlenwerte!")
        except Exception as e:
            print(f"Fehler: {e}")

    def setOnOff(self):
        if not self.my_instrument:
            return
        try:
            if self.status == 'Off':
                self.my_instrument.turn_on()
                self.button_on.setText('Ausgang Ausschalten (Stop)')
                self.status = 'On'
            else:
                self.my_instrument.turn_off()
                self.button_on.setText('Ausgang Einschalten (Start)')
                self.status = 'Off'
        except Exception as e:
            print(f"Fehler am Ausgang: {e}")

    def open_live_control(self):
        """Öffnet das ausgelagerte Live-Steuerungsfenster unblockiert."""
        if self.my_instrument:
            # Erstellt das Fenster aus der importierten Klasse
            self.live_dialog = LiveControlDialog(self.my_instrument, self)
            self.live_dialog.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    form = Form()
    form.show()
    sys.exit(app.exec())
