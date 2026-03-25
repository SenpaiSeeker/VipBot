import yaml

RAW_ID_STRINGS = r"""general:
  back: • Kembali •
  back_to_main_menu: • Kembali ke Menu Utama •
  back_to_settings: • Kembali ke Pengaturan •
  back_to_settings_api: • Kembali ke Pengaturan API •
  back_to_bot_list: ⬅️ Kembali ke Daftar Bot
  back_to_group_selection: • Kembali ke Pemilihan Grup •
  back_to_vvip_list: • Kembali ke Daftar VVIP •
  close_panel: Tutup Panel
  cancelled: <emoji id=6298671811345254603>🚫</emoji> **Proses Dibatalkan**
  timeout: '<emoji id=5413704112220949842>⏰</emoji> **Waktu Habis**

    Proses telah dibatalkan otomatis.'
  error: '<emoji id=6298671811345254603>❌</emoji> **Terjadi Kesalahan**

    <pre>{e}</pre>'
  success: <emoji id=6296367896398399651>✅</emoji> **Sukses!**
  processing: '<emoji id=5451732530048802485>⏳</emoji> **Sedang Memproses...**

    Mohon tunggu sebentar.'
  invalid_input_timeout: '**Input Tidak Valid / Timeout**

    Proses dibatalkan.'
  no_access: 🚫 Anda tidak memiliki akses ke menu ini.
  invalid_format: '**Format Salah**'
  not_your_bot: Ini bukan bot milik Anda.
  invalid_callback: Data callback tidak valid.
  no_access_decorator: '<emoji id=6298671811345254603>🚫</emoji> **Akses Ditolak!**

    Anda tidak memiliki izin untuk menggunakan perintah ini.'
prompts:
  cancel_footer: '


    Ketik `/batal` untuk membatalkan.'
  skip_footer: '

    Ketik `/skip` untuk menggunakan teks default.'
start:
  welcome_main_bot: '<emoji id=5458904472598095631>👋🏻</emoji> **Selamat Datang, {mention}!**


    Saya adalah asisten utama untuk membuat dan mengelola <emoji id=6244241334320762892>💎</emoji>
    **Bot VVIP** Anda sendiri. Jelajahi semua fitur yang tersedia melalui tombol di
    bawah ini.'
  welcome_clone_bot: '<emoji id=5458904472598095631>👋🏻</emoji> **Selamat Datang, {mention}!**


    Saya adalah asisten pribadi Anda untuk mengakses konten eksklusif. Jelajahi semua
    fitur yang tersedia melalui tombol di bawah ini.'
  create_bot: 🤖 Buat Bot
  my_bots: 📦 Bot Saya
  settings_panel: ⚙️ Panel Pengaturan ⚙️
  list_vvip: 📚 Lihat Daftar VVIP 📚
  donate: ❤️ Donasi
  about_bot: ℹ️ Tentang Bot ℹ️
about:
  panel: '<emoji id=5458799228719472718>🌟</emoji> **Tentang Bot VVIP Ini**


    Selamat datang! Saya adalah asisten otomatis yang dirancang untuk memberikan Anda
    kemudahan dalam mengakses grup VVIP.


    <emoji id=5372981976804366741>🤖</emoji> **Fungsi Utama Saya:**

    Saya menyediakan sistem pembayaran otomatis yang aman via QRIS, memastikan Anda
    mendapatkan akses instan ke konten premium setelah transaksi berhasil.


    <emoji id=5445284980978621387>🚀</emoji> **Alur Penggunaan:**

    1. **Pilih Paket:** Jelajahi daftar VVIP yang tersedia.

    2. **Lakukan Pembayaran:** Scan QRIS yang saya berikan.

    3. **Akses Instan:** Link undangan akan otomatis terkirim setelah pembayaran terkonfirmasi.


    Semua proses dirancang agar cepat, aman, dan tanpa perlu menunggu konfirmasi manual!'
  description: Saya adalah asisten otomatis yang dirancang untuk memberikan Anda kemudahan
    dalam mengakses grup VVIP, melalui sistem pembayaran otomatis yang aman via QRIS.
vvip_list:
  empty: <emoji id=5431736674147114227>🗂️</emoji> Saat ini belum ada paket VVIP yang
    tersedia.
  panel: '<emoji id=5334882760735598374>📚</emoji> **Daftar VVIP Bot: {mention}**


    Berikut adalah daftar paket eksklusif yang kami tawarkan. Klik pada salah satu
    paket untuk melihat detail lengkap dan penawaran spesial.'
  button_package: 📂 {name}
  button_promo: 🎉 Promo {name}
  button_take_all_vip: 🛒 Ambil Semua VIP
donation:
  panel: '<emoji id=6271607783599117330>❤️</emoji> **Dukung Kami dengan Telegram Stars!**


    Donasi Anda sangat berarti untuk membantu kami terus mengembangkan dan memelihara
    bot ini.


    Setiap Star yang Anda berikan memberikan kami semangat untuk terus berinovasi.
    Pilih jumlah donasi di bawah ini untuk memulai.


    Terima kasih atas dukungan Anda!'
admin:
  eval:
    processing: <emoji id=5264727218734524899>🔄</emoji> `Memproses kode...`
    no_code: <emoji id=6298671811345254603>❌</emoji> **Perintah Gagal:** Harap berikan
      kode untuk dievaluasi.
    success: <emoji id=6296367896398399651>✅</emoji> **Eksekusi Berhasil**
    output: '**<emoji id=6219796119933683821>🖥️</emoji> OUTPUT:**

      <pre>{output}</pre>


      **<emoji id=5451732530048802485>⏳</emoji> Waktu Eksekusi:** `{time:.4f}` detik'
    too_long_caption: <emoji id=6219796119933683821>📄</emoji> Hasil evaluasi terlalu
      panjang. Dikirim sebagai file.
  restore:
    usage: '<emoji id=6271786398404055377>⚠️</emoji> **Cara Penggunaan Salah:**

      Balas (reply) ke file backup `.zip` yang dikirim oleh bot dengan perintah ini.'
    wrong_format: '<emoji id=6298671811345254603>❌</emoji> **Format File Salah:**

      Hanya file backup dengan format `.zip` yang bisa dipulihkan.'
    processing: <emoji id=5451732530048802485>⏳</emoji> `Mendownload & mengekstrak
      file backup...`
    empty_zip: File .zip ini kosong atau rusak.
    success: '<emoji id=6296367896398399651>✅</emoji> **Pemulihan Berhasil!**

      Database `{db_path}` telah dipulihkan.


      <emoji id=6271786398404055377>⚠️</emoji> **PENTING:** Mohon **restart** bot
      agar dapat menggunakan database baru.'
    fail: '<emoji id=6298671811345254603>❌</emoji> **Pemulihan Gagal!**


      **Error:** `{e}`'
  access:
    usage_error: '**Format Salah.**

      Gunakan: `/akses <user_id atau @username>`'
    panel: '**<emoji id=6176966310920983412>🔑</emoji> Kelola Akses Pembuatan Bot**


      **Pengguna:** {mention}

      **ID:** `{id}`

      **Status:** `{status}`


      Pilih tindakan untuk pengguna ini:'
    has_access: <emoji id=6296367896398399651>✅</emoji> Memiliki Akses
    no_access: <emoji id=6298671811345254603>❌</emoji> Tidak Memiliki Akses
    give_button: ✅ Beri Akses
    revoke_button: ❌ Cabut Akses
    give_success_alert: <emoji id=6296367896398399651>✅</emoji> Akses berhasil diberikan
      kepada {target_id}
    revoke_success_alert: <emoji id=6298671811345254603>❌</emoji> Akses berhasil dicabut
      dari {target_id}
    process_fail: 'Gagal memproses. Error: `{e}`'
    give_duration_panel: 'Pilih durasi akses yang ingin diberikan:'
    give_success_panel_manual: '<emoji id=6296367896398399651>✅</emoji> **Akses Diberikan!**


      Pengguna {mention} sekarang memiliki akses untuk membuat bot selama **{months}
      bulan**.


      Masa aktif akses hingga: `{new_date}`'
    revoke_success_panel: '<emoji id=6298671811345254603>❌</emoji> **Akses Dicabut!**


      Pengguna {mention} tidak lagi memiliki hak untuk membuat bot.'
  seller:
    not_found: <emoji id=6298671811345254603>❌</emoji> Pengguna tidak ditemukan. Pastikan
      ID/Username benar atau balas pesan pengguna.
    already_exists: <emoji id=6298671811345254603>❌</emoji> User `{user_id}` sudah
      terdaftar sebagai seller.
    add_success: <emoji id=6296367896398399651>✅</emoji> Berhasil menambahkan `{user_mention}`
      sebagai seller.
    list_title: '**<emoji id=6176966310920983412>👤</emoji> Daftar Seller Aktif**


      '
    empty: Belum ada seller yang terdaftar.
    delete_button: Hapus Seller 🗑️
    deleted: Seller `{user_id}` berhasil dihapus.
  access_list:
    list_title: '**<emoji id=6176966310920983412>🔑</emoji> Daftar Pengguna Berakses**


      '
    empty: Tidak ada pengguna yang memiliki akses aktif saat ini.
    delete_button: Cabut Akses 🚫
    deleted: Akses untuk `{user_id}` telah dicabut.
  extend:
    usage_error: '**Format salah.**

      Gunakan: `/extend <bot_id> <jumlah_hari>`

      Contoh: `/extend 12345678 30`'
    success: '<emoji id=6296367896398399651>✅</emoji> **Sukses!** Durasi bot `{bot_id}`
      berhasil diubah. Masa aktif baru: `{new_date}`.'
    notification: '🎉 **Kabar Baik!**


      Masa aktif bot Anda **{bot_name}** telah diperpanjang oleh Owner Utama.'
    fail: '<emoji id=6298671811345254603>❌</emoji> Terjadi kesalahan: `{e}`'
  allbots:
    empty: Belum ada bot yang dibuat oleh pengguna manapun.
    panel: '**<emoji id=6283073379184415506>📦</emoji> Daftar Semua Bot ({page}/{total})**


      • **Nama Bot:** {bot_name}

      • **ID Bot:** `{bot_id}`

      • **Username Bot:** @{username}

      • **Pemilik:** {owner}

      • **Sisa Aktif:** `{days_left}` hari'
    offline: (Offline)
    error: (Error)
    unknown: Tidak diketahui
    prev_button: « Sebelumnya
    next_button: Selanjutnya »
    days: hari
    delete_button: 🗑️ Hapus Bot
    manage_duration_button: 🗓️ Kelola Masa Aktif
    delete_confirm: '**<emoji id=6271786398404055377>⚠️</emoji> Konfirmasi Penghapusan**


      Anda yakin ingin menghapus bot dengan ID `{bot_id}` secara permanen?'
    delete_confirm_yes: ✅ Ya, Hapus
    delete_confirm_no: ❌ Tidak
    deleting: <emoji id=5451732530048802485>⏳</emoji> Menghapus bot...
    delete_success: <emoji id=6296367896398399651>✅</emoji> Bot berhasil dihapus.
    delete_fail: '<emoji id=6298671811345254603>❌</emoji> Gagal menghapus bot: {e}'
    manage_duration_panel: '**<emoji id=4972341539033318152>🗓️</emoji> Kelola Masa
      Aktif untuk Bot `{bot_id}`**'
    add_duration_button: ➕ Tambah Masa Aktif
    reduce_duration_button: ➖ Kurangi Masa Aktif
    add_duration_select: 'Pilih durasi untuk ditambahkan ke Bot `{bot_id}`:'
    reduce_duration_select: 'Pilih durasi untuk dikurangi dari Bot `{bot_id}`:'
    add_duration_success: '{days} hari berhasil ditambahkan ke bot {bot_id}.'
    reduce_duration_success: Masa aktif bot {bot_id} berhasil dikurangi {days} hari.
    reduce_duration_no_expiry: Bot ini tidak memiliki tanggal kedaluwarsa untuk dikurangi.
  refund:
    no_permission: 🚫 Anda tidak memiliki izin untuk melakukan ini.
    fail_not_found: '


      <emoji id=6271786398404055377>⚠️</emoji> **Gagal: Transaksi tidak ditemukan
      atau sudah di-refund.**'
    success_text: '


      <emoji id=6296367896398399651>✅</emoji> Donasi berhasil dikembalikan.'
    success_notif: 'ℹ️ **Informasi Donasi**


      Donasi Stars Anda telah dikembalikan oleh admin. Terima kasih atas pengertiannya.'
    fail_text: '


      <emoji id=6298671811345254603>❌</emoji> **Gagal mengembalikan donasi:**

      `{e}`'
  total_users:
    result: '**<emoji id=5372926953978341366>👥</emoji> Total Pengguna Bot**


      Jumlah keseluruhan pengguna yang pernah memulai bot ini adalah: **{total} pengguna**.'
  dashboard:
    panel: '**<emoji id=5431577498364158238>📊</emoji> Dashboard Platform**


      **Statistik Platform:**

      - Total Bot Aktif: `{total_bots}`

      - Total Pengguna Unik: `{total_users}`

      - Bot Terpopuler: `{top_bot}`


      **Kesehatan Server:**

      {server_stats}'
    server_stats: '- CPU: `{cpu}%`

      - RAM: `{ram}%`

      - Disk: `{disk}%`'
    server_stats_fail: 'Gagal mengambil statistik server: `{e}`'
  broadcast_owners:
    usage: 'Gunakan: `/broadcast_owners <pesan>` atau balas ke sebuah pesan.'
    no_owners: Tidak ada pemilik bot yang bisa di-broadcast.
bot_management:
  payment:
    panel: '**<emoji id=6129870117619634982>💳</emoji> Beli Akses Pembuatan Bot**


      Dapatkan akses untuk membuat bot VVIP Anda sendiri dengan berlangganan.


      Harga: `Rp {price}/bulan`


      **Diskon:**

      • 3+ Bulan: 10%

      • 6+ Bulan: 20%


      **Pilihan Anda:**

      • Durasi: **{months} bulan**

      • Harga Normal: `Rp {total}`

      • Diskon: `{discount}`

      • **Total Bayar: `Rp {final}`**'
    month: Bulan
    pay_button: Bayar via QRIS (Rp {final})
    already_subscribed: '<emoji id=6296367896398399651>✅</emoji> **Anda Sudah Berlangganan!**


      Anda sudah memiliki akses untuk membuat bot. Tekan tombol di bawah untuk memulai
      proses pembuatan.'
    proceed_create_button: ▶️ Lanjutkan Membuat Bot
    success: '<emoji id=6296367896398399651>✅</emoji> **Pembayaran Berhasil!**


      Terima kasih! Langganan Anda untuk membuat bot selama **{months} bulan** telah
      diaktifkan.'
    owner_notif: '<emoji id=5375296873982604963>💰</emoji> **Langganan Akses Baru!**


      **Pengguna:** {mention}

      **Durasi:** {months} bulan

      **Jumlah:** `Rp {amount}`'
  create:
    new_user_notification: '**<emoji id=5373012449597335010>👤</emoji> Pengguna Baru
      Telah Memulai Bot Anda!**


      **Bot:** {mention}

      **Pengguna:** {user_mention}

      **ID:** `{user_id}`'
    no_access: '**🚫 Akses Ditolak**


      Hubungi {mention} untuk meminta akses membuat bot.'
    step1_api_id: '**<emoji id=5472308992514464048>🔐</emoji> 1/3: Masukkan API ID
      Anda.**

      Dapatkan dari my.telegram.org.'
    step2_api_hash: '**<emoji id=5472308992514464048>🔐</emoji> 2/3: Masukkan API Hash
      Anda.**

      Dapatkan dari my.telegram.org.'
    step3_bot_token: '**<emoji id=5372981976804366741>🤖</emoji> 3/3: Masukkan Bot
      Token Anda.**

      Dapatkan dari @BotFather.'
    verifying: <emoji id=5188217332748527444>🔍</emoji> `Memverifikasi data & token...`
    invalid_token: Token bot yang Anda masukkan tidak valid.
    saving: <emoji id=6296367896398399651>✅</emoji> Bot '{name}' valid dan sedang
      disimpan. `<emoji id=5445284980978621387>🚀</emoji> Memulai bot...`
    success: <emoji id=5436040291507247633>🎉</emoji> **Selamat!** Bot **{name}** berhasil
      dibuat dan aktif selama **30 hari**.
    fail: <emoji id=6298671811345254603>❌</emoji> **Error Pembuatan Bot:** `{e}`
    main_bot_inactive: Bot utama sedang tidak aktif, tidak dapat mengirim notifikasi.
  my_bots:
    empty: Anda belum memiliki bot. Tekan 'Buat Bot' untuk memulai.
    panel: '**<emoji id=6283073379184415506>📦</emoji> Daftar Bot Saya ({page}/{total})**


      • **Nama Bot:** {bot_name}

      • **ID Bot:** `{bot_id}`

      • **Username Bot:** @{username}

      • **Sisa Aktif:** `{days_left}` hari'
    manage_button: ⚙️ Kelola {name}
  manage:
    panel: '**<emoji id=6257780484281997093>⚙️</emoji> Kelola Bot: {name}**


      **ID Bot:** `{id}`

      **Sisa Masa Aktif:** `{days_left}`


      Pilih tindakan yang ingin Anda lakukan:'
    not_set: Tidak diatur
    extend_button: ➕ Minta Perpanjangan
    delete_button: 🗑️ Hapus Bot Ini
  extend:
    panel_owner: '**<emoji id=5242628160297641831>🔔</emoji> Permintaan Perpanjangan
      Durasi**


      **Pengguna:** {mention} (`{id}`)

      **Bot:** **{bot_name}** (`{bot_id}`)


      Setujui untuk menambah masa aktif bot ini sebanyak 30 hari.'
    approve_button: ✅ Setujui (+30 Hari)
    reject_button: ❌ Tolak Permintaan
    sent_alert: ✅ Permintaan perpanjangan telah dikirim ke Owner Utama. Anda akan
      dihubungi jika disetujui.
    fail_alert: '❌ Gagal mengirim permintaan ke Owner: {e}'
    approve_denied: Hanya Owner Utama yang bisa menyetujui permintaan ini.
    approve_success_log: '<emoji id=6296367896398399651>✅</emoji> **Persetujuan Berhasil!**

      Durasi untuk bot `{bot_id}` telah ditambah **{days} hari**.'
    approve_success_notif: '<emoji id=5436040291507247633>🎉</emoji> **Kabar Baik!**


      Permintaan perpanjangan Anda untuk bot **{bot_name}** telah disetujui dan diperpanjang.'
    approve_fail: '<emoji id=6298671811345254603>❌</emoji> Gagal menyetujui permintaan:
      `{e}`'
    reject_denied: Hanya Owner Utama yang bisa melakukan ini.
    rejected_log: <emoji id=6298671811345254603>🚫</emoji> Permintaan telah ditolak/ditutup
      oleh Owner Utama.
  delete:
    confirm_panel: '**<emoji id=6271786398404055377>⚠️</emoji> Konfirmasi Penghapusan**


      Anda yakin ingin menghapus bot **{name}** (`{id}`) secara permanen?


      __Semua data (member, paket, pengaturan) bot ini akan hilang dan tindakan ini
      tidak dapat diurungkan.__'
    confirm_yes_button: ✅ Ya, Saya Yakin Hapus
    confirm_no_button: ❌ Tidak, Batalkan
    no_permission: Anda tidak berhak menghapus bot ini.
    processing: <emoji id=5451732530048802485>⏳</emoji> Sedang menghentikan dan menghapus
      bot `{id}`...
    success: '<emoji id=6296367896398399651>✅</emoji> **Penghapusan Berhasil!**

      Bot `{id}` beserta datanya telah dihapus dari sistem.'
    fail: '<emoji id=6298671811345254603>❌</emoji> Terjadi kesalahan saat menghapus
      bot: `{e}`'
member:
  list:
    empty: <emoji id=6296367896398399651>✅</emoji> Tidak ada member VVIP yang tercatat
      di database.
    panel: '**<emoji id=5372926953978341366>👥</emoji> Daftar Member VVIP ({page}/{total})**


      **Nama:** {mention}

      **ID:** `{id}`

      **Kategori:** `{category}` ({type})

      **Bergabung:** `{date}`

      **Kedaluwarsa:** `{expiry}`'
    data_error: 'Data member ini tampaknya rusak atau pengguna tidak dapat diakses
      lagi.

      `Error: {e}`


      Entri ini telah dihapus dari daftar untuk menjaga kebersihan data.'
    kick_button: 🚨 Tendang {name}
    permanent_access: Permanen
  kick:
    confirm_panel: '**<emoji id=6271786398404055377>⚠️</emoji> Konfirmasi Penendangan**


      Anda yakin ingin menendang **{mention}** dari grup VVIP **{name}**?


      Pengguna akan dikeluarkan dari grup dan data keanggotaannya akan dihapus.'
    confirm_yes_button: ✅ Ya, Tendang
    confirm_no_button: ❌ Tidak
    record_not_found: <emoji id=6298671811345254603>❌</emoji> **Gagal:** Record keanggotaan
      tidak ditemukan di database.
    invalid_chat_id: <emoji id=6298671811345254603>❌</emoji> **Gagal:** Chat ID untuk
      menendang member tidak valid atau belum diatur di paket VVIP.
    processing: <emoji id=5451732530048802485>⏳</emoji> `Memproses penendangan member
      dari grup...`
    success: '<emoji id=6296367896398399651>✅</emoji> **Sukses!**

      Pengguna {mention} telah ditendang dari **{name}** dan dihapus dari daftar.'
    fail: <emoji id=6298671811345254603>❌</emoji> **Gagal Menendang:** `{e}`
  active_list:
    panel: '**<emoji id=6271786398404055377>🕵️</emoji> Cek Member Aktif Real-time**


      Pilih grup yang ingin Anda periksa untuk melihat daftar anggotanya saat ini.'
    button_normal: 👥 Cek '{name}' Normal
    button_promo: 👥 Cek '{name}' Promo
    no_valid_chat_id: Tidak ada VVIP dengan Chat ID valid yang terkonfigurasi. Silakan
      atur terlebih dahulu.
    fetching: <emoji id=5451732530048802485>⏳</emoji> Mengambil data member dari server
      Telegram, mohon tunggu...
    fetch_fail: '<emoji id=6298671811345254603>❌</emoji> **Gagal Mengambil Daftar
      Member:**

      `{e}`'
    empty: Tidak ada anggota (non-bot) yang ditemukan di dalam grup ini.
    member_panel: '**<emoji id=6271786398404055377>🕵️</emoji> Member Aktif ({page}/{total})**


      **Nama:** {mention}

      **ID:** `{id}`

      **Status:** `{status}`'
    kick_confirm_panel: '**<emoji id=6271786398404055377>⚠️</emoji> Konfirmasi**


      Anda yakin ingin menendang **{mention}** dari grup?'
    kick_confirm_yes_button: ✅ Ya, Tendang
    kick_confirm_no_button: ❌ Tidak, Batalkan
    kick_processing: <emoji id=5451732530048802485>⏳</emoji> `Memproses penendangan
      pengguna...`
    kick_success: '<emoji id=6296367896398399651>✅</emoji> **Sukses!**

      Pengguna **{mention}** telah ditendang dari grup.'
subscription:
  renewal_reminder: '<emoji id=5242628160297641831>🔔</emoji> **Pengingat Langganan**


    Langganan Anda untuk paket **{name}** akan berakhir dalam **{days} hari** lagi.
    Perpanjang sekarang agar tidak kehilangan akses!'
  renew_button: 🔄 Perpanjang Sekarang
  expired_kick_notif: '<emoji id=5451646226975955576>⌛</emoji> **Langganan Berakhir**


    Langganan Anda untuk paket **{name}** telah berakhir. Anda telah dikeluarkan dari
    grup.'
payment:
  notes:
    not_found: <emoji id=6298671811345254603>❌</emoji> Paket VVIP tidak ditemukan.
    pay_button: 💸 Bayar Harga Normal
  promo:
    not_found: <emoji id=6298671811345254603>❌</emoji> Paket promo tidak ditemukan
      atau tidak aktif.
    pay_button: ✅ Bayar Harga Promo
  pay:
    service_inactive_panel: '<emoji id=6271786398404055377>⚠️</emoji> **Layanan Pembayaran
      Tidak Aktif**


      Silakan atur API Key untuk payment gateway terlebih dahulu.'
    service_inactive_alert: Maaf, layanan pembayaran saat ini tidak tersedia.
    setup_api_button: ⚙️ Atur Kunci API
    not_found: <emoji id=6298671811345254603>❌</emoji> Paket VVIP ini tidak ditemukan
      lagi.
    invalid_price: <emoji id=6298671811345254603>❌</emoji> Harga untuk paket ini tidak
      valid (0 atau kurang).
    qr_fail: Gagal mengunduh gambar QRIS.
    all_vvip_product_name: Semua VIP ({total} paket)
    invoice_full: '**<emoji id=6296367896398399651>✅</emoji> Pembayaran Siap Dilakukan!**


      Silakan scan QRIS di atas untuk membayar. Setelah itu, tekan tombol **Konfirmasi
      Pembayaran**.


      ╭─ **Detail Tagihan**

      │

      ├─ <emoji id=5373052667671093676>🛍️</emoji> **Produk:** {name} ({type})

      ├─ <emoji id=6129870117619634982>💳</emoji> **Jumlah:** `Rp {amount}`

      ├─ <emoji id=6269253325477123346>🆔</emoji> **Order ID:** {id}

      │

      ╰─ <emoji id=5470177992950946662>👇</emoji> **Jika sudah membayar, silakan klik
      tombol di bawah ini.**

      '
  check:
    confirm_button: ✅ Konfirmasi Pembayaran
    checking: <emoji id=5188217332748527444>🔍</emoji> Memeriksa status pembayaran...
    not_paid: ❌ Pembayaran belum terdeteksi. Silakan coba lagi setelah beberapa saat.
    expired_or_completed: <emoji id=6271786398404055377>⚠️</emoji> Invoice ini sudah
      tidak valid atau telah selesai.
    category_missing: Kategori VVIP '{name}' tidak lagi ditemukan di database. Pembayaran
      berhasil, namun link grup gagal diberikan. Mohon hubungi admin.
    success_customer_full: '<emoji id=5436040291507247633>🎉</emoji> **Pembayaran Dikonfirmasi!**


      Terima kasih, berikut adalah link akses Anda untuk paket **{name}**:


      {link}


      <emoji id=6271786398404055377>⚠️</emoji> Link ini hanya berlaku untuk 1 kali
      klik dan akan kedaluwarsa dalam 60 menit jika tidak digunakan.

      '
    success_customer_bundle: '<emoji id=5436040291507247633>🎉</emoji> **Pembayaran
      Paket Semua VIP Berhasil!**


      Berikut semua link akses VIP Anda:


      {links}


      <emoji id=6271786398404055377>⚠️</emoji> Setiap link hanya berlaku 1 kali klik
      dan kedaluwarsa dalam 60 menit.

      '
    pending_join_multi: '<emoji id=6271786398404055377>⚠️</emoji> Anda belum join
      ke semua grup VIP dalam waktu 60 menit.


      Silakan join grup berikut:

      {pending_links}

      '
    bundle_empty_or_invalid: <emoji id=6298671811345254603>❌</emoji> Tidak ada paket
      VIP valid untuk pembelian semua VIP.
    all_vvip_label: Semua VIP
    success_owner_notif: '<emoji id=5375296873982604963>💰</emoji> **Pemasukan Baru!**


      **Pengguna:** {mention}

      **Bot:** {bot_mention}

      **Kategori:** `{name}` ({type})'
    expired_msg: '<emoji id=5451732530048802485>⏳</emoji> **Invoice Kedaluwarsa.**

      Order ID `{id}` telah dibatalkan karena melewati batas waktu pembayaran.'
    link_expired: <emoji id=6271786398404055377>⚠️</emoji> Link undangan Anda telah
      kedaluwarsa karena Anda tidak bergabung dalam 60 menit. Silakan hubungi admin
      jika terjadi masalah.
  donation:
    invoice_title: Donasi untuk Pengembangan Bot
    invoice_desc: Dukungan Anda sebesar {stars} Bintang (Stars) sangat kami hargai.
      Terima kasih!
    invalid_amount: Jumlah donasi tidak valid!
    preparing: Mempersiapkan invoice donasi...
    invoice_fail: Gagal membuat invoice donasi. Coba lagi nanti.
    success_msg: '<emoji id=5436040291507247633>🎉</emoji> **Terima Kasih Banyak, {name}!**


      Kami telah menerima donasi Anda sebesar **{stars} Stars (<emoji id=6298332994260175589>⭐</emoji>)**.

      Dukungan Anda adalah bahan bakar semangat bagi kami. Semoga hari Anda menyenangkan!'
    owner_notif: '<emoji id=5472164874886846699>✨</emoji> **Donasi Baru Diterima!**


      **Jumlah:** `{stars}` Stars (<emoji id=6298332994260175589>⭐</emoji>)

      **Dari:** {mention} (`{id}`)

      **Melalui Bot:** {bot_mention}'
    refund_button: 🔙 Kembalikan Donasi
    owner_blocked_notif: '<emoji id=6271786398404055377>⚠️</emoji> **Notifikasi Gagal
      Terkirim**


      Notifikasi donasi sebesar `{stars}` Stars dari {mention} gagal dikirim ke owner
      bot `{bot_name}` karena bot diblokir olehnya.'
  defaults:
    notes_text: '╭─ **<emoji id=5472164874886846699>✨</emoji> Detail Paket VVIP**

      │

      ├─ <emoji id=5431721976769027887>📂</emoji> **Nama Paket:** `{name}`

      ├─ <emoji id=5334882760735598374>📝</emoji> **Deskripsi:** Dapatkan akses instan
      ke konten premium dan eksklusif setelah pembayaran berhasil.

      │

      ├─ <emoji id=6129870117619634982>💳</emoji> **Harga Normal:** `Rp {price}`

      │

      ╰─ Silakan klik tombol ''Bayar'' di bawah untuk melanjutkan!

      '
    promo_text: '╭─ **<emoji id=5436040291507247633>🎉</emoji> Penawaran Spesial Terbatas!**

      │

      ├─ <emoji id=5431721976769027887>📂</emoji> **Nama Paket:** `{name}`

      ├─ <emoji id=5334882760735598374>📝</emoji> **Deskripsi:** Jangan lewatkan kesempatan
      emas ini untuk bergabung dengan harga yang jauh lebih terjangkau!

      │

      ├─ <emoji id=5375296873982604963>💰</emoji> **Harga Promo:** `Rp {promo_price}`

      │

      ╰─ Segera amankan slot Anda sebelum promo berakhir!

      '
settings:
  vip_revenue: 💰 Pendapatan VIP
  panel: '**<emoji id=6257780484281997093>🛠️</emoji> Panel Pengaturan Owner**


    Selamat datang di pusat kendali bot Anda! Silakan pilih menu di bawah untuk mengelola
    berbagai aspek bot.'
  set_start_photo: 🖼️ Atur Foto Start
  set_start_text: ✍️ Atur Teks Start
  add_vvip: ➕ Tambah VVIP
  del_vvip: ➖ Hapus VVIP
  check_members: 👥 Cek Member VVIP
  check_active_members: 🕵️ Cek Member Aktif
  api_keys: 🔑 Kelola Kunci API
  broadcast: 📢 Buat Broadcast
  stats_button: ⭐ Statistik Stars
  total_users: 👥 Total Pengguna
  coupons: 🎟️ Kelola Kupon
  set_photo_prompt: '<emoji id=5375074927252621134>🖼️</emoji> **Atur Foto Start**


    Silakan kirim foto baru yang ingin Anda gunakan sebagai gambar di pesan /start.


    Ketik `/empty` untuk menghapus foto saat ini dan kembali ke default.'
  set_photo_fail: <emoji id=6298671811345254603>❌</emoji> **Gagal:** Pesan yang dikirim
    bukan foto. Proses dibatalkan.
  set_photo_success: <emoji id=6296367896398399651>✅</emoji> **Sukses!** Foto /start
    telah berhasil diperbarui.
  photo_emptied: <emoji id=6296367896398399651>✅</emoji> **Sukses!** Foto /start telah
    dihapus dan akan kembali ke default.
  set_text_prompt: '<emoji id=5470060791883374114>✍️</emoji> **Atur Teks Start**


    Silakan kirim teks baru untuk pesan /start. Anda dapat menggunakan variabel `{mention}`
    untuk menyapa pengguna.


    **Contoh:** `Halo {mention}, selamat datang di bot saya!`


    Ketik `/empty` untuk menghapus teks kustom dan kembali ke default.'
  set_text_fail: <emoji id=6298671811345254603>❌</emoji> **Gagal:** Pesan yang dikirim
    tidak berisi teks. Proses dibatalkan.
  set_text_success: <emoji id=6296367896398399651>✅</emoji> **Sukses!** Teks /start
    telah berhasil diperbarui.
  text_emptied: <emoji id=6296367896398399651>✅</emoji> **Sukses!** Teks /start telah
    dihapus dan akan kembali ke default.
  broadcast_prompt: '**<emoji id=5368776520921784743>📢</emoji> Kirim Pesan Broadcast**


    Silakan teruskan (forward) atau kirim pesan yang ingin Anda siarkan ke semua pengguna
    yang pernah memulai bot ini. Anda bisa menggunakan tombol format.'
  broadcast_no_users: <emoji id=6298671811345254603>❌</emoji> **Gagal:** Tidak ada
    pengguna untuk disiarkan.
  broadcast_start: <emoji id=6296367896398399651>✅</emoji> Memulai siaran ke `{count}`
    pengguna...
  broadcast_done: '**<emoji id=5368776520921784743>📢</emoji> Siaran Selesai!**

    <emoji id=6296367896398399651>✅</emoji> **Terkirim:** `{success}`

    <emoji id=6298671811345254603>❌</emoji> **Gagal:** `{fail}` (pengguna gagal telah
    dihapus dari database)'
  setup_vvip:
    step1_name: '**<emoji id=5470060791883374114>✍️</emoji> Langkah 1/8: Nama Kategori**

      Contoh: `VVIP Bulanan`'
    step2_price: '**<emoji id=5375296873982604963>💰</emoji> Langkah 2/8: Harga Normal**

      Contoh: `50000` (tanpa titik atau koma)'
    step3_duration: '**<emoji id=5451732530048802485>⏳</emoji> Langkah 3/8: Durasi
      Keanggotaan (Hari)**

      Kirim `0` untuk akses permanen.'
    step4_chat_id: '**<emoji id=6269253325477123346>🆔</emoji> Langkah 4/8: Chat ID
      Grup Normal**

      Contoh: `-100123456789`. Ini adalah grup tujuan untuk member.'
    step5_promo_price: '**<emoji id=5436040291507247633>🎉</emoji> Langkah 5/8: Harga
      Promo**

      Kirim `0` jika tidak ada harga promo.'
    step6_promo_chat_id: '**<emoji id=6269253325477123346>🆔</emoji> Langkah 6/8: Chat
      ID Grup Promo**

      Diisi jika Harga Promo > 0.'
    step7_promo_text: '**<emoji id=5334882760735598374>📝</emoji> Langkah 7/8: Teks
      Deskripsi Promo**

      Gunakan `{name}` dan `{promo_price}`.'
    step8_normal_text: '**<emoji id=5334882760735598374>📝</emoji> Langkah 8/8: Teks
      Deskripsi Normal**

      Gunakan `{name}` dan `{price}`.'
    err_must_be_number: Input harus berupa angka.
    err_must_be_link: Input harus berupa link yang valid (diawali http/https).
    err_must_be_chat_id: Input harus berupa ID chat numerik (biasanya diawali dengan
      -100).
    success: '<emoji id=6296367896398399651>✅</emoji> **Sukses!**

      Paket VVIP **{name}** berhasil ditambahkan.'
    cancelled: <emoji id=6298671811345254603>🚫</emoji> Setup paket VVIP dibatalkan
      oleh pengguna.
  delete_vvip_panel: '**<emoji id=6156513311585211842>🗑️</emoji> Hapus Paket VVIP**


    Pilih paket VVIP yang ingin Anda hapus dari daftar.'
  delete_vvip_empty: <emoji id=6296367896398399651>✅</emoji> Bagus! Tidak ada paket
    VVIP untuk dihapus.
  delete_vvip_button: 🗑️ Hapus {name}
  delete_vvip_success: <emoji id=6296367896398399651>✅</emoji> **Berhasil!** Paket
    **{name}** telah dihapus.
  delete_vvip_fail: <emoji id=6298671811345254603>❌</emoji> **Gagal!** Paket **{name}**
    tidak ditemukan lagi.
  api_panel: '**<emoji id=6176966310920983412>🔑</emoji> Pengelola Kunci API untuk
    {mention}**


    Atur koneksi pembayaran Saweria untuk bot Anda.


    **Status Layanan:**

    - `Gateway Pembayaran (Saweria)`: **{saweria_status}**


    Pilih tindakan:'
  api_status_active: <emoji id=6296367896398399651>✅</emoji> Aktif
  api_status_saweria_active: '<emoji id=6296367896398399651>✅</emoji> Aktif (User:
    {username})'
  api_status_inactive: <emoji id=6298671811345254603>❌</emoji> Belum Diatur
  api_set_saweria: 💳 Atur Kunci Saweria
  api_del_all: 🗑️ Hapus Semua Kunci
  api_set_saweria_1: '**1/2:** Kirim **API Key** Anda dari [Maelyn API](https://api.maelyn.sbs).'
  api_set_saweria_2: '**2/2:** Kirim **Username Saweria** Anda.'
  api_set_fail_saweria: '<emoji id=6298671811345254603>❌</emoji> **Gagal!**

    Username Saweria tidak ditemukan atau API Key salah.


    `Error: {e}`'
  api_set_success_saweria: '<emoji id=6296367896398399651>✅</emoji> **Sukses!**

    Kunci Saweria berhasil diverifikasi dan disimpan.'
  api_set_success: '<emoji id=6296367896398399651>✅</emoji> **Sukses!**

    Kunci untuk `{key_name}` berhasil disimpan dan layanan terkait telah diaktifkan.'
  api_del_confirm_panel: '**⚠️ Konfirmasi**


    Anda yakin ingin menghapus **SEMUA** kunci API (Saweria & Gemini) untuk bot ini?'
  api_del_confirm_yes_button: ✅ Ya, Hapus Semua
  api_del_confirm_no_button: ❌ Tidak, Batalkan
  api_del_success: <emoji id=6296367896398399651>✅</emoji> Semua kunci API untuk bot
    ini telah berhasil dihapus.
  set_broadcast_price: 🌟 Harga Broadcast Paid
  set_broadcast_price_prompt: '<emoji id=5458799228719472718>🌟</emoji> **Atur Harga
    Broadcast Paid**


    Masukkan jumlah Bintang (Stars) yang harus dibayar pengguna untuk melihat media
    broadcast.


    Ketik `0` atau `/empty` untuk menonaktifkan fitur ini (Broadcast akan kembali
    normal dan gratis).'
  set_broadcast_price_success: <emoji id=6296367896398399651>✅</emoji> **Sukses!**
    Harga broadcast telah diatur menjadi `{stars}` Stars.
  set_broadcast_price_disabled: <emoji id=6296367896398399651>✅</emoji> **Sukses!**
    Fitur Paid Broadcast dinonaktifkan. Broadcast akan berjalan normal seperti biasa.
  broadcast_paid_no_media: <emoji id=6298671811345254603>❌</emoji> **Gagal:** Fitur
    Paid Broadcast sedang aktif seharga {stars} Stars. Pesan broadcast Anda HARUS
    berupa Foto atau Video agar bisa dikunci!
revenue:
  panel_title: '**<emoji id=5375296873982604963>💰</emoji> Cek Pendapatan VIP**


    Pilih periode waktu untuk melihat total pendapatan dari penjualan paket VIP.'
  btn_daily: 📅 Harian (Hari Ini)
  btn_weekly: 🗓️ Mingguan (7 Hari)
  btn_monthly: 📆 Bulanan (Bulan Ini)
  period_daily: Harian
  period_weekly: Mingguan
  period_monthly: Bulanan
  result_panel: '**<emoji id=5431577498364158238>📊</emoji> Laporan Pendapatan VIP**


    **Periode:** {period}


    <emoji id=5375296873982604963>💰</emoji> **Total Pendapatan:** `Rp {total}`

    <emoji id=5264727218734524899>🔄</emoji> **Jumlah Transaksi:** `{count}`'
stats:
  panel: '**<emoji id=5431577498364158238>📊</emoji> Statistik Pendapatan Stars**


    <emoji id=5375296873982604963>💰</emoji> **Saldo Saat Ini:** `{balance}` <emoji
    id=6298332994260175589>⭐</emoji>

    <emoji id=5373001317042101552>📈</emoji> **Total Pemasukan:** `{income}` <emoji
    id=6298332994260175589>⭐</emoji>

    <emoji id=5361748661640372834>📉</emoji> **Total Pengembalian:** `{refunds}` <emoji
    id=6298332994260175589>⭐</emoji>

    <emoji id=5264727218734524899>🔄</emoji> **Total Transaksi (Tampil):** `{count}`


    **<emoji id=5282843764451195532>📜</emoji> Transaksi Terakhir ({page}/{total_pages})**

    {transactions}'
  transaction_entry: '• `{date}`: **{amount_str}<emoji id=6298332994260175589>⭐</emoji>**
    dari {peer}'
  transaction_entry_unknown: sumber tidak dikenal
  no_transactions: Belum ada transaksi Stars yang tercatat.
  prev_button: « Sebelumnya
  next_button: Selanjutnya »
coupons:
  panel: '**<emoji id=5377599075237502153>🎟️</emoji> Manajemen Kupon**

    Kelola kode diskon untuk VVIP Anda.'
  add_button: ➕ Buat Kupon Baru
  list_button: 📋 Lihat Kupon
  ask_code: '**1/4:** Masukkan kode kupon unik (misal: `DISKONBARU`).'
  ask_type: '**2/4:** Pilih tipe diskon:

    1. Persentase (%)

    2. Potongan Harga Tetap (misal: 10000)'
  ask_value_percent: '**3/4:** Masukkan nilai persentase (misal: `15` untuk 15%).'
  ask_value_fixed: '**3/4:** Masukkan jumlah potongan harga (misal: `10000` untuk
    Rp 10.000).'
  ask_uses: '**4/4:** Berapa kali kupon ini bisa digunakan? (masukkan angka)'
  ask_expiry: '**5/5:** Berapa hari kupon ini akan berlaku? (masukkan angka)'
  add_success: <emoji id=6296367896398399651>✅</emoji> Kupon `{code}` berhasil dibuat.
  list_empty: Tidak ada kupon yang dibuat.
  list_panel: '**<emoji id=5334882760735598374>📋</emoji> Detail Kupon ({page}/{total})**

    - Kode: `{code}`

    - Tipe: `{type}`

    - Nilai: `{value}`

    - Sisa Penggunaan: `{uses}`

    - Berlaku hingga: `{expiry}`'
  delete_button: 🗑️ Hapus Kupon Ini
  delete_success: <emoji id=6296367896398399651>✅</emoji> Kupon berhasil dihapus.
  use_button: 🎟️ Gunakan Kupon
  prompt: Silakan masukkan kode kupon Anda.
  invalid: <emoji id=6298671811345254603>❌</emoji> Kode kupon tidak valid.
  limit_reached: <emoji id=6298671811345254603>❌</emoji> Kupon ini sudah habis digunakan.
  expired: <emoji id=6298671811345254603>❌</emoji> Kupon ini sudah kedaluwarsa.
  success_applied: <emoji id=6296367896398399651>✅</emoji> Kupon `{code}` berhasil
    digunakan! Harga awal `Rp {original}` menjadi `Rp {final}`.
gift:
  usage_error: '<emoji id=6298671811345254603>❌</emoji> **Target tidak ditemukan.**

    Balas pesan pengguna atau gunakan format:

    `/gift [username] [gift_id]`'
  invalid_id: '<emoji id=6298671811345254603>❌</emoji> **ID Hadiah tidak valid.**

    Gunakan `/listgift` untuk melihat ID.'
  processing: <emoji id=5264727218734524899>🔄</emoji> Memproses pengiriman hadiah...
  not_found: <emoji id=6298671811345254603>❌</emoji> Gift ID `{id}` tidak ditemukan
    atau tidak tersedia.
  sending: '<emoji id=6283073379184415506>🎁</emoji> Mengirim hadiah **Star** (ID:
    `{id}`) ke **{mention}**...'
  success: <emoji id=6296367896398399651>✅</emoji> Berhasil mengirim hadiah ke **{mention}**!
  fail: '<emoji id=6298671811345254603>❌</emoji> Gagal mengirim hadiah: `{e}`'
  list_processing: <emoji id=5264727218734524899>🔄</emoji> Mengambil daftar hadiah...
  list_empty: <emoji id=5258503720928288433>ℹ️</emoji> Tidak ada hadiah yang tersedia
    saat ini.
  info_caption: '<b><emoji id=6283073379184415506>🎁</emoji> Info Hadiah</b>


    <b><emoji id=6269253325477123346>🆔</emoji> ID:</b> <code>{id}</code>

    <b><emoji id=5375296873982604963>💰</emoji> Harga:</b> <code>{price} Stars</code>

    <b><emoji id=5359441070201513074>🎭</emoji> Emoji:</b> {emoji}

    '
  btn_send: 🎁 Kirim ke Teman
  btn_claim: 👤 Klaim Sendiri
  claim_self_success: '<emoji id=6296367896398399651>✅</emoji> Berhasil mengklaim
    hadiah (ID: {id}) untuk diri sendiri!'
  claim_fail: '<emoji id=6298671811345254603>❌</emoji> Gagal klaim: {e}'
  ask_target: '<emoji id=5373012449597335010>👤</emoji> **Kirim Hadiah**


    Silakan kirim **User ID** atau **Username** (@username) tujuan penerima hadiah.'
  cancel_text: <emoji id=6298671811345254603>🚫</emoji> Pengiriman dibatalkan.
  finding_user: <emoji id=5264727218734524899>🔄</emoji> Mencari pengguna `{input}`...
  user_not_found: <emoji id=6298671811345254603>❌</emoji> Pengguna tidak ditemukan.
    Pastikan username/ID benar.
  timeout: <emoji id=5413704112220949842>⏰</emoji> Waktu habis. Silakan ulangi proses.
vvip_status:
  button: 🔍 Cek Status Grup VVIP
  processing: '<emoji id=5451732530048802485>⏳</emoji> Sedang Memeriksa Status Grup...

    Mohon tunggu, proses ini mungkin memakan waktu.'
  header: '<emoji id=6271786398404055377>🕵️</emoji> Laporan Status Grup VVIP


    '
  empty: <emoji id=6298671811345254603>❌</emoji> Belum ada data VVIP.
  entry_normal: '<emoji id=6283073379184415506>📦</emoji> Nama: {name}

    <emoji id=6129870117619634982>💡</emoji> Grup: {title}

    <emoji id=5373052667671093676>🔗</emoji> Link: {link}

    <emoji id=6296367896398399651>✅</emoji> Status: Aman


    '
  entry_banned: '<emoji id=6283073379184415506>📦</emoji> Nama: {name}

    <emoji id=6129870117619634982>💡</emoji> Grup: {title}

    <emoji id=6298671811345254603>⛔</emoji> STATUS: BANNED/DIBATASI

    <emoji id=5334882760735598374>📝</emoji> Alasan: {reason}


    '
  entry_error: '<emoji id=6283073379184415506>📦</emoji> Nama: {name}

    <emoji id=6298671811345254603>❌</emoji> Error: Tidak dapat mengakses grup (ID:
    {chat_id}). Pastikan bot adalah admin.


    '
  done: <emoji id=6296367896398399651>✅</emoji> Pemeriksaan Selesai.
"""

STRINGS = yaml.safe_load(RAW_ID_STRINGS)


def get_string(key):
    node = STRINGS
    for part in key.split('.'):
        if not isinstance(node, dict) or part not in node:
            return f"[{key}]"
        node = node[part]
    return node if isinstance(node, str) else f"[{key}]"


class Language:
    def __init__(self, db, user_id, lang_code='id'):
        self.db = db
        self.user_id = user_id
        self.lang_code = 'id'

    @classmethod
    async def create(cls, db, user_id):
        return cls(db, user_id, 'id')

    def get(self, key, *args, **kwargs):
        raw_string = get_string(key)
        try:
            return raw_string.format(*args, **kwargs)
        except (KeyError, IndexError):
            return raw_string
