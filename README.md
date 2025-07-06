<h1 align="center">WhazzaStream</h1>

<p align="center">
  <img src="https://whazza.de/online_sachen/images/github/whazzastream.png"
       alt="WhazzaStream Logo" width="120"/>
</p>

> **Hinweis:** Dieses Projekt ist als privates Hobby entstanden.
> Weil die meisten kostenlosen Streaming-Setups kein Login-System bieten, habe ich kurzerhand selbst eines gebaut.
> Ich bin zwar kein Profi, doch der Code läuft stabil genug um damit zu experimentieren.

### Kurzbeschreibung
WhazzaStream ist ein **Self-Hosting-Setup** für Livestreaming  
(**RTMP-Ingest → HLS-Ausgabe**) inklusive Web-Panel.  
Aktuelle Latenz: **5 – 12 Sekunden**.

Das Web-Panel enthält außerdem einen kleinen Shop, in dem Nutzer mit ihren Coins Smilies, alternative Schriftarten, Texteffekte (blur, wave, glitch) sowie eine individuelle Profilfarbe freischalten können.

---

### Voraussetzungen
- Linux-Host (getestet mit **Debian 12**)  
- **Docker** + **Docker Compose**  
- Extern erreichbare **MariaDB**  
- Ports **1935** (RTMP) & **8090** (HLS) offen

---

### Installation (Quick Start)
```bash
# Repository direkt unter /home klonen (vereinfacht den Installer)
cd /home
git clone https://github.com/whazza1983/streaming.git
cd streaming

# Installer vorbereiten und starten
chmod 0755 install.sh
./install.sh
