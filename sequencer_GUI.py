import sys
from PyQt5.QtWidgets import (QLineEdit, QPushButton, QApplication, QGroupBox,
                             QVBoxLayout, QDialog, QLabel, QHBoxLayout, QComboBox, QScrollArea, QWidget)
import pyvisa
from PyQt5 import QtTest
from afg2225library import AFG2225


class Form(QDialog):

    def __init__(self, parent=None):
        super(Form, self).__init__(parent)
        self.status = 'Off'
        self.setWindowTitle("AFG-2225 - Dynamische Sequenzer-Steuerung")
        self.setMinimumWidth(600)
        self.resize(600, 550)

        # Liste, die die Dictionaries der einzelnen Signalzeilen speichert
        self.signal_rows = []

        main_layout = QVBoxLayout()

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
        main_layout.addWidget(glob_group)

        # --- DYNAMISCHE SEQUENZER SEKTION ---
        seq_group = QGroupBox("Signal-Abfolge (Sequenz)")
        seq_layout = QVBoxLayout()

        # ScrollArea für unendlich viele Signale
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.addStretch() # Hält alles kompakt oben
        self.scroll.setWidget(self.scroll_content)
        seq_layout.addWidget(self.scroll)

        # Button zum Hinzufügen
        btn_layout = QHBoxLayout()
        self.btn_add_signal = QPushButton("+ Signal hinzufügen")
        self.btn_add_signal.setStyleSheet("background-color: #5cb85c; color: white; font-weight: bold;")
        self.btn_add_signal.clicked.connect(self.add_signal_row)
        btn_layout.addWidget(self.btn_add_signal)

        seq_layout.addLayout(btn_layout)
        seq_group.setLayout(seq_layout)
        main_layout.addWidget(seq_group)

        # --- ACTION BUTTONS ---
        self.button_run_seq = QPushButton("Sequenz starten")
        self.button_run_seq.setStyleSheet("background-color: #2b579a; color: white; font-weight: bold; font-size: 14px; padding: 8px;")
        self.button_on = QPushButton("Ausgang Einschalten (Start)")

        main_layout.addWidget(self.button_run_seq)
        main_layout.addWidget(self.button_on)

        self.setLayout(main_layout)

        # Erste zwei Signale direkt erzeugen
        self.add_signal_row()
        self.add_signal_row()

        # Signale verknüpfen
        self.button_run_seq.clicked.connect(self.run_sequence)
        self.button_on.clicked.connect(self.setOnOff)

    def add_signal_row(self):
        """Fügt der UI dynamisch eine neue Zeile für ein Signal hinzu."""
        row_widget = QWidget()
        row_h_layout = QHBoxLayout(row_widget)
        row_h_layout.setContentsMargins(0, 4, 0, 4)

        # Label für die Nummerierung
        lbl = QLabel()

        edit_f = QLineEdit("1.0")
        edit_f.setFixedWidth(50)

        combo_u = QComboBox()
        combo_u.addItems(["Hz", "kHz", "MHz"])
        combo_u.setCurrentText("kHz")

        edit_a = QLineEdit("2.0")
        edit_a.setFixedWidth(50)

        edit_d = QLineEdit("2.0")
        edit_d.setFixedWidth(40)

        edit_p = QLineEdit("0.0")
        edit_p.setFixedWidth(40)

        # Roter Entfernen-Button (X)
        btn_remove = QPushButton("X")
        btn_remove.setFixedWidth(30)
        btn_remove.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold;")

        # Widgets im horizontalen Layout anordnen
        row_h_layout.addWidget(lbl)
        row_h_layout.addWidget(QLabel("F:"))
        row_h_layout.addWidget(edit_f)
        row_h_layout.addWidget(combo_u)
        row_h_layout.addWidget(QLabel("A:"))
        row_h_layout.addWidget(edit_a)
        row_h_layout.addWidget(QLabel("V | Dauer:"))
        row_h_layout.addWidget(edit_d)
        row_h_layout.addWidget(QLabel("s | Pause danach:"))
        row_h_layout.addWidget(edit_p)
        row_h_layout.addWidget(QLabel("s"))
        row_h_layout.addWidget(btn_remove)

        # Vor dem Stretch-Element (letztes Element im Scroll-Layout) einfügen
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, row_widget)

        # Zeilen-Daten als Dictionary speichern
        row_data = {
            'widget': row_widget,
            'label': lbl,
            'freq': edit_f,
            'unit': combo_u,
            'amp': edit_a,
            'duration': edit_d,
            'pause': edit_p
        }
        self.signal_rows.append(row_data)

        # Klick auf das "X" verknüpfen (übergibt die Zeilendaten an die Löschfunktion)
        btn_remove.clicked.connect(lambda: self.remove_signal_row(row_data))

        # Nummern aktualisieren
        self.update_row_numbers()

    def remove_signal_row(self, row_data):
        """Löscht eine spezifische Signalzeile aus der UI und der Liste."""
        # Mindestens ein Signal sollte in der Liste bleiben
        if len(self.signal_rows) <= 1:
            print("Hinweis: Es muss mindestens ein Signal in der Liste bleiben!")
            return

        # 1. Aus der Python-Liste entfernen
        self.signal_rows.remove(row_data)

        # 2. Widgets aus der grafischen Oberfläche löschen
        row_data['widget'].deleteLater()

        # 3. Nummern der verbleibenden Zeilen neu berechnen
        QtTest.QTest.qWait(10) # Ganz kurz warten, damit Qt das Widget sauber abbaut
        self.update_row_numbers()

    def update_row_numbers(self):
        """Aktualisiert die Labels (S1, S2, S3...) aller aktiven Zeilen."""
        for idx, row in enumerate(self.signal_rows):
            row['label'].setText(f"<b>S{idx + 1}:</b>")

    def run_sequence(self):
        try:
            if not self.signal_rows:
                print("Fehler: Keine Signale in der Liste!")
                return

            symmetry = float(self.edit_symmetry.text())
            offset = float(self.edit_offset.text())

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

                print(f"[{idx+1}/{len(self.signal_rows)}] Schalte: {f} {u}, {a} Vpp für {d}s")

                my_instrument.set_frequency(f, u)
                QtTest.QTest.qWait(100)
                my_instrument.set_amplitude(a)

                QtTest.QTest.qWait(int(d * 1000))

                if p > 0:
                    print(f"   -> Pause für {p}s (Ausgang auf 0V regeln)...")
                    my_instrument.set_amplitude(0.01)
                    QtTest.QTest.qWait(int(p * 1000))

            print("--- Sequenz erfolgreich beendet ---")

        except ValueError:
            print("Fehler: Bitte überprüfe alle Zahlenwerte in den Signalzeilen!")
        except Exception as e:
            print(f"Fehler während der Sequenzausführung: {e}")

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
