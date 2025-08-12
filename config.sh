GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}--- Skrip Konfigurasi VVIP Multi-Bot Manager ---${NC}"
echo "Skrip ini akan memandu Anda membuat file konfigurasi environment."
echo ""

echo -e "${YELLOW}Silakan masukkan kredensial Telegram Anda yang diperlukan:${NC}"
read -p "Masukkan API_ID Anda: " API_ID
read -p "Masukkan API_HASH Anda: " API_HASH
read -p "Masukkan BOT_TOKEN Anda (untuk Bot Utama/Induk): " BOT_TOKEN
read -p "Masukkan OWNER_ID Anda (ID Telegram numerik Anda): " OWNER_ID
echo ""

read -p "Masukkan nama file untuk environment Anda [default: .env]: " FILENAME
FILENAME=${FILENAME:-.env}

echo "Membuat file konfigurasi: $FILENAME..."

cat << EOF > "$FILENAME"
API_ID=$API_ID
API_HASH=$API_HASH
BOT_TOKEN=$BOT_TOKEN
OWNER_ID=$OWNER_ID
EOF

echo ""
echo -e "${GREEN}✅ File konfigurasi '$FILENAME' berhasil dibuat!${NC}"
echo "Sekarang Anda dapat menjalankan bot menggunakan perintah di bawah ini:"

if [ "$FILENAME" == ".env" ]; then
    echo -e "${CYAN}python3 main.py${NC}"
else
    echo -e "${CYAN}python3 main.py \"$FILENAME\"${NC}"
fi
