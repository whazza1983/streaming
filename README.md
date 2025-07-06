<h1 align="center">WhazzaStream</h1>

<p align="center">
  <img src="https://whazza.de/online_sachen/images/github/whazzastream.png"
       alt="WhazzaStream Logo" width="120"/>
</p>

<details> <summary><strong>English</strong></summary>

> **Note:** This project was created as a private hobby.  
> Because most free streaming setups don’t offer a login system, I quickly built one myself.  
> I’m not a professional, but the code runs stably enough to experiment with.

### Short Description
WhazzaStream is a **self-hosting setup** for live streaming  
(**RTMP ingest → HLS output**) including a web panel.  
Current latency: **5 – 12 seconds**.

The web panel also contains a small shop where users can unlock smilies, alternative fonts, text effects (blur, wave, glitch) and an individual profile color with their coins.

---

### Requirements
- Linux host (tested with **Debian 12**)  
- **Docker** + **Docker Compose**  
- Externally accessible **MariaDB**  
- Ports **1935** (RTMP) & **8090** (HLS) open

---

### Installation (Quick Start)
```bash
# Clone the repository directly under /home (simplifies the installer)
cd /home
git clone https://github.com/whazza1983/streaming.git
cd streaming

# Prepare and start the installer
chmod 0755 install.sh
./install.sh

```

---

**Info**

- **Smilies**: Animated Noto Emoji from  
  <https://googlefonts.github.io/noto-emoji-animation/>
- **Fonts**: Various Google Fonts, included completely offline in the repository (no external requests)

</details>

<details> <summary><strong>German</strong></summary>

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

```

---

**Info**

- **Smilies**: Animierte Noto-Emoji von  
  <https://googlefonts.github.io/noto-emoji-animation/>
- **Fonts**: Verschiedene Google-Fonts, komplett **offline** im Repository enthalten (keine externen Requests)

</details>
