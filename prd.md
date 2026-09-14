# MASTER PRD

## VIPBOT — FULL ARCHITECTURAL REWRITE, TELEPROTO MIGRATION & PYTHON ELIMINATION

---

# 1. TUJUAN UTAMA

Lakukan rekonstruksi total terhadap repository VipBot berdasarkan source project yang diberikan.

Repository saat ini memiliki sekitar 64 file Python, berbagai modul domain, helper, payment, bot management, admin, settings, database, serta `run.sh`.

Target akhir bukan sekadar mengganti library Telegram, tetapi melakukan **full migration dan architectural rewrite** dengan ketentuan utama berikut:

1. Seluruh implementasi Telegram harus berfokus pada `teleproto`.
2. Seluruh dependensi, import, abstraction, helper, handler, lifecycle, session, callback, keyboard, update processing, raw API, dan workflow yang sebelumnya bergantung pada Pyrogram atau pyrotgfork harus dihapus atau diganti.
3. Seluruh file Python harus dihapus dari hasil akhir.
4. Seluruh runtime utama harus menggunakan ekosistem TypeScript/JavaScript yang sesuai dengan teleproto.
5. `run.sh` harus ditulis ulang sepenuhnya agar sesuai dengan arsitektur baru.
6. Tidak boleh ada satu pun komentar di source code hasil akhir.
7. Jangan mempertahankan abstraction lama hanya demi kompatibilitas jika abstraction tersebut tidak lagi relevan.
8. Jangan melakukan translasi Python-ke-TypeScript secara mekanis. Rekonstruksi arsitektur berdasarkan kebutuhan aktual aplikasi.
9. Jangan menambahkan fitur baru yang tidak dibutuhkan hanya karena library teleproto menyediakannya.
10. Semua perilaku bisnis yang masih valid harus dipertahankan.
11. Semua bagian yang obsolete, redundant, duplicate, dead code, atau terkait library lama harus dibersihkan.
12. Hasil akhir harus buildable, runnable, testable, dan dapat dioperasikan melalui `run.sh`.

---

# 2. SUMBER KEBENARAN

Gunakan dua sumber utama:

## 2.1 Repository VipBot

Repository yang diberikan pengguna merupakan sumber kebenaran untuk:

* fitur bisnis;
* workflow;
* command;
* callback;
* payment;
* database;
* konfigurasi;
* admin;
* member;
* bot management;
* settings;
* helper;
* scheduler;
* logging;
* monitoring;
* lifecycle;
* integrasi eksternal.

Jangan menghilangkan perilaku hanya karena implementasi lamanya buruk.

Namun, implementasi lama tidak dianggap sebagai desain final.

## 2.2 Teleproto

Gunakan repository resmi:

`https://github.com/sanyok12345/teleproto`

Teleproto menjadi satu-satunya fondasi Telegram client pada hasil akhir.

Pelajari terlebih dahulu:

* struktur package;
* client lifecycle;
* session;
* authentication;
* update system;
* event system;
* middleware;
* handler;
* raw API;
* message operations;
* callback operations;
* keyboard;
* media;
* file transfer;
* error handling;
* connection handling;
* multi-account capability;
* API layer;
* TypeScript typings;
* package exports;
* build system;
* current API layer;
* contoh penggunaan resmi.

Jangan mengandalkan asumsi API dari Pyrogram, pyrotgfork, GramJS versi lama, atau library Telegram lainnya.

---

# 3. ATURAN GLOBAL

Seluruh tahap migration wajib mengikuti policy berikut.

## 3.1 Telegram Policy

Semua interaksi Telegram wajib melalui teleproto.

Dilarang mempertahankan:

* Pyrogram;
* pyrotgfork;
* wrapper Pyrogram;
* compatibility layer Pyrogram;
* helper yang sengaja mempertahankan API Pyrogram;
* adapter yang hanya dibuat untuk menyamarkan penggunaan library lama;
* import Telegram dari library lain;
* dependency Telegram client lain yang tidak diperlukan.

Jika suatu fitur lama tidak tersedia secara langsung, cari padanan teleproto melalui API resminya atau raw MTProto API.

## 3.2 TypeScript Policy

Hasil akhir harus menggunakan TypeScript sebagai bahasa aplikasi utama.

Gunakan struktur yang:

* modular;
* strongly typed;
* asynchronous;
* maintainable;
* testable;
* predictable;
* mudah dikembangkan.

Hindari:

