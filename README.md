# 🚀 VVIP Multi-Bot Manager

Selamat datang di **VVIP Multi-Bot Manager**, sebuah platform Telegram canggih yang dirancang tidak hanya untuk mengelola satu grup VVIP, tetapi untuk **membuat, mengelola, dan menskalakan seluruh armada bot VVIP**. Bot utama berfungsi sebagai pusat kontrol (*control panel*), memungkinkan *Owner Utama* untuk memberikan akses kepada pengguna lain untuk meluncurkan bot VVIP mereka sendiri. Setiap bot yang dibuat beroperasi secara mandiri, lengkap dengan masa aktif, panel kontrol pribadi, dan sistem pembayaran yang terisolasi.

Platform ini adalah solusi *all-in-one* bagi siapa saja yang ingin membangun bisnis komunitas berbayar di Telegram dengan model multi-tenant.

## ⭐ Fitur Unggulan

### 🤖 Sistem Multi-Bot Canggih
- **Bot Induk (Main Bot)**: Berfungsi sebagai pusat manajemen untuk membuat, memantau, dan mengelola semua bot VVIP yang ada di dalam sistem.
- **Pembuatan Bot oleh Pengguna**: *Owner Utama* dapat mendelegasikan hak pembuatan bot kepada pengguna terpercaya melalui perintah `/akses`.
- **Manajemen Bot Individual**: Setiap bot yang dibuat adalah entitas independen dengan database, daftar VVIP, dan API Keys yang terpisah.
- **Masa Aktif Bot**: Setiap bot yang dibuat otomatis mendapatkan masa aktif 30 hari, yang dapat diperpanjang. Pengingat otomatis dikirim ke pemilik bot pada H-10, H-5, H-3, dan H-1. Bot yang sudah kedaluwarsa otomatis dihentikan dan dihapus dari sistem.
- **Panel Kontrol Terpusat (`/allbots`)**: *Owner Utama* memiliki pandangan lengkap dari semua bot yang aktif.
- **Atur Masa Aktif (`/extend`)**: *Owner Utama* dapat menambah **atau mengurangi** masa aktif bot langsung dari panel tombol (bulan 1–12, 1 bulan = 30 hari).
- **Daftar Owner Bot (`/botowners`)**: Tabel lengkap berisi bot, owner, token, tanggal kedaluwarsa, dan jumlah penjualan (*Terjual*).
- **Dashboard Global (`/dashboard`)**: *Owner Utama* dapat melihat statistik vital platform, termasuk total bot, total pengguna, dan status kesehatan server (CPU, RAM, Disk) secara real-time.
- **Watchdog Token**: Setiap 15 menit sistem memeriksa token seluruh bot berjalan. Bot dengan token tidak valid/revoked/diblokir otomatis dihentikan (data tetap aman) dan *Owner Utama* menerima notifikasi.
- **Perlindungan FloodWait**: Bot yang terkena `FloodWait` tidak langsung dijalankan ulang; sistem menyimpan waktu tunggu di database dan menampilkan estimasi di proses login, sehingga tidak memicu pembatasan berulang.

### 💼 Manajemen VVIP & Langganan
- **Model Berlangganan (Subscription)**: Atur durasi keanggotaan untuk setiap paket VVIP (misal: 7, 30, 90 hari). Bot akan secara otomatis menendang anggota yang langganannya telah berakhir.
- **Pengingat Perpanjangan Otomatis**: Bot akan mengirimkan notifikasi perpanjangan kepada anggota beberapa hari sebelum masa langganan habis.
- **Harga Dinamis**: Atur harga normal dan harga promosi untuk setiap paket.
- **Teks yang Dapat Disesuaikan**: Personalisasi teks deskripsi untuk setiap paket.
- **Ambil Semua VIP**: Beli seluruh paket sekaligus dalam satu transaksi (tombol otomatis disembunyikan jika paket hanya satu).
- **Ambil Sebagian VIP**: Pelanggan memilih sendiri beberapa paket, membayar **sekali** via QRIS, lalu menerima link akses **satu per satu** untuk tiap paket lengkap dengan verifikasi join.

### 💳 Pembayaran & Marketing Tools
- **Integrasi QRIS (Saweria)**: Setiap bot terhubung ke akun **Saweria** milik pemiliknya sendiri. Username Saweria diatur melalui panel pengaturan bot; pembuatan QRIS dan verifikasi pembayaran berjalan otomatis.
- **Sistem Kode Kupon**: Pemilik bot dapat membuat kode kupon (persentase atau potongan harga tetap) dengan batasan penggunaan dan tanggal kedaluwarsa untuk mendorong penjualan.
- **Verifikasi Otomatis & Keamanan Link**:
    - Bot memverifikasi pembayaran dan memberikan akses instan.
    - Link undangan dikirim sebagai pesan yang dilindungi (*protected content*).
    - **Verifikasi Join**: Bot akan memantau apakah pengguna sudah bergabung. Setelah berhasil bergabung, pesan berisi link akan **otomatis dihapus** untuk mencegah penyebaran. Jika pengguna tidak bergabung dalam 10 menit, link akan kedaluwarsa dan pesan dihapus.
