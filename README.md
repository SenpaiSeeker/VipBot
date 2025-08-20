# 🚀 VVIP Multi-Bot Manager

Selamat datang di **VVIP Multi-Bot Manager**, sebuah platform Telegram canggih yang dirancang tidak hanya untuk mengelola satu grup VVIP, tetapi untuk **membuat, mengelola, dan menskalakan seluruh armada bot VVIP**. Bot utama berfungsi sebagai pusat kontrol (*control panel*), memungkinkan *Owner Utama* untuk memberikan akses kepada pengguna lain untuk meluncurkan bot VVIP mereka sendiri. Setiap bot yang dibuat beroperasi secara mandiri, lengkap dengan masa aktif, panel kontrol pribadi, dan sistem pembayaran yang terisolasi.

Platform ini adalah solusi *all-in-one* bagi siapa saja yang ingin membangun bisnis komunitas berbayar di Telegram dengan model multi-tenant.

## ⭐ Fitur Unggulan

### 🤖 Sistem Multi-Bot Canggih
- **Bot Induk (Main Bot)**: Berfungsi sebagai pusat manajemen untuk membuat, memantau, dan mengelola semua bot VVIP yang ada di dalam sistem.
- **Pembuatan Bot oleh Pengguna**: *Owner Utama* dapat mendelegasikan hak pembuatan bot kepada pengguna terpercaya melalui perintah `/akses`.
- **Manajemen Bot Individual**: Setiap bot yang dibuat adalah entitas independen dengan database, daftar VVIP, daftar member, dan API Keys (Violet & Gemini) yang terpisah.
- **Masa Aktif Bot**: Setiap bot yang dibuat otomatis mendapatkan masa aktif 30 hari, yang dapat diperpanjang melalui permintaan kepada *Owner Utama*.
- **Panel Kontrol Terpusat (`/allbots`)**: *Owner Utama* memiliki pandangan *bird's-eye* dari semua bot yang aktif, lengkap dengan informasi pemilik dan sisa masa aktif.
- **Manajemen Durasi Manual (`/extend`)**: *Owner Utama* dapat menambah atau mengurangi masa aktif bot manapun secara manual, memberikan fleksibilitas penuh dalam manajemen.

### 💼 Manajemen VVIP & Paket
- **Panel Kontrol Intuitif**: Tambah, hapus, dan kelola paket VVIP dengan mudah melalui antarmuka berbasis tombol di dalam **"⚙️ Panel Pengaturan ⚙️"**.
- **Harga Dinamis**: Atur harga normal dan harga promosi untuk setiap paket, memungkinkan strategi penjualan yang fleksibel.
- **Teks yang Dapat Disesuaikan**: Personalisasi teks deskripsi untuk setiap paket dan promo untuk menarik lebih banyak pelanggan.

### 💳 Pembayaran dan Akses Otomatis
- **Integrasi QRIS (VioletMediaPay)**: Terhubung secara *seamless* dengan VioletMediaPay untuk menghasilkan kode QRIS yang unik untuk setiap transaksi, mendukung semua e-wallet dan m-banking di Indonesia.
- **Verifikasi Otomatis**: Bot secara mandiri memverifikasi status pembayaran setiap 15 detik dan memberikan akses instan begitu pembayaran berhasil. Tidak perlu lagi konfirmasi manual.
- **Konten Terlindungi**: Tautan undangan grup dikirim sebagai pesan yang dilindungi (*protected content*) untuk mencegah penerusan dan penyalahgunaan.
- **Dukungan Donasi (Telegram Stars ⭐)**: Terima dukungan finansial dari pengguna melalui Telegram Stars. Notifikasi instan dikirim ke pemilik bot, lengkap dengan tombol untuk *refund* jika diperlukan.

### 👥 Manajemen Anggota yang Komprehensif
- **Daftar Member VVIP**: Lihat daftar lengkap semua anggota yang telah bergabung melalui bot, lengkap dengan detail paket, tanggal bergabung, dan tombol untuk menendang (*kick*) anggota.
- **Cek Member Aktif Real-time**: Verifikasi daftar anggota langsung dari grup/channel target untuk memastikan tidak ada penyusup atau anggota yang tidak terdaftar.