* `any` tanpa alasan kuat;
* global mutable state;
* circular dependency;
* singleton berlebihan;
* business logic di handler;
* database logic di handler;
* Telegram API call tersebar di seluruh project;
* konfigurasi tersebar;
* utility duplikat.

## 3.3 Python Elimination Policy

Pada tahap akhir:

* tidak boleh ada file `.py`;
* tidak boleh ada import Python;
* tidak boleh ada dependency Python;
* tidak boleh ada virtualenv Python;
* tidak boleh ada script Python;
* tidak boleh ada dokumentasi yang menganggap Python sebagai runtime;
* tidak boleh ada konfigurasi deployment yang menjalankan Python;
* tidak boleh ada workflow CI yang menjalankan Python;
* tidak boleh ada referensi pyrotgfork/Pyrogram yang tersisa.

Repository harus diverifikasi menggunakan pencarian menyeluruh, bukan hanya berdasarkan daftar file.

## 3.4 Comment Policy

Source code hasil akhir harus **100% bebas komentar**.

Ini mencakup:

* inline comments;
* block comments;
* TODO;
* FIXME;
* commented-out code;
* explanatory comments;
* generated comments jika dapat dihindari;
* komentar pada configuration source;
* komentar pada shell script.

Kode harus menjelaskan dirinya melalui:

* nama;
* struktur;
* tipe;
* abstraction;
* fungsi;
* module boundary.

Jangan mengganti komentar dengan dokumentasi panjang di dalam source code.

## 3.5 Duplication Policy

Jangan membuat beberapa implementasi untuk kebutuhan yang sama.

Jika terdapat:

* dua logger;
* dua database helper;
* beberapa button builder;
* beberapa parser argument;
* beberapa session manager;
* beberapa API wrapper;
* beberapa retry helper;
* beberapa error mapper;
* beberapa config loader;

gabungkan menjadi satu abstraction yang memiliki tanggung jawab jelas.

Setiap capability harus memiliki satu owner utama.

## 3.6 Responsibility Policy

Setiap module harus memiliki satu tanggung jawab utama.

Pisahkan:

* transport;
* Telegram client;
* handlers;
* business logic;
* persistence;
* external services;
* scheduling;
* configuration;
* security;
* observability.

Handler tidak boleh menjadi tempat seluruh logic aplikasi.

## 3.7 Compatibility Policy

Compatibility hanya dipertahankan jika diperlukan untuk menjaga behavior atau data.

Jangan mempertahankan:

* nama module lama;
* struktur directory lama;
* API internal lama;
* helper lama;
* wrapper lama;

jika semuanya sudah tidak memiliki nilai setelah migrasi.

Compatibility layer tidak boleh menjadi cara untuk membawa arsitektur lama ke project baru.

---

# 4. PHASE 0 — REPOSITORY FORENSICS

Sebelum menulis kode baru, lakukan audit penuh.

Audit seluruh repository:

* directory;
* file;
* import;
* dependency;
* environment;
* workflow;
* database;
* command;
* handler;
* callback;
* scheduler;
* network;
* payment;
* Telegram API;
* external service;
* process lifecycle.

Repository saat ini harus dipetakan secara eksplisit, termasuk area:

* `VvipBot/admin`;
* `VvipBot/allbots`;
* `VvipBot/bot_management`;
* `VvipBot/core`;
* `VvipBot/member`;
* `VvipBot/payment`;
* `VvipBot/send_gift`;
* `VvipBot/settings`;
* `helpers`;
* root-level runtime;
* `bot_manager`;
* database;
* configuration;
* environment;
* `run.sh`.

Buat dependency graph internal secara konseptual sebelum migration.

Identifikasi:

* entry point;
* initialization order;
* Telegram client creation;
* bot creation;
* bot deletion;
* bot extension;
* bot expiration;
* payment flow;
* admin flow;
* member flow;
* settings flow;
* notification flow;
* database lifecycle;
* scheduler lifecycle.

---

# 5. PHASE 1 — BEHAVIOR INVENTORY

Untuk setiap module lama, tentukan:

1. Apa tanggung jawabnya?
2. Siapa yang memanggilnya?
3. Data apa yang diterima?
4. Data apa yang dihasilkan?
5. Apakah berhubungan dengan Telegram?
6. Apakah berhubungan dengan database?
7. Apakah berhubungan dengan external service?
8. Apakah memiliki business rule?
9. Apakah terdapat duplicate implementation?
10. Apakah masih dibutuhkan?
11. Apakah dapat digabung dengan module lain?
12. Apakah harus direstrukturisasi?

