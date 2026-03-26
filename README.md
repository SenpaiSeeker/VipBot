# 🚀 VVIP Multi-Bot Manager

Selamat datang di **VVIP Multi-Bot Manager**, sebuah platform Telegram canggih yang dirancang tidak hanya untuk mengelola satu grup VVIP, tetapi untuk **membuat, mengelola, dan menskalakan seluruh armada bot VVIP**. Bot utama berfungsi sebagai pusat kontrol (*control panel*), memungkinkan *Owner Utama* untuk memberikan akses kepada pengguna lain untuk meluncurkan bot VVIP mereka sendiri. Setiap bot yang dibuat beroperasi secara mandiri, lengkap dengan masa aktif, panel kontrol pribadi, dan sistem pembayaran yang terisolasi.

Platform ini adalah solusi *all-in-one* bagi siapa saja yang ingin membangun bisnis komunitas berbayar di Telegram dengan model multi-tenant.

## ⭐ Fitur Unggulan

### 🤖 Sistem Multi-Bot Canggih
- **Bot Induk (Main Bot)**: Berfungsi sebagai pusat manajemen untuk membuat, memantau, dan mengelola semua bot VVIP yang ada di dalam sistem.
- **Pembuatan Bot oleh Pengguna**: *Owner Utama* dapat mendelegasikan hak pembuatan bot kepada pengguna terpercaya melalui perintah `/akses`.
- **Manajemen Bot Individual**: Setiap bot yang dibuat adalah entitas independen dengan database, daftar VVIP, dan API Keys yang terpisah.
- **Masa Aktif Bot**: Setiap bot yang dibuat otomatis mendapatkan masa aktif 30 hari, yang dapat diperpanjang.
- **Panel Kontrol Terpusat (`/allbots`)**: *Owner Utama* memiliki pandangan lengkap dari semua bot yang aktif.
- **Manajemen Durasi Manual (`/extend`)**: *Owner Utama* dapat mengubah masa aktif bot manapun.
- **Dashboard Global (`/dashboard`)**: *Owner Utama* dapat melihat statistik vital platform, termasuk total bot, total pengguna, dan status kesehatan server (CPU, RAM, Disk) secara real-time.

### 💼 Manajemen VVIP & Langganan
- **Model Berlangganan (Subscription)**: Atur durasi keanggotaan untuk setiap paket VVIP (misal: 7, 30, 90 hari). Bot akan secara otomatis menendang anggota yang langganannya telah berakhir.
- **Pengingat Perpanjangan Otomatis**: Bot akan mengirimkan notifikasi perpanjangan kepada anggota beberapa hari sebelum masa langganan habis.
- **Harga Dinamis**: Atur harga normal dan harga promosi untuk setiap paket.
- **Teks yang Dapat Disesuaikan**: Personalisasi teks deskripsi untuk setiap paket.

### 💳 Pembayaran & Marketing Tools
- **Integrasi QRIS (VioletMediaPay)**: Terhubung secara *seamless* dengan VioletMediaPay untuk pembayaran otomatis.
- **Sistem Kode Kupon**: Pemilik bot dapat membuat kode kupon (persentase atau potongan harga tetap) dengan batasan penggunaan dan tanggal kedaluwarsa untuk mendorong penjualan.
- **Verifikasi Otomatis & Keamanan Link**:
    - Bot memverifikasi pembayaran dan memberikan akses instan.
    - Link undangan dikirim sebagai pesan yang dilindungi (*protected content*).
    - **Verifikasi Join**: Bot akan memantau apakah pengguna sudah bergabung. Setelah berhasil bergabung, pesan berisi link akan **otomatis dihapus** untuk mencegah penyebaran. Jika pengguna tidak bergabung dalam 10 menit, link akan kedaluwarsa dan pesan dihapus.
- **Dukungan Donasi (Telegram Stars ⭐)**: Terima dukungan finansial melalui Telegram Stars.

### 👥 Manajemen Anggota yang Komprehensif
- **Daftar Member VVIP**: Lihat daftar lengkap semua anggota yang telah bergabung, lengkap dengan detail paket, tanggal bergabung, dan tanggal kedaluwarsa.
- **Cek Member Aktif Real-time**: Verifikasi daftar anggota langsung dari grup/channel target untuk memastikan tidak ada penyusup.