### 🛠️ Peralatan Admin yang Kuat
- **Fitur Broadcast**: Kirim pesan massal ke semua pengguna yang pernah berinteraksi dengan bot Anda, cocok untuk pengumuman atau promosi.
- **Manajemen API per-Bot**: Setiap pemilik bot dapat mengatur API Key Violet (untuk pembayaran) dan Gemini (untuk AI) mereka sendiri, memastikan layanan tetap terisolasi dan mandiri.
- **Backup & Restore Database**: Bot secara otomatis mengirimkan file backup `database.zip` secara berkala. Pulihkan seluruh data bot dengan mudah menggunakan perintah `/restore`.
- **Eksekusi Kode (`/eval`)**: Fitur canggih untuk debugging dan eksekusi kode Python secara *real-time* (hanya untuk *Owner Utama*).

### 🎨 Kustomisasi & Personalisasi
- **Dukungan Multi-Bahasa**: Bot mendukung Bahasa Indonesia, Inggris, dan Jepang. Pengguna dapat memilih bahasa pilihan mereka melalui menu pengaturan.
- **Kustomisasi Tampilan**: Pemilik bot dapat dengan mudah mengubah foto dan teks sambutan (`/start`) melalui panel pengaturan, memberikan identitas unik pada setiap bot. Perintah `/empty` tersedia untuk kembali ke pengaturan default.
- **Asisten AI (Google Gemini)**: Integrasi dengan Google Gemini menghadirkan fitur hiburan "Cek Khodam" dan *chatbot* cerdas yang dapat menjawab pertanyaan pengguna seputar fungsionalitas bot, harga paket, dan lainnya, mengurangi beban support manual.

## 🚀 Pengaturan dan Instalasi

Ikuti langkah-langkah ini untuk menjalankan platform bot Anda dari awal hingga siap digunakan.