Jangan memindahkan file satu per satu secara mekanis.

Setiap file harus masuk ke salah satu keputusan:

* migrate;
* merge;
* redesign;
* replace;
* delete.

---

# 6. PHASE 2 — TELEPROTO RECONNAISSANCE

Pelajari teleproto secara mendalam sebelum implementasi.

Validasi secara aktual:

* package installation;
* client construction;
* session handling;
* connection lifecycle;
* authentication;
* update listeners;
* middleware;
* event builders;
* raw API;
* messages;
* callback queries;
* inline keyboard;
* reply keyboard;
* media;
* upload;
* download;
* entity resolution;
* error types;
* API invocation;
* disconnect;
* reconnect.

Jika dokumentasi dan implementation berbeda, prioritaskan API aktual yang tersedia pada versi package yang digunakan.

Jangan menerjemahkan konsep Pyrogram secara langsung.

---

# 7. PHASE 3 — TARGET ARCHITECTURE

Gunakan architecture baru yang secara konseptual terbagi menjadi:

## Application

Mengatur:

* startup;
* shutdown;
* lifecycle;
* dependency initialization;
* service orchestration.

## Telegram

Mengatur seluruh komunikasi dengan teleproto.

Mencakup:

* client;
* sessions;
* updates;
* event dispatch;
* message operations;
* callback;
* keyboards;
* media;
* raw API;
* Telegram errors.

## Domain

Mengatur business rules.

Contohnya:

* member;
* bot;
* subscription;
* pricing;
* purchase;
* payment;
* seller;
* coupon;
* notification;
* gift.

Domain tidak boleh mengetahui detail implementation teleproto.

## Infrastructure

Mengatur:

* database;
* filesystem;
* HTTP;
* external APIs;
* encryption;
* QR generation;
* scraping;
* storage;
* cache.

## Presentation

Mengatur:

* commands;
* callbacks;
* menus;
* panels;
* responses;
* formatting.

Presentation hanya mengubah input Telegram menjadi application/domain calls dan hasilnya menjadi Telegram response.

---

# 8. PHASE 4 — CORE TELEGRAM LAYER

Buat satu Telegram infrastructure layer.

Layer ini menjadi pintu utama komunikasi aplikasi dengan teleproto.

Tanggung jawab:

* client lifecycle;
* session;
* connection;
* authentication;
* update routing;
* event registration;
* message operations;
* callback operations;
* keyboard construction;
* raw API access;
* media operations;
* Telegram-specific error mapping.

Module lain tidak boleh membuat instance Telegram client secara sembarangan.

Jika aplikasi memiliki banyak bot/account, lifecycle masing-masing instance harus dikelola oleh satu manager.

---

# 9. PHASE 5 — MULTI-BOT MANAGEMENT

Rebuild seluruh lifecycle bot.

Harus terdapat satu mekanisme terpusat untuk:

* register bot;
* load bot;
* start bot;
* stop bot;
* restart bot;
* remove bot;
* check bot status;
* track bot metadata;
* track expiration;
* extend subscription;
* prevent duplicate startup.

Pastikan operasi lifecycle idempotent.

Jika bot sudah aktif, operasi start tidak boleh menciptakan instance kedua.

Jika bot gagal connect, sistem harus memiliki recovery strategy yang konsisten.

---

# 10. PHASE 6 — SESSION MANAGEMENT

Session harus diperlakukan sebagai credential-sensitive state.

Tetapkan satu session abstraction.

Session manager harus menangani:

* creation;
* loading;
* validation;
* persistence;
* rotation;
* deletion;
* failure;
* encryption jika diperlukan;
* multi-account isolation.

Jangan menyebarkan logic session ke handler.

Jangan menyimpan credential secara hardcoded.

---

# 11. PHASE 7 — UPDATE & HANDLER SYSTEM

Bangun handler architecture yang konsisten.

Alur umum:

Telegram update → dispatcher → middleware → handler → application service → domain/infrastructure → response.

Middleware dapat menangani:

* authentication;
* authorization;
* admin check;
* member check;
* rate limiting;
* context creation;
* error boundary.

Handler harus tipis.

Handler tidak boleh berisi:

* SQL kompleks;
* payment verification;
* bot lifecycle logic;
* encryption;
* external API implementation;
* retry engine;
* business rules besar.

---

# 12. PHASE 8 — COMMAND SYSTEM