- **Penghitung Penjualan & Bagi Hasil Otomatis**: Setiap penjualan VIP yang lunas dihitung per bot. Pada penjualan kelipatan 10 (ke-10, ke-20, dst.), pembayaran diarahkan ke akun Saweria *Owner Utama* dan notifikasinya dikirim ke *Owner Utama* (tidak dicatat sebagai pemasukan bot pemilik). Hitungan tidak pernah di-reset dan ikut menghitung riwayat penjualan lama.
- **Mode Block (`/block on|off`)**: Menonaktifkan pencatatan pemasukan bot, mengalihkan seluruh notifikasi pembelian VIP ke *Owner Utama*, dan memakai akun Saweria *Owner Utama*. Pembelian akses bot tidak terpengaruh.
- **Template Notifikasi Pemasukan**: Format notifikasi pemasukan dapat diubah bebas memakai 24 variabel (data pembeli, paket, pembayaran, bot, dll.).
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
- **Tampilan Rich Message**: Seluruh teks memakai tabel rapi dan premium emoji, termasuk tombol beremoji.
- **Kustomisasi Tampilan**: Ubah foto dan teks sambutan (`/start`) dengan mudah.

## 🚀 Pengaturan dan Instalasi

Ikuti langkah-langkah ini untuk menjalankan platform bot Anda dari awal hingga siap digunakan.

### 1. Prasyarat
- Python 3.10+ (disarankan 3.12) dan akses **root** (untuk manajemen layanan systemd).
- Token Bot Telegram untuk **Bot Utama (Induk)**. Dapatkan dari [@BotFather](https://t.me/BotFather).
- API ID dan API Hash dari [my.telegram.org](https://my.telegram.org).
- Paket sistem pendukung:
```bash
sudo apt-get install -y libzbar0 ffmpeg
```

### 2. Kloning Repositori
```bash
git clone https://github.com/your-username/VipBot-main.git
cd VipBot-main
```

### 3. Instalasi Dependensi
```bash
python3 -m venv env
env/bin/pip install -r requirements.txt
env/bin/playwright install chromium
```
> `playwright install chromium` wajib dijalankan agar gambar QRIS dapat dibuat.

### 4. Konfigurasi Environment
Buat satu file `.env` di dalam folder `envpath/` untuk setiap layanan yang ingin dijalankan, misalnya `envpath/vvip.env`:
```env
API_ID=123456
API_HASH=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BOT_TOKEN=123456:ABC-DEF...
OWNER_ID=123456789
DB_NAME=vvip_database
BACKUP_BOT=123456:ABC-DEF...
```
- `DB_NAME` menentukan nama file database lokal terenkripsi (gunakan nama berbeda per environment).
- Satu file `.env` = satu layanan `vipbot_<nama>`.

### 5. Menjalankan Bot Menggunakan Skrip `run.sh`
```bash
sudo bash run.sh
```
Menu interaktif akan menampilkan seluruh environment di `envpath/` beserta statusnya. Anda dapat memilih satu atau beberapa environment (misal `1,3,5-8` atau `all`) lalu:
- **Install**: membuat unit systemd `vipbot_<nama>` (meminta `DB_KEY` untuk enkripsi database).
- **Start / Stop / Restart**.
- **Status / Logs**.
- **Uninstall**.

Bot akan berjalan otomatis lewat systemd dan restart sendiri jika berhenti.

## Jika terjadi error silakan instal
```bash
sudo apt-get install -y libzbar0 ffmpeg
```

## 📖 Panduan Penggunaan

### 👑 Untuk Owner Utama (Super Admin)
- `/start`: Memulai interaksi.
- `/akses <user_id>`: Memberikan hak kepada pengguna untuk membuat bot.
- `/allbots`: Melihat semua bot yang aktif di sistem.
- `/botowners`: Melihat tabel semua bot (owner, token, masa aktif, jumlah penjualan).
- `/extend`: Membuka panel atur masa aktif bot (tambah/kurangi 1–12 bulan).
- `/dashboard`: Melihat statistik lengkap platform dan kesehatan server.
- `/broadcast_owners <pesan>`: Mengirim pesan ke semua pemilik bot.
- `/block on|off`: Mengaktifkan mode block untuk bot yang sedang dipakai.
- `/restore`: Balas ke file `database.zip` untuk memulihkan data.
- `/eval`: Menjalankan kode Python untuk debugging.

### 👤 Untuk Pemilik Bot (Pengguna)
- **Buat Bot**: Tekan tombol **"🤖 Buat Bot"** di bot utama.
- **Panel Pengaturan**: Di bot pribadi Anda, gunakan **"⚙️ Panel Pengaturan ⚙️"** untuk:
    - Menambah/menghapus paket VVIP (dengan durasi langganan).
    - Mengelola kupon diskon.
    - Mengecek anggota, broadcast, mengatur API Saweria, template notifikasi pemasukan, dll.
- **Minta Perpanjangan**: Di bot utama, masuk ke menu **"📦 Bot Saya"** untuk meminta perpanjangan masa aktif bot.

### 👨‍👩‍👧‍👦 Untuk Pengguna Akhir (Pelanggan)
- `/start`: Memulai bot VVIP.
- **Lihat Paket**: Klik **"📚 Lihat Daftar VVIP 📚"**.
- **Pilih Paket**: Gunakan **"Ambil Semua VIP"** untuk seluruh paket atau **"Ambil Sebagian VIP"** untuk memilih beberapa paket sendiri.
- **Pembayaran**: Pilih paket, gunakan kupon (jika ada), lalu bayar dengan QRIS (Saweria).
- **Akses Grup**: Link undangan otomatis dikirim setelah pembayaran sukses — satu pesan per paket untuk pembelian pilihan sendiri. Link akan dihapus setelah Anda bergabung atau setelah 10 menit.

#### ⭐️ Dibuat oleh: [@NorSodikin](https://t.me/NorSodikin)
