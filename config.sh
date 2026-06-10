#!/usr/bin/env bash

LIGHT_CYAN='\033[1;38;5;87m'
LIGHT_GREEN='\033[1;38;5;120m'
LIGHT_YELLOW='\033[1;38;5;227m'
LIGHT_RED='\033[1;38;5;203m'
LIGHT_MAGENTA='\033[1;38;5;219m'
LIGHT_BLUE='\033[1;38;5;75m'
LIGHT_WHITE='\033[1;38;5;255m'
LIGHT_GRAY='\033[1;38;5;244m'
NC='\033[0m'

clear

function banner() {
    echo -e "${LIGHT_CYAN}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${LIGHT_CYAN}║       VVIP Multi-Bot — Konfigurasi Env     ║${NC}"
    echo -e "${LIGHT_CYAN}╚═══════════════════════════════════════════╝${NC}"
    echo
}

function loading() {
    echo -ne "${LIGHT_BLUE}Menyiapkan konfigurasi"
    for i in {1..5}; do
        echo -ne "."
        sleep 0.15
    done
    echo -e "${NC}"
    echo
}

function prompt_required() {
    local label="$1"
    local varname="$2"
    local value=""
    while [ -z "$value" ]; do
        read -p "$(echo -e "${LIGHT_YELLOW}${label}${NC}: ")" value
        if [ -z "$value" ]; then
            echo -e "${LIGHT_RED}  ✗ Tidak boleh kosong, coba lagi.${NC}"
        fi
    done
    eval "$varname=\"$value\""
}

function prompt_default() {
    local label="$1"
    local varname="$2"
    local default_val="$3"
    read -p "$(echo -e "${LIGHT_YELLOW}${label}${NC} ${LIGHT_GRAY}[${default_val}]${NC}: ")" value
    if [ -z "$value" ]; then
        value="$default_val"
    fi
    eval "$varname=\"$value\""
}

function prompt_secret() {
    local label="$1"
    local varname="$2"
    local value=""
    while [ -z "$value" ]; do
        read -s -p "$(echo -e "${LIGHT_YELLOW}${label}${NC}: ")" value
        echo
        if [ -z "$value" ]; then
            echo -e "${LIGHT_RED}  ✗ Tidak boleh kosong, coba lagi.${NC}"
        fi
    done
    eval "$varname=\"$value\""
}

function separator() {
    echo -e "${LIGHT_CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

banner
loading

separator
echo -e "${LIGHT_WHITE}  Masukkan konfigurasi bot utama Anda:${NC}"
separator
echo

prompt_required "  API ID (dari my.telegram.org)" API_ID
prompt_required "  API Hash (dari my.telegram.org)" API_HASH
prompt_required "  Bot Token (dari @BotFather)" BOT_TOKEN
prompt_required "  Owner ID (ID Telegram Anda)" OWNER_ID
prompt_default  "  Nama Database" DB_NAME "vvip_database"
prompt_default  "  Username Bot Backup (tanpa @)" BACKUP_BOT ""

echo
separator
echo -e "${LIGHT_WHITE}  Pengaturan file environment:${NC}"
separator
echo

ENVDIR="envpath"

if [ ! -d "$ENVDIR" ]; then
    mkdir -p "$ENVDIR"
    echo -e "${LIGHT_BLUE}  ✔ Folder '${ENVDIR}' dibuat.${NC}"
fi

prompt_default "  Nama file env (tanpa .env)" ENV_FILENAME "vvip"

ENV_FILENAME="${ENV_FILENAME%.env}"
ENV_PATH="${ENVDIR}/${ENV_FILENAME}.env"

if [ -f "$ENV_PATH" ]; then
    echo
    echo -e "${LIGHT_YELLOW}  ⚠ File '${ENV_PATH}' sudah ada.${NC}"
    read -p "$(echo -e "${LIGHT_MAGENTA}  Timpa file ini? (y/N): ${NC}")" overwrite
    if [[ ! "$overwrite" =~ ^[Yy]$ ]]; then
        echo -e "${LIGHT_RED}  ✗ Dibatalkan. File tidak diubah.${NC}"
        exit 0
    fi
fi

cat > "$ENV_PATH" << EOF
API_ID=${API_ID}
API_HASH=${API_HASH}
BOT_TOKEN=${BOT_TOKEN}
OWNER_ID=${OWNER_ID}
DB_NAME=${DB_NAME}
BACKUP_BOT=${BACKUP_BOT}
EOF

echo
separator
echo -e "${LIGHT_GREEN}  ✔ File env berhasil dibuat:${NC}"
echo -e "${LIGHT_WHITE}  📄 Lokasi : ${LIGHT_CYAN}${ENV_PATH}${NC}"
echo -e "${LIGHT_WHITE}  🔧 DB Name: ${LIGHT_CYAN}${DB_NAME}${NC}"
separator
echo
echo -e "${LIGHT_MAGENTA}  Langkah selanjutnya:${NC}"
echo -e "${LIGHT_WHITE}  1. Jalankan bot dengan:  ${LIGHT_CYAN}chmod +x run.sh && ./run.sh${NC}"
echo -e "${LIGHT_WHITE}  2. Pilih file env yang baru dibuat saat diminta.${NC}"
echo -e "${LIGHT_WHITE}  3. Masukkan kunci enkripsi database Anda.${NC}"
echo