Inventarisasi seluruh command lama.

Untuk setiap command:

* identifikasi trigger;
* identifikasi authorization;
* identifikasi input;
* identifikasi business operation;
* identifikasi output;
* identifikasi error;
* identifikasi side effect.

Kemudian kelompokkan command berdasarkan domain.

Jangan membuat satu file raksasa berisi seluruh command.

Gunakan registry atau struktur dispatch yang konsisten.

---

# 13. PHASE 9 — CALLBACK & KEYBOARD SYSTEM

Semua inline interaction harus menggunakan satu callback architecture.

Tentukan format callback data secara konsisten.

Callback harus:

* dapat divalidasi;
* memiliki namespace;
* tidak ambigu;
* aman terhadap manipulasi;
* memiliki routing jelas.

Keyboard harus memiliki centralized builder.

Jangan membuat button builder yang sama di banyak module.

Jika terdapat keyboard:

* admin;
* seller;
* member;
* purchase;
* payment;
* settings;
* bot management;

atur berdasarkan domain tetapi gunakan primitive builder yang sama.

---

# 14. PHASE 10 — MESSAGE & RESPONSE SYSTEM

Centralize response construction.

Pisahkan:

* data;
* business result;
* presentation;
* Telegram transport.

Gunakan format response yang konsisten.

Error response juga harus konsisten.

Jangan setiap handler memiliki gaya error dan success message yang berbeda tanpa alasan bisnis.

---

# 15. PHASE 11 — DATABASE REBUILD

Audit seluruh akses database.

Identifikasi:

* schema;
* table;
* query;
* transaction;
* relation;
* index;
* migration;
* connection lifecycle;
* duplicate query;
* race condition.

Pisahkan:

Database connection → repository → service/domain.

Jangan menaruh SQL langsung di Telegram handler.

Gabungkan query yang sama.

Gunakan transaction boundary pada operasi yang mengubah beberapa entitas sekaligus.

---

# 16. PHASE 12 — PAYMENT

Payment adalah domain sensitif dan harus direstrukturisasi secara terpisah.

Audit:

* invoice;
* price;
* Stars;
* callback;
* verification;
* confirmation;
* payment state;
* expiration;
* duplicate payment;
* notification.

Payment operation harus idempotent.

Jangan menganggap callback sebagai bukti pembayaran tanpa validasi.

Pisahkan:

Payment provider interaction → verification → domain transaction → persistence → notification.

Jika payment berhasil, state database harus konsisten walaupun notification gagal.

---

# 17. PHASE 13 — BOT MANAGEMENT DOMAIN

Rebuild fitur:

* creation;
* deletion;
* listing;
* detail;
* duration;
* extension;
* pricing;
* purchase.

Gunakan satu domain service untuk lifecycle bisnis bot.

Jangan mengulang logic expiration atau pricing di beberapa handler.

Expiration calculation harus memiliki satu sumber kebenaran.

---

# 18. PHASE 14 — MEMBER & ADMIN

Pisahkan authorization dari presentation.

Tentukan role dan permission secara eksplisit.

Admin features harus menggunakan authorization service.

Member features harus menggunakan member service.

Seller features harus menggunakan seller service.

Jangan menggunakan pengecekan role yang tersebar secara manual di setiap handler.

---

# 19. PHASE 15 — SETTINGS

Rebuild seluruh settings berdasarkan domain.

Audit:

* API settings;
* pricing;
* coupons;
* notification;
* broadcast;
* panel;
* revenue.

Pisahkan:

* configuration;
* persistent settings;
* runtime settings;
* user preferences.

Hindari satu object settings raksasa yang mengandung seluruh state aplikasi.

---

# 20. PHASE 16 — HELPERS CONSOLIDATION

Seluruh folder helper harus diaudit secara agresif.

Kelompokkan berdasarkan fungsi nyata.

Gabungkan helper yang memiliki tujuan sama.

Periksa secara khusus:

* argument parsing;
* button;
* colorization;
* dashboard generation;
* database;
* emoji parsing;
* encryption;
* faker;
* gradient;
* listener;
* logger;
* monitor;
* QR;
* scheduler;
* storage;
* YAML;
* external service utilities.

Jangan mempertahankan folder `helpers` sebagai tempat sampah.

Jika sebuah utility hanya digunakan satu domain dan bukan utility umum, pindahkan ke domain tersebut.

---

# 21. PHASE 17 — EXTERNAL SERVICES

Setiap external integration harus memiliki adapter/service sendiri.