### 🛠️ Peralatan Admin yang Kuat
- **Fitur Broadcast Fleksibel**:
    - **Pemilik Bot**: Kirim pesan massal ke semua pengguna botnya.
    - **Owner Utama**: Kirim pesan broadcast ke semua *pemilik bot* di platform melalui perintah `/broadcast_owners`.
- **Manajemen API per-Bot**: Setiap pemilik bot mengatur API payment (Saweria) mereka sendiri.
- **Backup & Restore Database**: Backup otomatis berkala dan pemulihan data yang mudah.
- **Eksekusi Kode (`/eval`)**: Fitur canggih untuk debugging (hanya *Owner Utama*).

### 🎨 Kustomisasi & Personalisasi
- **Bahasa Indonesia**: Seluruh antarmuka bot menggunakan Bahasa Indonesia.
- **Kustomisasi Tampilan**: Ubah foto dan teks sambutan (`/start`) dengan mudah.

## 🚀 Pengaturan dan Instalasi

Ikuti langkah-langkah ini untuk menjalankan platform bot Anda dari awal hingga siap digunakan.

### 1. Prasyarat
- Python 3.8 atau lebih tinggi.
- Token Bot Telegram untuk **Bot Utama (Induk)**. Dapatkan dari [@BotFather](https://t.me/BotFather).
- API ID dan API Hash dari [my.telegram.org](https://my.telegram.org).

### 2. Kloning Repositori
```bash
git clone https://github.com/your-username/VipBot-main.git
cd VipBot-main
```

### 3. Instalasi Dependensi
```bash
pip3 install -r requirements.txt
```

### 4. Konfigurasi Menggunakan Skrip `config.sh`
1.  Jalankan skrip `config.sh`:
    ```bash
    bash config.sh
    ```
2.  Skrip akan memandu Anda memasukkan:
    - **API_ID** & **API_HASH**.
    - **BOT_TOKEN** untuk bot utama.
    - **OWNER_ID** numerik Anda.
    - Nama file database (default: `vvip_database`).
    - Nama file environment (default: `vvip.env`).

### 5. Menjalankan Bot Menggunakan Skrip `run.sh`
1.  Jadikan skrip `run.sh` executable (hanya sekali):
    ```bash
    chmod +x run.sh
    ```
2.  Jalankan bot:
    ```bash
    ./run.sh
    ```
3.  Skrip akan meminta:
    - Nama file environment (tekan Enter untuk default).
    - Kunci enkripsi rahasia (input tidak akan terlihat).

Bot akan dimulai dengan banner selamat datang di terminal.

## Jika terjadi error silakan instal 
```bash
sudo apt-get install -y libzbar0 ffmpeg 
```

## 📖 Panduan Penggunaan

### 👑 Untuk Owner Utama (Super Admin)
- `/start`: Memulai interaksi.
- `/akses <user_id>`: Memberikan hak kepada pengguna untuk membuat bot.
- `/allbots`: Melihat semua bot yang aktif di sistem.
- `/extend <bot_id> <jumlah_hari>`: Mengatur masa aktif bot.
- `/dashboard`: Melihat statistik lengkap platform dan kesehatan server.
- `/broadcast_owners <pesan>`: Mengirim pesan ke semua pemilik bot.
- `/restore`: Balas ke file `database.zip` untuk memulihkan data.

### 👤 Untuk Pemilik Bot (Pengguna)
- **Buat Bot**: Tekan tombol **"🤖 Buat Bot"** di bot utama.
- **Panel Pengaturan**: Di bot pribadi Anda, gunakan **"⚙️ Panel Pengaturan ⚙️"** untuk:
    - Menambah/menghapus paket VVIP (sekarang dengan durasi langganan).
    - Mengelola kupon diskon.
    - Mengecek anggota, broadcast, mengatur API, dll.
- **Minta Perpanjangan**: Di bot utama, masuk ke menu **"📦 Bot Saya"** untuk meminta perpanjangan masa aktif bot.

### 👨‍👩‍👧‍👦 Untuk Pengguna Akhir (Pelanggan)
- `/start`: Memulai bot VVIP.
- **Lihat Paket**: Klik **"📚 Lihat Daftar VVIP 📚"**.
- **Pembayaran**: Pilih paket, gunakan kupon (jika ada), bayar dengan QRIS.
- **Akses Grup**: Link undangan otomatis dikirim setelah pembayaran sukses. Link ini akan dihapus setelah Anda bergabung atau setelah 10 menit.

#### ⭐️ Dibuat oleh: [@NorSodikin](https://t.me/NorSodikin)
