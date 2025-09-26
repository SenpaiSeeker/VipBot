LIGHT_CYAN='\033[1;38;5;87m'
LIGHT_GREEN='\033[1;38;5;120m'
LIGHT_YELLOW='\033[1;38;5;227m'
LIGHT_RED='\033[1;38;5;203m'
LIGHT_MAGENTA='\033[1;38;5;219m'
NC='\033[0m'

clear

echo -e "${LIGHT_CYAN}========================================${NC}"
echo -e "${LIGHT_CYAN}   Konfigurasi VVIP Multi-Bot Manager   ${NC}"
echo -e "${LIGHT_CYAN}========================================${NC}"
echo
echo -e "${LIGHT_YELLOW}Skrip ini akan memandu Anda untuk membuat file environment (.env).${NC}"
echo

read -p "$(echo -e ${LIGHT_MAGENTA}"Masukkan API_ID Anda: "${NC})" API_ID
read -p "$(echo -e ${LIGHT_MAGENTA}"Masukkan API_HASH Anda: "${NC})" API_HASH
read -p "$(echo -e ${LIGHT_MAGENTA}"Masukkan BOT_TOKEN bot utama Anda: "${NC})" BOT_TOKEN
read -p "$(echo -e ${LIGHT_MAGENTA}"Masukkan OWNER_ID numerik Anda: "${NC})" OWNER_ID
read -p "$(echo -e ${LIGHT_MAGENTA}"Masukkan nama file database (${LIGHT_YELLOW}default: vvip_database${LIGHT_MAGENTA}): "${NC})" DB_NAME
DB_NAME=${DB_NAME:-vvip_database}

echo

read -p "$(echo -e ${LIGHT_MAGENTA}"Masukkan nama file environment yang ingin dibuat (${LIGHT_YELLOW}default: vvip.env${LIGHT_MAGENTA}): "${NC})" ENV_FILE
ENV_FILE=${ENV_FILE:-vvip.env}

echo
echo -e "${LIGHT_YELLOW}Membuat file '$ENV_FILE'...${NC}"

cat > "$ENV_FILE" << EOL
API_ID=$API_ID
API_HASH=$API_HASH
BOT_TOKEN=$BOT_TOKEN
OWNER_ID=$OWNER_ID
DB_NAME=$DB_NAME
EOL

echo
echo -e "${LIGHT_GREEN}✅ File '$ENV_FILE' berhasil dibuat!${NC}"
echo
echo -e "${LIGHT_CYAN}================ LANGKAH SELANJUTNYA =================${NC}"
echo -e "${LIGHT_YELLOW}1. Pilih dan ingat sebuah Kunci Enkripsi Rahasia (contoh: 'kunci-vvip-aman-2025').${NC}"
echo -e "${LIGHT_YELLOW}   Anda akan membutuhkannya setiap kali menjalankan bot.${NC}"
echo
echo -e "${LIGHT_YELLOW}2. Jalankan bot menggunakan skrip 'run.sh':${NC}"
echo -e "   ${LIGHT_GREEN}./run.sh${NC}"
echo
echo -e "${LIGHT_YELLOW}   Skrip tersebut akan menanyakan nama file environment ('$ENV_FILE') dan Kunci Enkripsi Rahasia Anda.${NC}"
echo -e "${LIGHT_CYAN}=====================================================${NC}"