Termasuk bila repository menggunakan:

* HTTP API;
* payment service;
* QR service;
* scraping;
* notification provider;
* storage;
* third-party API.

Tetapkan:

* timeout;
* retry;
* error mapping;
* response validation;
* rate limiting bila diperlukan.

Jangan menyebarkan HTTP request langsung ke berbagai handler.

---

# 22. PHASE 18 — ERROR ARCHITECTURE

Buat error taxonomy yang konsisten.

Bedakan:

* validation error;
* authorization error;
* not found;
* conflict;
* Telegram error;
* network error;
* payment error;
* database error;
* configuration error;
* internal error.

Error harus diterjemahkan pada boundary yang tepat.

Jangan menelan error secara diam-diam.

Jangan menggunakan catch-all tanpa logging dan classification.

---

# 23. PHASE 19 — LOGGING & OBSERVABILITY

Buat satu logging system.

Log harus menyediakan context yang cukup untuk:

* startup;
* shutdown;
* bot lifecycle;
* Telegram update;
* payment;
* database failure;
* external service failure;
* scheduler;
* authentication.

Jangan membuat beberapa logger dengan format berbeda.

Jangan mencatat:

* token;
* session;
* password;
* API secret;
* private credential;
* sensitive payment data.

---

# 24. PHASE 20 — CONFIGURATION

Buat centralized configuration layer.

Configuration harus membedakan:

* required;
* optional;
* default;
* secret;
* runtime;
* environment-specific.

Validasi configuration saat startup.

Jika configuration invalid, application harus gagal secara jelas dan deterministic.

Jangan membaca environment variable secara acak dari seluruh module.

---

# 25. PHASE 21 — SECURITY

Audit seluruh repository untuk:

* credential exposure;
* token leakage;
* insecure session storage;
* unsafe file permissions;
* command injection;
* arbitrary path access;
* unsafe HTTP handling;
* unvalidated callback;
* privilege escalation;
* SQL injection;
* unsafe deserialization.

Semua security-sensitive operation harus memiliki satu implementation owner.

---

# 26. PHASE 22 — SCHEDULER

Buat satu scheduler abstraction.

Gunakan scheduler untuk:

* expiration;
* cleanup;
* recurring maintenance;
* notification;
* periodic verification.

Jangan membuat timer tersebar di banyak module.

Scheduler harus:

* dapat dihentikan;
* tidak menggandakan job;
* menangani failure;
* memiliki lifecycle yang jelas.

---

# 27. PHASE 23 — CACHE & STATE

Audit seluruh cache dan temporary state.

Bedakan:

* persistent state;
* process state;
* cache;
* session;
* temporary state.

Jangan menggunakan global object sebagai database.

Jika state harus survive restart, simpan pada persistent storage.

Jika state hanya temporary, pastikan cleanup tersedia.

---

# 28. PHASE 24 — PACKAGE & PROJECT STRUCTURE

Susun repository agar struktur mencerminkan arsitektur.

Jangan mempertahankan struktur Python lama hanya karena familiar.

Target structure harus:

* mudah dinavigasi;
* memiliki dependency direction jelas;
* memisahkan domain dan infrastructure;
* memiliki satu entry point;
* memiliki satu configuration system;
* memiliki satu Telegram layer;
* memiliki satu persistence layer.

Nama module harus menggambarkan tanggung jawabnya.

---

# 29. PHASE 25 — DEPENDENCY CLEANUP

Audit semua dependency lama.

Hapus dependency yang hanya digunakan oleh:

* Python;
* Pyrogram;
* pyrotgfork;
* obsolete helper;
* obsolete runtime.

Tambahkan hanya dependency yang benar-benar dibutuhkan oleh target architecture.

Jangan membawa dependency lama hanya karena sebelumnya digunakan.

Package manifest harus merepresentasikan dependency aktual.

---

# 30. PHASE 26 — README & DOCUMENTATION

Setelah migration selesai, update dokumentasi agar tidak ada asumsi bahwa aplikasi masih Python.

Dokumentasi harus menggambarkan:

* architecture;
* installation;
* configuration;
* runtime;
* database;
* session;
* bot lifecycle;
* deployment;
* troubleshooting.

Jangan meninggalkan instruksi Pyrogram atau pyrotgfork.

---

# 31. PHASE 27 — RUN.SH TOTAL REWRITE

`run.sh` harus dirombak total.

Jangan patch script lama sedikit demi sedikit.

