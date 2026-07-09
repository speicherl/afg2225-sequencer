# GW-Instek AFG-2225 Rampen-Sequenzer

Dieses Python-Programm bietet eine grafische PyQt5-Oberfläche zur präzisen Steuerung des Funktionsgenerators **GW-Instek AFG-2225** über eine USB-Verbindung. 

Das Tool erlaubt es, eine zeitliche Abfolge von Dreieckssignalen (Rampen) mit **konstanter Flankensteilheit (V/ms)** zu definieren, abzuspeichern und an das Gerät zu übertragen. Jedes Signal wird über seine Amplitude und die exakte Anzahl an Schwingungsperioden (`Cycles`) definiert, was einen phasenreinen Übergang ohne Signalabrisse garantiert.

## 🚀 Features
* **Dynamische Signalabfolge:** Beliebig viele Teilsignale per Knopfdruck hinzufügen oder entfernen.
* **Konstante Flankensteilheit (V/ms):** Die Software berechnet die notwendige Zielfrequenz für jede Amplitude automatisch, sodass alle Flanken physikalisch parallel laufen.
* **Interaktive Vorschau:** Echtzeit-Plotter mit Zoom- und Verschiebe-Werkzeug (Matplotlib) zur Sichtung des Soll-Signals.
* **Speicherfunktion:** Erstellte Sequenzen als `.json`-Datei sichern und jederzeit wieder laden.
* **Hardware-Schutzschaltung:** Automatische Filterung unzulässiger Werte vor der Übertragung (Schutz vor Überspannungen).

---

## 🔌 Treiber-Installation & Vorbereitung

Damit Python mit dem GW-Instek AFG-2225 kommunizieren kann, muss das System wissen, wie es den USB-VCP (Virtual COM Port) des Geräts ansprechen soll.

### 🐧 Unter Linux (Keine externen Treiber nötig)
Unter Linux bringt der Kernel bereits alles mit (`cdc_acm` Modul). Das Gerät wird automatisch als `/dev/ttyACM0` (oder ähnlich) eingebunden. 

Du musst lediglich dafür sorgen, dass Python-native Treiber genutzt werden und dein Benutzer die Rechte hat:
1. **USB-Zugriff erlauben:**
   ```bash
   sudo usermod -a -G dialout $USER
   ```

*Danach einmal vom System abmelden und neu anmelden, damit die Rechte aktiv werden.*

2. **Pakete:** Die Pakete `pyvisa-py` und `pyusb` (werden von `uv` automatisch installiert) emulieren die komplette VISA-Schicht in purem Python. Keine Software von National Instruments erforderlich.

### 🪟 Unter Windows (NI-VISA benötigt)

Windows benötigt einen dedizierten VISA-Treiberstack, um das USB-Gerät als VISA-Ressource registrieren zu können.

1. **NI-VISA herunterladen:**
* Gehe auf die offizielle Support-Seite von National Instruments: [NI-VISA Download](https://www.google.com/search?q=https://www.ni.com/de-de/support/downloads/drivers/download.ni-visa.html)
* Wähle die aktuellste Version aus.
* Wähle als Betriebssystem **Windows** und klicke auf **Herunterladen**.


2. **Installation:**
* Starte den Installer (die `.exe`-Datei).
* Im Installations-Assistenten reicht die Standardauswahl (du brauchst *keine* Entwicklungs-Add-Ons für C++ oder LabVIEW, sondern nur die **NI-VISA Runtime**).
* Starte den Computer nach der Installation einmal neu.


3. **Gerät überprüfen (Optional):**
* Schließe den AFG-2225 per USB an deinen PC an und schalte ihn ein.
* Öffne das Programm **NI MAX** (NI Measurement & Automation Explorer), das mitinstalliert wurde.
* Unter "Geräte und Schnittstellen" sollte der Generator nun auftauchen (z. B. als `ASRL3::INSTR` oder unter einem spezifischen COM-Port wie `COM3`).



---

## 🛠️ Installation & Start mit uv (Empfohlen)

Wenn du den modernen Python-Paketmanager `uv` nutzt, musst du Python nicht manuell verwalten oder virtuelle Umgebungen händisch aktivieren. `uv` erledigt alles isoliert im Hintergrund.

1. **Repository klonen & in den Ordner wechseln:**
```bash
git clone <git@github.com:speicherl/afg2225-sequencer.git
>
cd afg2225-sequencer
```


2. **Abhängigkeiten automatisch installieren und App starten:**
Führe einfach den folgenden Befehl aus. `uv` erstellt selbstständig eine virtuelle Umgebung, installiert alle nötigen Pakete (`PyQt5`, `matplotlib`, `numpy`, `pyvisa`, `pyvisa-py`, `pyusb`) und startet die GUI:
```bash
uv run sequencer_GUI.py
```


3. **💡 Linux-Spezifischer Start:**
Zwinge PyVISA über eine Umgebungsvariable, das Python-native Treiber-Modul zu nutzen:
```bash
PYVISA_LIBRARY="@py" uv run sequencer_GUI.py
```


4. **💡 Windows-Spezifische Anpassung:**
Öffne die `sequencer_GUI.py` und passe ganz unten im `__main__`-Block die Adresse von `ASRL/dev/ttyACM0::INSTR` auf deinen Windows-Port an (z. B. `COM3` oder `ASRL3::INSTR` – einsehbar im Windows Geräte-Manager). Danach in der Eingabeaufforderung (cmd) starten:
```cmd
uv run sequencer_GUI.py
```
