RED='\033[38;5;196m'
GREEN='\033[38;5;46m'
YELLOW='\033[38;5;226m'
BLUE='\033[38;5;75m'
MAGENTA='\033[38;5;201m'
CYAN='\033[38;5;51m'
WHITE='\033[38;5;255m'
ORANGE='\033[38;5;208m'
PURPLE='\033[38;5;93m'
GRAY='\033[38;5;244m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Harap jalankan script ini sebagai root (sudo).${NC}"
    exit 1
fi

PROJECT_DIR="$(pwd)"
VENV_PYTHON=""

if [ -f "$PROJECT_DIR/env/bin/python3" ]; then
    VENV_PYTHON="$PROJECT_DIR/env/bin/python3"
elif [ -f "$PROJECT_DIR/env/bin/python" ]; then
    VENV_PYTHON="$PROJECT_DIR/env/bin/python"
else
    echo -e "${RED}❌ Virtual environment tidak ditemukan di directory 'env'.${NC}"
    exit 1
fi

clear

function banner() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    VipBot Control Hub                        ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
}

if [ ! -d envpath ]; then
    echo -e "${RED}❌ Direktori envpath tidak ditemukan${NC}"
    exit 1
fi

shopt -s nullglob
env_files=( envpath/*.env )
shopt -u nullglob

if [ ${#env_files[@]} -eq 0 ]; then
    echo -e "${RED}❌ Tidak ada file .env di envpath${NC}"
    exit 1
fi

IFS=$'\n' sorted_env_files=($(printf "%s\n" "${env_files[@]}" | sort -f -V))
unset IFS

function show_menu() {
    banner
    local per_row=4
    local total=${#sorted_env_files[@]}

    echo -e "${CYAN}Daftar Environment dan Status Layanan:${NC}"
    echo -e "${GRAY}----------------------------------------------------------------------------------------------------${NC}"
    for i in "${!sorted_env_files[@]}"; do
        local file_path="${sorted_env_files[$i]}"
        local name_only="$(basename "$file_path")"
        local base_name="${name_only%.*}"
        local service_name="vipbot_${base_name}"
        
        local raw_status
        local status_color
        if systemctl is-active --quiet "$service_name" 2>/dev/null; then
            raw_status="[ON]"
            status_color="${GREEN}"
        else
            raw_status="[OFF]"
            status_color="${RED}"
        fi
        
        local padded_status
        printf -v padded_status "%-5s" "${raw_status}"
        local status="${status_color}${padded_status}${NC}"
        
        local idx_str="$((i+1))."
        
        printf " ${YELLOW}%-4s${NC}${WHITE}%-12s${NC} %b   " "${idx_str}" "${base_name}" "${status}"
        
        if [ "$(( (i+1) % per_row ))" -eq 0 ]; then
            echo
        fi
    done

    if [ "$(( total % per_row ))" -ne 0 ]; then
        echo
    fi
    echo -e "${GRAY}----------------------------------------------------------------------------------------------------${NC}"
    echo -e "${BLUE}Petunjuk Pilihan: Angka (misal: 5) | Kisaran (misal: 1-5) | Kombinasi (misal: 1,3,5-8) | 'all' atau '*'${NC}"
    echo
}

function parse_selection() {
    local input="$1"
    local max="$2"
    local -a selected=()
    if [[ "$input" == "all" || "$input" == "*" ]]; then
        for ((i=1; i<=max; i++)); do
            selected+=($i)
        done
        echo "${selected[@]}"
        return 0
    fi
    IFS=',' read -ra ADDR <<< "$input"
    for part in "${ADDR[@]}"; do
        part=$(echo "$part" | xargs)
        if [[ "$part" =~ ^[0-9]+-[0-9]+$ ]]; then
            local start=$(echo "$part" | cut -d'-' -f1)
            local end=$(echo "$part" | cut -d'-' -f2)
            if [ "$start" -le "$end" ] && [ "$start" -ge 1 ] && [ "$end" -le "$max" ]; then
                for ((i=start; i<=end; i++)); do
                    selected+=($i)
                done
            fi
        elif [[ "$part" =~ ^[0-9]+$ ]]; then
            if [ "$part" -ge 1 ] && [ "$part" -le "$max" ]; then
                selected+=($part)
            fi
        fi
    done
    echo $(echo "${selected[@]}" | tr ' ' '\n' | sort -nu | tr '\n' ' ')
}

function main() {
    show_menu
    local user_input
    read -p "$(echo -e ${MAGENTA}"Pilih nomor environment: "${NC})" user_input

    if [ -z "$user_input" ]; then
        echo -e "${RED}❌ Pilihan tidak boleh kosong${NC}"
        exit 1
    fi

    local total_files=${#sorted_env_files[@]}
    local selected_indices=($(parse_selection "$user_input" "$total_files"))

    if [ ${#selected_indices[@]} -eq 0 ]; then
        echo -e "${RED}❌ Nomor pilihan tidak valid atau di luar jangkauan${NC}"
        exit 1
    fi

    local is_mass=false
    if [ ${#selected_indices[@]} -gt 1 ]; then
        is_mass=true
    fi

    clear
    banner

    local action
    if [ "$is_mass" = true ]; then
        echo -e "${CYAN}Operasi Massal Terpilih untuk ${WHITE}${#selected_indices[@]}${CYAN} Layanan:${NC}"
        for idx in "${selected_indices[@]}"; do
            local file_path="${sorted_env_files[$((idx-1))]}"
            local name_only="$(basename "$file_path")"
            local base_name="${name_only%.*}"
            echo -e " ${YELLOW}-${NC} ${WHITE}vipbot_${base_name}${NC}"
        done
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${WHITE}1.${NC} ${BLUE}Pasang / Perbarui Layanan Massal (Mass Install)${NC}"
        echo -e "${WHITE}2.${NC} ${GREEN}Mulai Layanan Massal (Mass Start)${NC}"
        echo -e "${WHITE}3.${NC} ${YELLOW}Hentikan Layanan Massal (Mass Stop)${NC}"
        echo -e "${WHITE}4.${NC} ${BLUE}Restart Layanan Massal (Mass Restart)${NC}"
        echo -e "${WHITE}5.${NC} ${ORANGE}Lihat Status Singkat Massal (Mass Status)${NC}"
        echo -e "${WHITE}6.${NC} ${RED}Hapus Layanan Massal (Mass Uninstall)${NC}"
        echo -e "${WHITE}7.${NC} ${WHITE}Keluar${NC}"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        read -p "$(echo -e ${MAGENTA}"Pilih tindakan (1-7): "${NC})" action
    else
        local SELECTED_ENV="${sorted_env_files[$((selected_indices[0]-1))]}"
        local SELECTED_NAME="$(basename "$SELECTED_ENV")"
        local BASE_NAME="${SELECTED_NAME%.*}"
        local SERVICE_NAME="vipbot_${BASE_NAME}"

        echo -e "${CYAN}Layanan Terpilih: ${WHITE}${SERVICE_NAME}${NC}"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${WHITE}1.${NC} ${BLUE}Pasang / Perbarui Layanan (Install)${NC}"
        echo -e "${WHITE}2.${NC} ${GREEN}Mulai Layanan (Start)${NC}"
        echo -e "${WHITE}3.${NC} ${YELLOW}Hentikan Layanan (Stop)${NC}"
        echo -e "${WHITE}4.${NC} ${BLUE}Restart Layanan (Restart)${NC}"
        echo -e "${WHITE}5.${NC} ${ORANGE}Lihat Status Rinci (Status/Details)${NC}"
        echo -e "${WHITE}6.${NC} ${MAGENTA}Lihat Log Sistem (Journal/Logs)${NC}"
        echo -e "${WHITE}7.${NC} ${RED}Hapus Layanan (Uninstall)${NC}"
        echo -e "${WHITE}8.${NC} ${WHITE}Keluar${NC}"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        read -p "$(echo -e ${MAGENTA}"Pilih tindakan (1-8): "${NC})" action
    fi

    if [ "$is_mass" = true ]; then
        case "$action" in
            1)
                local DB_KEY
                read -s -p "$(echo -e ${MAGENTA}"Masukkan kunci enkripsi massal (DB_KEY): "${NC})" DB_KEY
                echo
                if [ -z "$DB_KEY" ]; then
                    echo -e "${RED}❌ Kunci enkripsi massal wajib diisi!${NC}"
                    exit 1
                fi
                
                echo -e "${BLUE}Menulis berkas unit systemd secara massal...${NC}"
                for idx in "${selected_indices[@]}"; do
                    local file_path="${sorted_env_files[$((idx-1))]}"
                    local name_only="$(basename "$file_path")"
                    local base_name="${name_only%.*}"
                    local service_name="vipbot_${base_name}"
                    local service_file="/etc/systemd/system/${service_name}.service"
                    
                    cat <<EOF > "$service_file"
[Unit]
Description=VipBot - ${base_name}
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${PROJECT_DIR}
Environment="DB_KEY=${DB_KEY}"
Environment="PATH=${PROJECT_DIR}/env/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=${VENV_PYTHON} -u main.py --key ${DB_KEY} --env ${file_path}
Restart=always
RestartSec=5
Nice=10
IOSchedulingClass=best-effort
IOSchedulingPriority=7

[Install]
WantedBy=multi-user.target
EOF
                    chmod 600 "$service_file"
                    systemctl enable "$service_name" >/dev/null 2>&1
                    echo -e " ${GREEN}✔${NC} Terkonfigurasi: ${WHITE}${service_name}${NC}"
                done
                
                systemctl daemon-reload
                echo -e "${BLUE}Menjalankan seluruh layanan baru...${NC}"
                for idx in "${selected_indices[@]}"; do
                    local file_path="${sorted_env_files[$((idx-1))]}"
                    local name_only="$(basename "$file_path")"
                    local base_name="${name_only%.*}"
                    local service_name="vipbot_${base_name}"
                    systemctl start "$service_name"
                    sleep 0.5
                done
                echo -e "${GREEN}✔ Seluruh layanan terpilih berhasil dipasang dan dijalankan.${NC}"
                ;;
            2)
                echo -e "${GREEN}Memulai layanan terpilih...${NC}"
                for idx in "${selected_indices[@]}"; do
                    local file_path="${sorted_env_files[$((idx-1))]}"
                    local name_only="$(basename "$file_path")"
                    local base_name="${name_only%.*}"
                    local service_name="vipbot_${base_name}"
                    systemctl start "$service_name"
                    echo -e " ${GREEN}✔${NC} Memulai: ${WHITE}${service_name}${NC}"
                    sleep 0.5
                done
                ;;
            3)
                echo -e "${YELLOW}Menghentikan layanan terpilih...${NC}"
                for idx in "${selected_indices[@]}"; do
                    local file_path="${sorted_env_files[$((idx-1))]}"
                    local name_only="$(basename "$file_path")"
                    local base_name="${name_only%.*}"
                    local service_name="vipbot_${base_name}"
                    systemctl stop "$service_name"
                    echo -e " ${YELLOW}✔${NC} Menghentikan: ${WHITE}${service_name}${NC}"
                done
                ;;
            4)
                echo -e "${BLUE}Merestart layanan terpilih...${NC}"
                for idx in "${selected_indices[@]}"; do
                    local file_path="${sorted_env_files[$((idx-1))]}"
                    local name_only="$(basename "$file_path")"
                    local base_name="${name_only%.*}"
                    local service_name="vipbot_${base_name}"
                    systemctl restart "$service_name"
                    echo -e " ${GREEN}✔${NC} Merestart: ${WHITE}${service_name}${NC}"
                    sleep 0.5
                done
                ;;
            5)
                echo -e "${CYAN}Status Singkat Layanan Terpilih:${NC}"
                echo -e "${GRAY}----------------------------------------------------------------${NC}"
                for idx in "${selected_indices[@]}"; do
                    local file_path="${sorted_env_files[$((idx-1))]}"
                    local name_only="$(basename "$file_path")"
                    local base_name="${name_only%.*}"
                    local service_name="vipbot_${base_name}"
                    local status_info
                    if systemctl is-active --quiet "$service_name" 2>/dev/null; then
                        status_info="${GREEN}ACTIVE (ON)${NC}"
                    else
                        status_info="${RED}INACTIVE (OFF)${NC}"
                    fi
                    printf " ${YELLOW}-${NC} ${WHITE}%-30s${NC} ${MAGENTA}: %b\n" "${service_name}" "${status_info}"
                done
                echo -e "${GRAY}----------------------------------------------------------------${NC}"
                ;;
            6)
                echo -e "${RED}Hapus layanan terpilih...${NC}"
                for idx in "${selected_indices[@]}"; do
                    local file_path="${sorted_env_files[$((idx-1))]}"
                    local name_only="$(basename "$file_path")"
                    local base_name="${name_only%.*}"
                    local service_name="vipbot_${base_name}"
                    systemctl stop "$service_name" >/dev/null 2>&1
                    systemctl disable "$service_name" >/dev/null 2>&1
                    rm -rf "/etc/systemd/system/${service_name}.service"
                    echo -e " ${RED}✔${NC} Dihapus: ${WHITE}${service_name}${NC}"
                done
                systemctl daemon-reload
                echo -e "${GREEN}✔ Seluruh layanan terpilih berhasil dihapus dari sistem.${NC}"
                ;;
            *)
                echo -e "${BLUE}Keluar.${NC}"
                exit 0
                ;;
        esac
    else
        case "$action" in
            1)
                local DB_KEY
                read -s -p "$(echo -e ${MAGENTA}"Masukkan kunci enkripsi (DB_KEY): "${NC})" DB_KEY
                echo
                if [ -z "$DB_KEY" ]; then
                    echo -e "${RED}❌ Kunci enkripsi wajib diisi!${NC}"
                    exit 1
                fi
                
                local SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
                
                echo -e "${BLUE}Membuat berkas unit systemd...${NC}"
                
                cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=VipBot - ${BASE_NAME}
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${PROJECT_DIR}
Environment="DB_KEY=${DB_KEY}"
Environment="PATH=${PROJECT_DIR}/env/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=${VENV_PYTHON} -u main.py --key ${DB_KEY} --env ${SELECTED_ENV}
Restart=always
RestartSec=5
Nice=10
IOSchedulingClass=best-effort
IOSchedulingPriority=7

[Install]
WantedBy=multi-user.target
EOF
                chmod 600 "$SERVICE_FILE"
                systemctl daemon-reload
                systemctl enable "$SERVICE_NAME"
                systemctl start "$SERVICE_NAME"
                
                echo -e "${GREEN}✔ Layanan ${SERVICE_NAME} berhasil dipasang dan dijalankan.${NC}"
                ;;
            2)
                systemctl start "$SERVICE_NAME"
                echo -e "${GREEN}✔ Layanan ${SERVICE_NAME} telah dimulai.${NC}"
                ;;
            3)
                systemctl stop "$SERVICE_NAME"
                echo -e "${YELLOW}✔ Layanan ${SERVICE_NAME} telah dihentikan.${NC}"
                ;;
            4)
                systemctl restart "$SERVICE_NAME"
                echo -e "${GREEN}✔ Layanan ${SERVICE_NAME} telah dimuat ulang (restarted).${NC}"
                ;;
            5)
                echo -e "${CYAN}Informasi Status Rinci:${NC}"
                systemctl status "$SERVICE_NAME"
                ;;
            6)
                journalctl -u "$SERVICE_NAME" -f -a -o cat --no-pager
                ;;
            7)
                systemctl stop "$SERVICE_NAME" 2>/dev/null
                systemctl disable "$SERVICE_NAME" 2>/dev/null
                rm -rf "/etc/systemd/system/${SERVICE_NAME}.service"
                systemctl daemon-reload
                echo -e "${RED}✔ Layanan ${SERVICE_NAME} berhasil dihapus dari sistem.${NC}"
                ;;
            *)
                echo -e "${BLUE}Keluar.${NC}"
                exit 0
                ;;
        esac
    fi
}

main