Script baru harus bertanggung jawab atas:

1. validasi environment;
2. validasi dependency;
3. validasi configuration;
4. persiapan runtime;
5. persiapan database jika diperlukan;
6. build;
7. start;
8. signal forwarding;
9. shutdown;
10. failure handling.

`run.sh` tidak boleh:

* menjalankan Python;
* membuat virtualenv Python;
* menginstall dependency Python;
* menjalankan Pyrogram;
* menjalankan pyrotgfork;
* mengandalkan struktur runtime lama.

Script harus aman dijalankan berulang kali.

---

# 32. PHASE 28 — CI/CD CLEANUP

Audit seluruh workflow CI.

Hapus workflow yang hanya relevan untuk Python.

Ganti dengan pipeline yang memvalidasi:

* dependency installation;
* formatting;
* type checking;
* linting;
* build;
* tests;
* prohibited dependency scan;
* Python file scan;
* comment scan;
* Pyrogram/pyrotgfork reference scan.

---

# 33. PHASE 29 — TESTING STRATEGY

Testing harus mengikuti domain, bukan struktur file lama.

Minimal validasi:

## Telegram

* client initialization;
* session;
* update handling;
* command;
* callback;
* keyboard;
* message;
* raw API;
* reconnect.

## Bot

* creation;
* startup;
* shutdown;
* deletion;
* extension;
* expiration;
* duplicate prevention.

## Member

* registration;
* lookup;
* authorization;
* role.

## Payment

* invoice;
* verification;
* duplicate prevention;
* transaction consistency;
* failure recovery.

## Database

* connection;
* transaction;
* repository;
* migration.

## Scheduler

* registration;
* execution;
* failure;
* shutdown.

## Configuration

* valid configuration;
* missing secret;
* invalid value;
* environment override.

---

# 34. PHASE 30 — MIGRATION VALIDATION

Setelah implementasi selesai, lakukan static verification.

Cari seluruh repository untuk:

* `.py`;
* `import pyrogram`;
* `from pyrogram`;
* `pyrotgfork`;
* `pyrogram`;
* Python executable;
* Python package manager;
* virtualenv;
* obsolete Telegram wrapper;
* commented-out code;
* TODO;
* FIXME;
* duplicate Telegram client;
* duplicate database implementation;
* duplicate configuration loader.

Semua hasil yang tidak sesuai harus diperbaiki sebelum dianggap selesai.

---

# 35. PHASE 31 — BEHAVIOR PARITY

Bandingkan behavior lama dengan behavior baru.

Untuk setiap fitur:

OLD BEHAVIOR → TARGET BEHAVIOR → VALIDATION.

Validasi terutama:

* command;
* button;
* callback;
* payment;
* admin;
* member;
* seller;
* bot management;
* settings;
* notification;
* scheduler.

Perubahan implementation diperbolehkan.

Perubahan behavior hanya boleh terjadi jika memang diperlukan karena perubahan architecture atau keamanan.

---

# 36. PHASE 32 — DATA SAFETY

Migration tidak boleh merusak data existing.

Sebelum mengubah persistence:

* pahami schema lama;
* pahami format data;
* identifikasi credential;
* identifikasi session;
* identifikasi relationship;
* identifikasi migration requirement.

Jika schema berubah, sediakan migration strategy.

Jangan menghapus data production sebagai bagian dari refactor.

---

# 37. PHASE 33 — LIFECYCLE VALIDATION

Uji seluruh lifecycle:

START

→ load configuration

→ initialize infrastructure

→ initialize database

→ initialize Telegram layer

→ load bot/session

→ register handlers

→ start clients

→ application ready

SHUTDOWN

→ stop scheduler

→ stop accepting new work

→ stop Telegram clients

→ flush resources

→ close database

→ exit cleanly.

Tidak boleh terdapat resource leak.

---

# 38. PHASE 34 — FAILURE VALIDATION

Uji kondisi:

* invalid configuration;
* missing environment;
* database unavailable;
* Telegram unavailable;
* authentication failure;
* bot disconnect;
* payment failure;
* external API timeout;
* malformed callback;
* invalid user input;
* duplicate request;
* duplicate payment;
* process restart.

Pastikan failure pada satu subsystem tidak menyebabkan state aplikasi menjadi corrupt.

---

# 39. PHASE 35 — CODE QUALITY

Setiap module final harus diperiksa untuk:

