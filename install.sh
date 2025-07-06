#!/bin/bash

ORANGE=$'\033[0;33m'
GREEN=$'\033[0;32m'
RED=$'\033[0;31m'
BRIGHT_RED=$'\033[1;31m'
CYAN=$'\033[0;36m'
NC=$'\033[0m'

stty sane        2>/dev/null || true
stty -echoctl

cleanup() {
  echo -ne "\033[0K${NC}"
  command -v stty >/dev/null && stty sane 2>/dev/null || true
}

trap cleanup EXIT

trap 'echo; cleanup; exit 130' INT TERM


read_secret() {
  local prompt="$1" var_name="$2"
  echo -n "$prompt"
  stty -echo
  read -r "$var_name"
  stty echo
  echo
}

ini_get() {
  local section="$1" key="$2"
  awk -F' *= *' -v section="$section" -v key="$key" '
    $0=="["section"]"{f=1;next}
    /^\[/{f=0}
    f && $1==key {print $2; exit}
  ' "$CONFIG_FILE"
}

echo "${CYAN}Bitte Sprache wählen / Please choose language:"
echo "  1) Deutsch"
echo "  2) English${NC}"
read -e -rp "Auswahl (1/2): " lang_choice

case "$lang_choice" in
  2) LANG="en" ;;
  1|*) LANG="de" ;;
esac

if [ "$LANG" = "de" ]; then
  TXT_TITLE="WhazzaStream Installer"
  TXT_CONFIG_FOUND="Fehler: Eine bestehende Konfiguration wurde gefunden:"
  TXT_DB_EXISTS="Fehler: Die Datenbank '%s' existiert bereits."
  TXT_REMOVE="Bitte entferne zuerst die Datei und die Datenbank, bevor du neu installierst."  
  TXT_MENU_OVERWRITE="1) Alles überschreiben"
  TXT_MENU_EDIT="2) Einzelne Werte ändern"
  TXT_MENU_ABORT="3) Abbrechen"
  TXT_CHOICE="Auswahl (1/2/3): "
  TXT_OVERWRITE_SELECTED="Vollständige Überschreibung gewählt."
  TXT_EDIT_VALUES="Einzelne Werte ändern …"
  TXT_ASK_IP="Öffentliche IP               : "
  TXT_ASK_DB_HOST="Datenbank-Host               : "
  TXT_ASK_DB_PORT="Datenbank-Port (3306)        : "
  TXT_ASK_DB_NAME="Datenbank-Name               : "
  TXT_ASK_DB_USER="Datenbank-Benutzer           : "
  TXT_ASK_DB_PASS="Datenbank-Passwort           : "
  TXT_DB_CHECK="🔍 Prüfe DB-Verbindung …"
  TXT_DB_SUCCESS="✅ Verbindung erfolgreich!"
  TXT_DB_FAIL="❌ Verbindung fehlgeschlagen – erneut."
  TXT_ASK_ADMIN_USER="Admin-Benutzer              : "
  TXT_ASK_ADMIN_PASS="Admin-Passwort              : "
  TXT_ASK_ADMIN_PASS_CONFIRM="Passwort wiederholen        : "
  TXT_PW_MISMATCH_RETRY="❌ Nicht identisch – erneut."
  TXT_PW_MISMATCH_ABORT="❌ Nicht identisch – Abbruch."
  TXT_ASK_ADMIN_COLOR="Admin-Farbe (Hex z. B. #FF3030) : "
  TXT_ASK_DISCORD="(Optional) Discord Webhook   : "
  TXT_RESTART_CONTAINERS="♻️  Container neu starten …"
  TXT_DONE="✅ Fertig."
  TXT_ABORT="⛔ Abbruch."
  TXT_INVALID="❌ Ungültige Wahl."
  TXT_INSTALL_COMPLETE="✅ WhazzaStream-Installation abgeschlossen!"
