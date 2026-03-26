LIGHT_CYAN='\033[1;38;5;87m'
LIGHT_GREEN='\033[1;38;5;120m'
LIGHT_YELLOW='\033[1;38;5;227m'
LIGHT_RED='\033[1;38;5;203m'
LIGHT_MAGENTA='\033[1;38;5;219m'
LIGHT_BLUE='\033[1;38;5;75m'
LIGHT_WHITE='\033[1;38;5;255m'
NC='\033[0m'

clear

function banner() {
    echo -e "${LIGHT_CYAN}╔══════════════════════════════════════╗${NC}"
    echo -e "${LIGHT_CYAN}║         VVIP Multi-Bot Control Hub        ║${NC}"
    echo -e "${LIGHT_CYAN}╚══════════════════════════════════════╝${NC}"
    echo
}

function loading() {
    echo -ne "${LIGHT_BLUE}Memuat sistem"
    for i in {1..6}; do
        echo -ne "."
        sleep 0.2
    done
    echo -e "${NC}"
    echo
}

banner
loading

if [ ! -d envpath ]; then
    echo -e "${LIGHT_RED}❌ Direktori envpath tidak ditemukan${NC}"
    exit 1
fi

shopt -s nullglob
env_files=( envpath/*.env )
shopt -u nullglob

if [ ${#env_files[@]} -eq 0 ]; then
    echo -e "${LIGHT_RED}❌ Tidak ada file .env di envpath${NC}"
    exit 1
fi

IFS=$'\n' sorted_env_files=($(printf "%s\n" "${env_files[@]}" | sort -f -V))
unset IFS

echo -e "${LIGHT_CYAN}Daftar Environment Tersedia:${NC}"
for i in "${!sorted_env_files[@]}"; do
    name_only="$(basename "${sorted_env_files[$i]}")"
    printf "${LIGHT_YELLOW}%2d${NC}. ${LIGHT_WHITE}%s${NC}\n" "$((i+1))" "$name_only"
done

echo
read -p "$(echo -e ${LIGHT_MAGENTA}"Pilih nomor environment: "${NC})" choice

if ! [[ "$choice" =~ ^[0-9]+$ ]]; then
    echo -e "${LIGHT_RED}❌ Input harus angka${NC}"
    exit 1
fi

if [ "$choice" -lt 1 ] || [ "$choice" -gt ${#sorted_env_files[@]} ]; then
    echo -e "${LIGHT_RED}❌ Nomor di luar jangkauan${NC}"
    exit 1
fi

ENV_FILE="${sorted_env_files[$((choice-1))]}"

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${LIGHT_RED}❌ File tidak ditemukan${NC}"
    exit 1
fi

echo
read -s -p "$(echo -e ${LIGHT_MAGENTA}"Masukkan kunci enkripsi: "${NC})" DB_KEY
echo

if [ -z "$DB_KEY" ]; then
    echo -e "${LIGHT_RED}❌ Kunci tidak boleh kosong${NC}"
    exit 1
fi

echo
echo -e "${LIGHT_GREEN}✔ Environment: $(basename "$ENV_FILE")${NC}"
echo -e "${LIGHT_GREEN}✔ Kunci diterima${NC}"
echo

echo -e "${LIGHT_BLUE}Menyiapkan eksekusi...${NC}"
sleep 1
echo -e "${LIGHT_CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

nice -n 10 ionice -c2 -n7 python3 main.py --key "$DB_KEY" --env "$ENV_FILE"
