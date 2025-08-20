LIGHT_CYAN='\033[1;38;5;87m'
LIGHT_GREEN='\033[1;38;5;120m'
LIGHT_YELLOW='\033[1;38;5;227m'
LIGHT_RED='\033[1;38;5;203m'
LIGHT_MAGENTA='\033[1;38;5;219m'
NC='\033[0m'

clear

echo -e "${LIGHT_CYAN}==============================${NC}"
echo -e "${LIGHT_CYAN}  VVIP Multi-Bot Launcher     ${NC}"
echo -e "${LIGHT_CYAN}==============================${NC}"
echo

read -p "$(echo -e ${LIGHT_MAGENTA}"Masukkan nama file environment (${LIGHT_YELLOW}default: vvip.env${LIGHT_MAGENTA}): "${NC})" ENV_FILE
ENV_FILE=${ENV_FILE:-vvip.env}

if [ ! -f "$ENV_FILE" ]; then
    echo
    echo -e "${LIGHT_RED}❌ Error: File '$ENV_FILE' tidak ditemukan.${NC}"
    echo -e "${LIGHT_YELLOW}Pastikan Anda telah menjalankan 'bash config.sh' terlebih dahulu.${NC}"
    exit 1
fi

read -s -p "$(echo -e ${LIGHT_MAGENTA}"Masukkan kunci enkripsi rahasia: "${NC})" SECRET_KEY
echo

if [ -z "$SECRET_KEY" ]; then
    echo
    echo -e "${LIGHT_RED}❌ Error: Kunci enkripsi tidak boleh kosong.${NC}"
    exit 1
fi

echo
echo -e "${LIGHT_GREEN}✅ Konfigurasi diterima. Menjalankan bot...${NC}"
echo -e "${LIGHT_CYAN}------------------------------------------------${NC}"
echo

python3 main.py --key "$SECRET_KEY" --env "$ENV_FILE"