else
  TXT_TITLE="WhazzaStream Installer"
  TXT_CONFIG_FOUND="Error: Existing configuration found:"
  TXT_DB_EXISTS="Error: Database '%s' already exists."
  TXT_REMOVE="Please remove the config file and the database before reinstalling."  
  TXT_MENU_OVERWRITE="1) Overwrite everything"
  TXT_MENU_EDIT="2) Edit individual values"
  TXT_MENU_ABORT="3) Abort"
  TXT_CHOICE="Choice (1/2/3): "
  TXT_OVERWRITE_SELECTED="Full overwrite selected."
  TXT_EDIT_VALUES="Editing individual values …"
  TXT_ASK_IP="Public IP address            : "
  TXT_ASK_DB_HOST="Database host               : "
  TXT_ASK_DB_PORT="Database port (3306)        : "
  TXT_ASK_DB_NAME="Database name               : "
  TXT_ASK_DB_USER="Database user               : "
  TXT_ASK_DB_PASS="Database password           : "
  TXT_DB_CHECK="🔍 Checking DB connection …"
  TXT_DB_SUCCESS="✅ Connection successful!"
  TXT_DB_FAIL="❌ Connection failed – retry."
  TXT_ASK_ADMIN_USER="Admin user                 : "
  TXT_ASK_ADMIN_PASS="Admin password             : "
  TXT_ASK_ADMIN_PASS_CONFIRM="Repeat password           : "
  TXT_PW_MISMATCH_RETRY="❌ Not identical – retry."
  TXT_PW_MISMATCH_ABORT="❌ Not identical – abort."
  TXT_ASK_ADMIN_COLOR="Admin color (hex e.g. #FF3030): "
  TXT_ASK_DISCORD="(Optional) Discord webhook  : "
  TXT_RESTART_CONTAINERS="♻️  Restarting containers …"
  TXT_DONE="✅ Done."
  TXT_ABORT="⛔ Aborting."
  TXT_INVALID="❌ Invalid choice."
  TXT_INSTALL_COMPLETE="✅ WhazzaStream installation complete!"
fi

set -e
echo -e "${BRIGHT_RED}${TXT_TITLE}${NC}"

CONFIG_FILE="/portainer/whazzastream/config/config.cfg"

if [ -f "$CONFIG_FILE" ]; then
  echo -e "\033[1;31m${TXT_CONFIG_FOUND} ${CONFIG_FILE}\033[0m"

  db_host=$(ini_get database host)
  db_user=$(ini_get database user)
  db_pass=$(ini_get database password)
  db_name=$(ini_get database database)

  if mysql -h "$db_host" -u"$db_user" -p"$db_pass" -e "USE \`$db_name\`" &>/dev/null; then
    printf "\033[1;31m${TXT_DB_EXISTS}\033[0m\n" "$db_name"
  fi

  echo -e "\033[0;36m${TXT_REMOVE}\033[0m"
  exit 1
fi

read -e -rp "${TXT_ASK_IP}" IP_ADDR

while true; do
  read -e -rp "${TXT_ASK_DB_HOST}" DB_HOST
  read -e -rp "${TXT_ASK_DB_PORT}" DB_PORT; DB_PORT=${DB_PORT:-3306}
  read -e -rp "${TXT_ASK_DB_NAME}" DB_NAME
  read -e -rp "${TXT_ASK_DB_USER}" DB_USER
  read_secret "${TXT_ASK_DB_PASS}" DB_PASS
  echo "${ORANGE}$TXT_DB_CHECK${NC}"
  if mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" -e "USE $DB_NAME;" 2>/dev/null; then
    echo "${GREEN}$TXT_DB_SUCCESS${NC}"
    break
  else
    echo "${RED}$TXT_DB_FAIL${NC}"
  fi
done

read -e -rp "${TXT_ASK_ADMIN_USER}" ADMIN_USER
while true; do
  read_secret "${TXT_ASK_ADMIN_PASS}" ADMIN_PASS
  read_secret "${TXT_ASK_ADMIN_PASS_CONFIRM}" CONFIRM
  if [[ "$ADMIN_PASS" == "$CONFIRM" ]]; then
    break
  else
    echo "$TXT_PW_MISMATCH_RETRY"
  fi
done
read -e -rp "${TXT_ASK_ADMIN_COLOR}" ADMIN_COLOR
read -e -rp "${TXT_ASK_DISCORD}" DISCORD_WEBHOOK

mkdir -p /portainer/{hls,nginx,whazzastream/config}
cp -r /home/streaming/hls/.          /portainer/hls/
cp -r /home/streaming/nginx/*        /portainer/nginx/
cp -r /home/streaming/whazzastream/* /portainer/whazzastream/

sed -i "s|http://.*:5015|http://$IP_ADDR:5015|g" /portainer/nginx/nginx.conf

mkdir -p "$(dirname "$CONFIG_FILE")"
{
  echo "[database]"
  echo "host = $DB_HOST"
  echo "port = $DB_PORT"
  echo "database = $DB_NAME"
  echo "user = $DB_USER"
  echo "password = $DB_PASS"
  echo
  echo "[admin]"
  echo "username = $ADMIN_USER"
  echo "password = $ADMIN_PASS"
  echo "color = $ADMIN_COLOR"
  echo
  echo "[stream]"
  echo "base_url = http://$IP_ADDR:8090"
  [ -n "$DISCORD_WEBHOOK" ] && { echo; echo "[discord]"; echo "webhook = $DISCORD_WEBHOOK"; }
} > "$CONFIG_FILE"

cd /home/streaming
docker compose build --no-cache
docker compose up -d

echo -e "${GREEN}${TXT_INSTALL_COMPLETE}${NC}"