* duplicate logic;
* unnecessary abstraction;
* dead code;
* unreachable code;
* unused dependency;
* unused import;
* unclear responsibility;
* excessive coupling;
* circular dependency;
* hidden side effect;
* global mutable state.

Jangan mengoptimalkan hanya berdasarkan jumlah file.

Targetnya adalah **coherent architecture**, bukan sekadar repository yang lebih kecil.

---

# 40. PHASE 36 — FINAL FILE ELIMINATION

Setelah migration selesai, hapus seluruh file Python.

Jangan meninggalkan:

* `__init__.py`;
* migration helper Python;
* old scripts;
* backup `.py`;
* test Python;
* temporary Python file;
* compatibility Python file.

Pastikan penghapusan dilakukan setelah seluruh dependency terhadap file tersebut telah dipindahkan.

---

# 41. PHASE 37 — FINAL TELEPROTO AUDIT

Lakukan audit akhir khusus Telegram.

Pastikan seluruh Telegram interaction menggunakan teleproto.

Verifikasi:

* client;
* session;
* authentication;
* events;
* updates;
* middleware;
* handlers;
* messages;
* callback;
* keyboard;
* media;
* raw API;
* lifecycle;
* error handling.

Tidak boleh ada library Telegram lain yang tersisa tanpa alasan yang benar-benar diperlukan.

Pyrogram dan pyrotgfork harus dianggap forbidden dependency.

---

# 42. PHASE 38 — FINAL RUN.SH AUDIT

Periksa `run.sh` dari awal hingga akhir.

Pastikan script:

* sesuai runtime baru;
* tidak memiliki dependency Python;
* tidak mengandung komentar;
* tidak menjalankan obsolete entry point;
* dapat menjalankan application dari clean environment;
* gagal dengan jelas ketika prerequisite tidak tersedia;
* meneruskan termination signal;
* tidak membuat process zombie;
* dapat digunakan pada deployment environment target.

---

# 43. PHASE 39 — CLEAN REPOSITORY TEST

Buat kondisi seolah-olah repository baru saja di-clone.

Mulai dari environment bersih.

Kemudian:

1. install dependency;
2. konfigurasi environment;
3. siapkan database;
4. build project;
5. jalankan `run.sh`;
6. pastikan application start;
7. pastikan Telegram client connect;
8. pastikan handler aktif;
9. jalankan smoke test;
10. shutdown;
11. jalankan kembali.

Tidak boleh bergantung pada file lokal yang tidak dideklarasikan.

---

# 44. PHASE 40 — FINAL ACCEPTANCE GATE

Migration hanya dianggap selesai jika seluruh kondisi berikut terpenuhi:

### Architecture

* target architecture diterapkan;
* dependency direction jelas;
* domain terisolasi;
* Telegram layer terpusat;
* persistence terpusat;
* external service terisolasi.

### Telegram

* teleproto menjadi fondasi Telegram;
* Pyrogram tidak digunakan;
* pyrotgfork tidak digunakan;
* tidak ada compatibility layer lama;
* lifecycle client benar.

### Python

* tidak ada file `.py`;
* tidak ada Python runtime;
* tidak ada Python dependency;
* tidak ada Python CI workflow.

### Code

* tidak ada komentar;
* tidak ada commented-out code;
* tidak ada TODO/FIXME;
* tidak ada dead code penting;
* tidak ada duplicate implementation yang tidak diperlukan.

### Business

* bot management berfungsi;
* member berfungsi;
* admin berfungsi;
* seller berfungsi;
* payment berfungsi;
* settings berfungsi;
* notification berfungsi;
* scheduler berfungsi.

### Infrastructure

* database berfungsi;
* configuration berfungsi;
* logging berfungsi;
* error handling berfungsi;
* external service handling berfungsi.

### Runtime

* build berhasil;
* clean install berhasil;
* `run.sh` berhasil;
* startup berhasil;
* shutdown berhasil;
* restart berhasil.

---

# 45. ATURAN PRIORITAS JIKA TERJADI KONFLIK

Jika terdapat konflik keputusan selama migration, gunakan prioritas berikut:

1. Security.
2. Data integrity.
3. Teleproto compatibility.
4. Correct business behavior.
5. Architectural consistency.
6. Maintainability.
7. Performance.
8. Backward compatibility terhadap implementation internal lama.

Jangan mempertahankan implementation lama jika bertentangan dengan architecture baru.

---

# 46. METODE EKSEKUSI AGENT

Coding agent harus bekerja secara bertahap.

## Step A — Audit

Jangan langsung mengedit source.

