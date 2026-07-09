# GW-Instek AFG-2225 Rampen-Sequenzer & Live-Control

Dieses Python-Programm bietet eine grafische Oberfläche auf Basis von **PyQt6** zur präzisen Steuerung des Funktionsgenerators **GW-Instek AFG-2225** über eine USB-Verbindung. 

Das Tool erlaubt es zum einen, eine zeitliche Abfolge von Dreieckssignalen (Rampen) mit **konstanter Flankensteilheit (V/ms)** zu programmieren, und bringt zum anderen ein separates **Live-Direktansteuerungs-Fenster** mit, um Einstellungen spontan und verzögerungsfrei an die Hardware zu senden.

## 🚀 Features
* **Dynamische Signalabfolge:** Beliebig viele Teilsignale per Knopfdruck hinzufügen oder entfernen.
* **Echte Hardware-Pausen:** Schaltet den Ausgang bei definierten Pausenzeiten über das Relais komplett ab und phasenrein für das nächste Signal wieder an. Automatic-Auto-Stop am Ende der Sequenz.
* **Interaktive Vorschau:** Echtzeit-Plotter (Matplotlib) zur visuellen Überprüfung der Soll-Sequenz vor dem Hardware-Start.
* **🎛️ Live-Direktansteuerung:** Ein auswählbares Zweitfenster zur On-the-fly-Regelung von Frequenz, Amplitude, DC-Offset und Signalform (inkl. globalem "Burst/Sweep-Aus"-Schalter).
* **Automatischer Port-Scan:** Erkennt beim Start und per Refresh-Button angeschlossene Geräte plattformübergreifend (COM-Ports unter Windows, `/dev/ttyACM` unter Linux).
* **Speicherfunktion:** Erstellte Sequenzen als `.json`-Datei sichern und laden.

---

## 📁 Projektstruktur
* `sequencer_GUI.py` — Das Hauptfenster für die grafische Rampen-Sequenzverwaltung.
* `live_control.py` — Das modulare Zusatzfenster für die Live-Direktansteuerung.
* `afg2225library/` — Der Kern-Ordner mit den Hardware-Treibermethoden des Generators.
* `pyproject.toml` & `uv.lock` — Moderne Konfigurations- und Sperrdateien für den `uv`-Paketmanager.

---

## 🔌 Treiber-Installation & Vorbereitung

Dank des Python-nativen VISA-Backends benötigt das System **keine proprietären Treiber von National Instruments (NI)** unter Linux!

### 🐧 Unter Linux (Fedora, Pop!_OS, Ubuntu, Mint)
Der Linux-Kernel erkennt den Generator automatisch als virtuellen seriellen Port (`/dev/ttyACM0`). Du musst deinem Benutzer lediglich Zugriffsrechte für die Schnittstelle gewähren:

1. **USB-Zugriff erlauben:**
   ```bash
   sudo usermod -a -G dialout $USER
   ```
*Danach einmal vom System abmelden und neu anmelden, damit die Gruppenrechte aktiv werden.*

### 🪟 Unter Windows

Unter Windows wird ein Standard-USB-VCP (Virtual COM Port) Treiber benötigt, damit das Gerät im Geräte-Manager einen festen Port (z. B. `COM10`) zugewiesen bekommt. Die Kommunikation wird im Code komplett über das schlanke Python-native Serial-Backend abgewickelt.

   Download AFG-2225 USB driver from GW Instek Website:
   https://www.gwinstek.com/en-global/products/detail/AFG-2225

## 🛠️ Installation & Start mit uv (Empfohlen)

Das Projekt nutzt den modernen Python-Paketmanager `uv`. Dieser verwaltet Python-Versionen (voll kompatibel mit Python 3.14+) und Abhängigkeiten isoliert im Hintergrund, ohne dein System zu belasten.

1. **Repository klonen & in den Ordner wechseln:**
```bash
git clone https://github.com/speicherl/afg2225-sequencer.git
cd afg2225-sequencer
```


2. **App via uv starten:**
Führe einfach den folgenden Befehl im Hauptverzeichnis aus. `uv` installiert automatisch alle benötigten Abhängigkeiten (`PyQt6`, `matplotlib`, `numpy`, `pyvisa-py`, `pyserial`) in eine virtuelle Umgebung und startet die Anwendung:
```bash
uv run sequencer_GUI.py
```


3. **Bedienung der Hardware:**
* Klicke oben im Fenster auf **🔄 Aktualisieren**, um die USB-Kanäle zu scannen.
* Wähle den erkannten Port aus (z. B. `/dev/ttyACM0` oder `COM10`) und klicke auf **⚡ Verbinden**.
* Nach erfolgreichem Verbindungsaufbau werden alle Steuerungselemente sowie das Live-Fenster freigeschaltet.