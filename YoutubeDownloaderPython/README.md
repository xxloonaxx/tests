# YouTube Downloader (Python, Tkinter)

Eine einfache Desktop-Anwendung zum Herunterladen von YouTube-Videos oder -Audiospuren.

## Features

- Lädt Metadaten (Titel, Dauer, Kanal) für beliebige YouTube-URLs.
- Listet verfügbare **MP4**-Video-Formate inklusive Auflösung, Bildrate, geschätzter Bitrate und Dateigröße.
- Listet Audio-Only-Formate mit Bitrate, Container und Dateigröße – ideal für Musik-Downloads.
- Fortschrittsanzeige mit Geschwindigkeit, verbleibender Zeit und Downloadfortschritt.
- Wahl des Zielordners sowie Möglichkeit, Downloads abzubrechen.

## Voraussetzungen

- Python 3.9 oder neuer.
- Installierte Abhängigkeiten aus `requirements.txt`:

```bash
pip install -r requirements.txt
```

Unter Windows empfiehlt es sich, das Skript in einer venv zu betreiben:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Anwendung starten

```bash
python app.py
```

Gib anschließend im Fenster eine YouTube-URL ein, klicke auf **„Info laden"**, wähle ein Format und starte den Download.

> **Hinweis:** yt-dlp benötigt Netzwerkzugriff auf YouTube. In restriktiven Netzwerken oder bei gesperrten Inhalten kann der Download fehlschlagen.