Petakan repository dan dependency.

## Step B — Design

Tentukan target architecture dan migration mapping.

## Step C — Foundation

Bangun:

* configuration;
* infrastructure;
* Telegram core;
* database;
* lifecycle.

## Step D — Domain

Migrasikan domain satu per satu.

Urutan yang direkomendasikan:

1. core;
2. member;
3. bot management;
4. payment;
5. admin;
6. settings;
7. notifications;
8. scheduler;
9. external integrations.

## Step E — Presentation

Migrasikan:

* commands;
* callbacks;
* keyboards;
* menus;
* responses.

## Step F — Cleanup

Hapus:

* Python;
* Pyrogram;
* pyrotgfork;
* obsolete helper;
* duplicate implementation;
* dead code.

## Step G — Runtime

Rewrite `run.sh`.

## Step H — Validation

Build, test, scan, dan clean-install.

## Step I — Final Audit

Pastikan seluruh acceptance gate terpenuhi.

---

# 47. LARANGAN ABSOLUT

Jangan:

* mempertahankan Pyrogram;
* mempertahankan pyrotgfork;
* membuat adapter Pyrogram;
* menerjemahkan seluruh Python menjadi TypeScript baris demi baris;
* mempertahankan duplicate abstraction;
* membuat Telegram client di banyak tempat;
* menaruh business logic di handler;
* menaruh SQL di handler;
* menyebarkan configuration access;
* menyimpan credential hardcoded;
* meninggalkan file Python;
* meninggalkan Python workflow;
* meninggalkan komentar source code;
* meninggalkan commented-out code;
* menambahkan dependency tanpa kebutuhan;
* menghapus behavior bisnis tanpa audit;
* mengubah database tanpa memahami data existing;
* membuat migration hanya berdasarkan nama file;
* menganggap build sukses sebagai bukti migration selesai.

---

# 48. HASIL AKHIR YANG DIHARAPKAN

Hasil akhir harus berupa repository VipBot yang secara konseptual merupakan aplikasi baru yang:

* menggunakan TypeScript;
* menggunakan teleproto sebagai Telegram foundation;
* tidak bergantung pada Pyrogram;
* tidak bergantung pada pyrotgfork;
* tidak memiliki Python;
* memiliki architecture modular;
* memiliki centralized Telegram infrastructure;
* memiliki centralized persistence;
* memiliki domain services;
* memiliki handler tipis;
* memiliki lifecycle yang jelas;
* memiliki error architecture;
* memiliki security boundary;
* memiliki payment architecture yang idempotent;
* memiliki multi-bot lifecycle yang aman;
* memiliki scheduler terpusat;
* memiliki configuration terpusat;
* memiliki logging terpusat;
* memiliki test strategy;
* memiliki deployment workflow baru;
* memiliki `run.sh` baru;
* tidak memiliki komentar pada source code;
* tidak memiliki duplicate implementation yang tidak diperlukan.

---

# 49. FINAL REPORT AGENT

Setelah seluruh pekerjaan selesai, agent harus melaporkan:

1. architecture final;
2. struktur directory final;
3. module yang digabung;
4. module yang dihapus;
5. module yang direwrite;
6. mapping fitur lama ke implementation baru;
7. penggunaan teleproto;
8. dependency yang dihapus;
9. dependency yang ditambahkan;
10. database migration yang dilakukan;
11. perubahan lifecycle;
12. perubahan `run.sh`;
13. hasil build;
14. hasil test;
15. hasil clean-install;
16. hasil scan Python;
17. hasil scan Pyrogram;
18. hasil scan pyrotgfork;
19. hasil scan komentar;
20. sisa risiko jika ada.

Jangan menyatakan migration selesai hanya karena source berhasil dikompilasi.

Migration selesai hanya jika seluruh behavior, architecture, runtime, dependency, security, dan cleanup telah lolos final acceptance gate.

# 50. DEFINISI SELESAI

Definisi akhir dari project ini adalah:

**VipBot telah direkonstruksi dari implementation Python lama menjadi aplikasi TypeScript berbasis teleproto dengan architecture baru yang bersih, seluruh dependency Pyrogram/pyrotgfork telah dieliminasi, seluruh file Python telah dihapus, `run.sh` telah ditulis ulang, source code tidak memiliki komentar, duplicate implementation telah dikonsolidasikan, seluruh business behavior penting telah dipertahankan, dan repository dapat dibangun serta dijalankan dari environment bersih.**