### 1. Prasyarat
- Python 3.8 atau lebih tinggi.
- Token Bot Telegram untuk **Bot Utama (Induk)**. Dapatkan dari [@BotFather](https://t.me/BotFather).
- API ID dan API Hash dari [my.telegram.org](https://my.telegram.org).

### 2. Kloning Repositori
Pertama, kloning repositori ini ke mesin lokal atau server Anda.
```bash
git clone https://github.com/your-username/VipBot-main.git
cd VipBot-main
```

### 3. Instalasi Dependensi
Instal semua pustaka Python yang diperlukan menggunakan file `requirements.txt`.
```bash
pip3 install -r requirements.txt
```

### 4. Konfigurasi Menggunakan Skrip `config.sh`
Langkah ini adalah untuk membuat file environment (`.env`) yang berisi kredensial Anda.

1.  Jalankan skrip `config.sh` di terminal Anda:
    ```bash
    bash config.sh
    ```

2.  Skrip akan memandu Anda untuk memasukkan informasi berikut:
    - **API_ID** & **API_HASH** Anda.
    - **BOT_TOKEN** untuk bot utama/induk.
    - **OWNER_ID** numerik Anda (dapatkan dari [@userinfobot](https://t.me/userinfobot)).
    - **Nama file database** (default: `vvip_database`).
    - **Nama file environment** yang ingin dibuat (default: `vvip.env`).

    **Penting:** Skrip ini tidak lagi meminta Kunci Enkripsi. Kunci tersebut akan dimasukkan secara aman pada saat bot dijalankan.

### 5. Menjalankan Bot Menggunakan Skrip `run.sh`
Ini adalah cara yang direkomendasikan dan paling aman untuk memulai bot Anda.

1.  **Jadikan skrip `run.sh` executable** (hanya perlu dilakukan sekali):
    ```bash
    chmod +x run.sh
    ```

2.  **Jalankan bot**:
    ```bash
    ./run.sh
    ```

3.  Skrip akan meminta dua hal:
    - **Nama file environment**: Tekan Enter untuk menggunakan default (`vvip.env`) atau ketik nama file lain.
    - **Kunci enkripsi rahasia**: Ketik kunci rahasia Anda. **Input tidak akan terlihat di layar** demi keamanan.

Setelah Anda memasukkan informasi tersebut, bot akan dimulai dengan banner selamat datang di terminal.

## 📖 Panduan Penggunaan

### 👑 Untuk Owner Utama (Super Admin)
Anda adalah administrator tertinggi dengan kontrol penuh atas seluruh sistem.

1.  **Mulai Bot**: Kirim `/start` ke bot utama Anda.
2.  **Memberikan Akses**: Untuk mengizinkan pengguna lain membuat bot, gunakan perintah:
    ```
    /akses <user_id atau @username>
    ```
    Ini akan membuka panel untuk memberi atau mencabut hak "Create Bot".
3.  **Melihat Semua Bot**: Gunakan perintah `/allbots` untuk melihat daftar semua bot yang telah dibuat, lengkap dengan ID, pemilik, dan sisa masa aktif. Panel ini memiliki navigasi halaman.
4.  **Mengatur Durasi Bot**: Gunakan perintah `/extend` untuk menambah atau mengurangi masa aktif bot manapun secara manual.
    ```
    /extend <bot_id> <jumlah_hari>
    # Contoh: /extend 123456789 30 (menambah 30 hari)
    # Contoh: /extend 123456789 -10 (mengurangi 10 hari)
    ```
5.  **Menyetujui Perpanjangan**: Ketika seorang pemilik bot meminta perpanjangan, Anda akan menerima pesan di chat pribadi dengan tombol untuk menyetujui atau menolak.
6.  **Backup & Restore**: Bot akan secara otomatis mengirimkan file backup `database.zip` secara berkala. Untuk memulihkan, balas file tersebut dengan perintah `/restore`. **PENTING: Restart bot setelah restore berhasil.**

### 👤 Untuk Pemilik Bot (Pengguna)
Setelah mendapatkan akses dari *Owner Utama*, Anda dapat membuat dan mengelola bot VVIP Anda sendiri.

1.  **Membuat Bot**: Tekan tombol **"🤖 Buat Bot"** di bot utama dan ikuti instruksi untuk memasukkan `API_ID`, `API_HASH`, dan `BOT_TOKEN` Anda. Setelah berhasil, bot Anda akan langsung aktif selama 30 hari.
2.  **Mengelola Bot**:
    - Mulai bot **pribadi Anda** dengan perintah `/start`.
    - Anda akan melihat menu **"⚙️ Panel Pengaturan ⚙️"**. Di sinilah Anda mengelola semua aspek bot Anda: menambah/menghapus paket VVIP, mengecek anggota, mengatur API keys, mengubah foto/teks start, dan melakukan broadcast **hanya untuk pengguna bot Anda**.
3.  **Meminta Perpanjangan**:
    - Di bot **utama**, tekan tombol **"📦 Bot Saya"**.
    - Pilih bot Anda dari daftar, lalu klik **"➕ Minta Perpanjangan"**. Permintaan akan dikirimkan ke *Owner Utama* untuk disetujui.

### 👨‍👩‍👧‍👦 Untuk Pengguna Akhir (Pelanggan)
Pelanggan akan berinteraksi dengan bot-bot VVIP yang telah Anda atau pengguna lain buat.

1.  **Mulai Bot**: Pengguna mengirim `/start`.
2.  **Pilih Bahasa**: Pengguna dapat memilih bahasa melalui tombol "🌐 Bahasa".
3.  **Lihat Paket**: Klik **"📚 Lihat Daftar VVIP 📚"**.
4.  **Pembayaran**: Setelah memilih paket, pengguna klik "Bayar", menerima QRIS, dan melakukan pembayaran.
5.  **Akses Grup**: Setelah pembayaran terkonfirmasi, bot akan otomatis mengirimkan link undangan grup dalam pesan yang tidak bisa diteruskan.

#### ⭐️ Dibuat oleh: [@NorSodikin](https://t.me/NorSodikin)
