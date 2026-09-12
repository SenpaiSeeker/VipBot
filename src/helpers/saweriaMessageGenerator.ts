const _GREETINGS = [
    "Halo", "Hi", "Hello", "Hoi", "Woi", "Uy", "P", "Ping", "Tes", "Cek",
    "Spada", "Punten", "Permisi", "Misi", "Lapor", "Izin", "Numpang", "Salam",
    "Greetings", "Hola", "Aloha", "Bonjour", "Shalom", "Om swastiastu",
    "Namo Buddhaya", "Salam sejahtera", "Kulonuwun", "Sampurasun", "Horas",
    "Nengah", "Kompe", "Ampure", "Assalamualaikum", "Pagi", "Siang", "Sore",
    "Malam", "Met pagi", "Met siang", "Met sore", "Met malam", "Met malem",
    "Oy", "Euy", "Cuy", "Bre", "Woy", "Yuhu", "Yahallo", "Hehe", "Wkwk",
    "Wkwkwk", "Haha", "Hihi", "Yoo", "Hellow", "Alow", "Lur", "Gan", "Agan",
    "Min", "Admin", "Momod", "Mimin", "Pg", "Sg", "Mlm", "Mlem", "Mpls",
    "Sup", "Sup boss", "Excuse me", "Konbanwa", "Ohayo", "Ohayou",
    "Moshi moshi", "Hai hai", "Hiy", "Hy", "Hlo", "Hadeh", "Haduh",
    "Mantap", "Markotop", "Josss", "Gas", "Gaskeun", "Skuy", "Yuk",
];

const _NICKNAMES = [
    "Bang", "Mas", "Kak", "Min", "Om", "Pak", "Bu", "Sis", "Mam", "Pap",
    "Gan", "Agan", "Bro", "Brow", "Bray", "Cuy", "Sob", "Sobat", "Kawan",
    "Teman", "Lur", "Dulur", "Ndang", "Ngab", "Bre", "Warga", "Jamaah",
    "Pack", "Mank", "Bestie", "Besti", "Best", "Bebs", "Beb", "Sayang",
    "Say", "Cantik", "Ganteng", "Suhu", "Sepuh", "Mastah", "Master",
    "Idola", "Panutan", "Legend", "Legends", "Boss", "Bos", "Bosque",
    "Juragan", "Jurgan", "Sultan", "Raja", "Ratu", "Dewa", "Dewi", "Nder",
    "Bli", "Uda", "Cici", "Koko", "Abang", "Akang", "Aa", "Teteh", "Mbak",
    "Neng", "Uni", "Mamank", "Mpok", "Bude", "Pakde", "Tante", "Paman",
    "Bibi", "Admin", "Mimin", "Momod", "Lord", "King", "Queen", "Datuk",
    "Sensei", "Senpai", "Kohai", "Coach", "Kapten", "Komandan", "Chief",
    "Head", "Leader", "Presiden", "Menteri", "Jenderal", "Pinter", "Pintar",
    "Pandai", "Soleh", "Solehah", "Struggler", "Pejuang", "Pencari rezeki",
    "Rezeki",
];

const _GIVING_VERBS = [
    "Traktir", "Ngasih", "Kirim", "Bagi", "Share", "Bagi-bagi", "Support",
    "Dukung", "Dukung terus", "Support terus", "Semangatin", "Nyawer",
    "Sawer", "Donasi", "Donate", "Sedekah", "Infaq", "Sodaqoh", "Wakaf",
    "Amal", "Bersedekah", "Berkah", "Titip", "Nitip", "Sumbang", "Gift",
    "Ngegift", "Kasih", "Jajanin", "Nambahin", "Bantu", "Bantuin",
    "Cemplungin", "Lempar", "Sisihin", "Nyalurin", "Topup", "Isi",
    "Suntik", "Inject", "Ngedukung", "Nyumbang", "Nraktir", "Cendolin",
    "Drop", "Setor", "Deposit", "Simpan", "Tabung", "Invest", "Transfer",
    "TF", "Kirimim", "Kasihim", "Buat", "Bikin", "Sediain",
    "Transfer energi", "Berbagi", "Menyapa", "Mampir", "Lewat", "Betah",
    "Ayam", "Serok", "Gembok", "Panci", "Wajib",
];

const _OBJECTS = [
    "kopi", "kopi hitam", "kopi susu", "kopi kenangan", "janji jiwa",
    "teh manis", "es teh", "es teh manis", "boba", "bubble tea", "matcha",
    "gorengan", "bakwan", "tahu isi", "tahu bulat", "cireng", "bala-bala",
    "seblak", "seblak ceker", "bakso", "bakso urat", "bakso malang",
    "mie ayam", "mie ayam bakso", "mie goreng", "indomie", "indomie goreng",
    "indomie rebus", "soto", "soto ayam", "soto betawi", "rawon",
    "nasi goreng", "nasgor", "nasi uduk", "nasi rames", "nasi padang",
    "sate", "sate ayam", "sate kambing", "sate padang", "tongseng",
    "martabak", "martabak manis", "martabak telur", "terang bulan",
    "siomay", "batagor", "pempek", "pempek kapal selam", "ketoprak",
    "gado-gado", "pecel", "pecel lele", "ayam geprek", "ayam goreng",
    "ayam bakar", "ikan bakar", "ikan goreng", "jus", "jus jeruk",
    "jus alpukat", "jus mangga", "susu", "susu coklat", "air putih",
    "mineral", "air galon", "es krim", "mixue", "chatime", "starbucks",
    "kfc", "mcd", "pizza", "burger", "kentang goreng", "cemilan",
    "kerupuk", "keripik", "cilok", "cimol", "colenak", "roti bakar",
    "pisang goreng", "pisang coklat", "kue", "donat", "brownies",
    "uang rokok", "rokok", "surya", "sampoerna", "magnum", "gudang garam",
    "bensin", "pertalite", "pertamax", "solar", "gas 3kg", "gas melon",
    "kuota", "pulsa", "listrik", "token listrik", "token", "pdam",
    "diamond", "dm", "diamond ml", "diamond ff", "uc", "pubgm",
    "mobile legends", "free fire", "valorant", "genshin", "prime",
    "steam wallet", "gplay", "google play", "voucher", "top up", "skin",
    "bundle", "starlight", "jajan", "dana", "saldo", "gopay", "ovo",
    "shopeepay", "linkaja", "modal", "amunisi", "energi", "gizi",
    "vitamin", "suplemen", "uang kaget", "receh", "kembalian", "sangu",
    "sangu bulanan", "thr", "angpao", "uang jajan", "kas", "tabungan",
    "celengan", "uang kopi", "uang bensin", "uang makan", "uang saku",
    "nafkah", "uang parkir", "uang kas", "uang keamanan", "uang lelah",
    "tip", "gaji", "bonus", "tunjangan", "fee", "upah", "hasil sawer",
    "buket", "bunga", "kadokado", "kado", "hadiah", "oleh-oleh",
    "buah tangan", "souvenir", "bungkus", "nasi bungkus", "warung",
    "ngemil", "ngopi", "nongki", "nongkrong", "segaran", "segarsegar",
    "fresh", "healing", "liburan", "piknik",
];

const _BLESSINGS = [
    "semangat", "semangat terus", "jangan menyerah", "fighting", "gas terus",
    "sukses", "sukses selalu", "sukses berkah", "maju terus", "jaya",
    "sehat", "sehat selalu", "sehat wal afiat", "panjang umur", "kuat",
    "lancar", "lancar jodoh", "lancar rezeki", "murah rezeki", "berkah",
    "bahagia", "happy", "senang", "gembira", "santuy", "kalem", "rileks",
    "mantap", "mantul", "mantap jiwa", "keren", "ganteng", "cantik",
    "gacor", "menyala", "joss", "josss", "top", "markotop", "markesot",
    "gokil", "gila", "wuenak", "sop trik", "cool", "nice", "nice inpoh",
    "good luck", "best", "the best", "terbaik", "juara", "legend",
    "panutan", "idola", "inspiratif", "produktif", "kreatif", "muda",
    "hoki", "cuan", "profit", "stonks", "laris", "manis", "kaya",
    "makmur", "berlimpah", "barokah", "mabrur", "amanah", "ikhlas",
    "tawakal", "istiqomah", "bersyukur", "syukur", "sakinah", "mawaddah",
    "warahmah", "gandoss", "savage", "gg", "ggwp", "wp", "op", "imba",
    "anjay", "anjim", "kece", "kece badai", "sipp", "sip", "oki",
    "oki sip", "sip lah", "yoi", "yoi bos", "siapp", "siap", "oke",
    "oke gas", "oke sipp", "solved", "fix", "no drama", "valid", "no debat",
];

const _THANKS = [
    "makasih", "terima kasih", "thanks", "thank you", "thank u", "ty",
    "tysm", "thx", "tq", "tx", "mksh", "mksih", "makasih banyak", "suwun",
    "hatur nuhun", "matur nuwun", "nuwun", "sakalangkong", "tengkyu",
    "tararengkyu", "nuhun", "arigato", "arigatou", "kamsia", "xie xie",
    "gracias", "danke", "kamsahamnida", "merci", "salamat", "tenkyu",
    "tengkyu berat", "thanks berat", "appreciate it", "big thanks",
    "thanks a lot", "many thanks", "cheers", "cheers mate", "peace",
    "salim", "sungkem", "pasrah", "langgeng", "aman", "ashiap", "woke",
    "ok",
];

const _PARTICLES = [
    "ya", "yah", "iya", "nah", "nih", "tuh", "dong", "donk", "dunk",
    "banget", "bgt", "parah", "sih", "deh", "lah", "kah", "kok", "anjay",
    "woi", "woy", "cuy", "bre", "bro", "sist", "bestie", "terus",
    "selalu", "mulu", "lagi", "juga", "pun", "doang", "cuma", "dikit",
    "lumayan", "buat", "untuk", "biar", "agar", "supaya", "saja", "aja",
    "sok atuh", "atuh", "mah", "teh", "rek", "cok", "lur", "bos",
    "bosku", "juragan", "sekarang", "nanti", "besok", "kemarin", "tadi",
    "barusan", "ala kadarnya", "seikhlasnya", "hati-hati", "santai",
    "gas", "kecil kecilan", "tipis tipis", "seadanya", "apa adanya",
    "iseng", "gabut", "daripada luang", "sambil lewat", "sadboy", "yuk",
    "kuy", "skuy", "gaskeun", "sikat", "crot", "edm", "wkwk", "hehe",
    "lol", "haha", "hihi", "sad", "cry",
];

const _EMOJIS = [
    "😊", "😇", "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗",
    "😙", "😚", "😋", "😛", "😝", "😜", "🤪", "🤨", "🧐", "🤓",
    "😎", "🤩", "🥳", "😏", "😒", "😞", "😔", "😟", "😕", "🙁",
    "☹️", "😣", "😖", "😫", "😩", "🥺", "😢", "😭", "😤", "😠",
    "😡", "🤬", "🤯", "😳", "🥵", "🥶", "😱", "😨", "😰", "😥",
    "🤗", "🤔", "🤭", "🤫", "🤥", "😶", "😐", "😑", "😬", "🙄",
    "😯", "😦", "😧", "😮", "😲", "🥱", "😴", "🤤", "😪", "😵",
    "🤐", "🥴", "🤢", "🤮", "🤧", "😷", "🤒", "🤕", "🤑", "🤠",
    "👋", "🤚", "🖐️", "✋", "🖖", "👌", "🤌", "🤏", "✌️", "🤞",
    "🤟", "🤘", "🤙", "👈", "👉", "👆", "🖕", "👇", "☝️", "👍",
    "👎", "✊", "👊", "🤛", "🤜", "👏", "🙌", "👐", "🤲", "🤝",
    "🙏", "✍️", "💅", "🤳", "💪", "🦾", "🦿", "🦵", "🦶", "👂",
    "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔",
    "❣️", "💕", "💞", "💓", "💗", "💖", "💘", "💝", "💟", "♥️",
    "💌", "💤", "💢", "💣", "💥", "💨", "💦", "💫", "💬", "💭",
    "🗯️", "♠️", "♣️", "♦️", "🃏", "🎴", "🀄", "🕐", "🕑", "☕",
    "🍵", "🥤", "🧋", "🍶", "🍾", "🍷", "🍸", "🍹", "🍺", "🍻",
    "🥂", "🥃", "🥡", "🥢", "🍽️", "🍴", "🥄", "🔪", "🏺", "🌽",
    "🍠", "🍯", "🍼", "🥛", "🧉", "🫖", "🧃", "🍱", "🍘", "🍙",
    "🍚", "🍛", "🍜", "🍝", "🍢", "🍣", "🍤", "🍥", "🥮", "🍡",
    "🥟", "🥠", "🍦", "🍧", "🍨", "🍩", "🍪", "🎂", "🍰", "🧁",
    "🥧", "🍫", "🍬", "🍭", "🍮", "🐶", "🐱", "🐭", "🐹", "🐰",
    "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐮", "🐷", "🐽", "🐸",
    "🐵", "🙈", "🙉", "🙊", "🐒", "🐔", "🐧", "🐦", "🐤", "🐣",
    "🐥", "🦆", "🦅", "🦉", "🦇", "🐺", "🐗", "🐴", "🦄", "🐝",
    "🐛", "🦋", "🐌", "🐞", "🐜", "🦟", "🦗", "🕷️", "🕸️", "🦂",
    "🐢", "🐍", "🦎", "🦖", "🦕", "🐙", "🦑", "🦐", "🦞", "🦀",
    "🐡", "🐠", "🐟", "🐬", "🐳", "🐋", "🦈", "🐊", "🐅", "🐆",
    "🦓", "🦍", "🦧", "🦣", "🐘", "🦛", "🦏", "🐪", "🐫", "🦒",
    "🦘", "🦬", "🐃", "🐂", "🐄", "🐎", "🐖", "🐏", "🐑", "🦙",
    "🐐", "🦌", "🐕", "🐩", "🦮", "🐈", "🐓", "🦃", "🦤", "🦚",
    "🦜", "🦢", "🦩", "🕊️", "🐇", "🦝", "🦨", "🦡", "🦦", "🦥",
    "🐁", "🐀", "🐿️", "🦔", "🐾", "🌸", "💮", "🏵️", "🌹", "🥀",
    "🌺", "🌻", "🌼", "🌷", "🌱", "🪴", "🌲", "🌳", "🌴", "🌵",
    "🌾", "🌿", "☘️", "🍀", "🍁", "🍂", "🍃", "🍄", "🐚", "💐",
    "⚽", "🏀", "🏈", "⚾", "🥎", "🎾", "🏐", "🏉", "🥏", "🎱",
    "🪀", "🏓", "🏸", "🏒", "🏑", "🥍", "🏏", "🪃", "🥅", "⛳",
    "🪁", "🏹", "🎣", "🤿", "🥊", "🥋", "🎽", "🛹", "🛼", "🛷",
    "⛸️", "🥌", "🎿", "⛷️", "🏂", "🪂", "🏋️", "🤼", "🤸", "🤺",
    "⛹️", "🤾", "🏌️", "🏇", "🧘", "🏄", "🏊", "🤽", "🚣", "🧗",
    "💎", "💰", "💴", "💵", "💶", "💷", "💸", "💳", "🧾", "💹",
    "✉️", "📩", "📨", "📧", "📥", "📤", "📦", "🏷️", "📪", "📫",
    "📬", "📭", "📮", "📯", "📜", "📃", "📄", "📑", "📊", "📈",
    "📉", "🗒️", "🗓️", "📆", "📅", "🗑️", "📇", "🗃️", "🗳️", "🗄️",
    "📋", "📁", "📂", "🗂️", "🗞️", "📰", "📓", "📔", "📒", "📕",
    "📗", "📘", "📙", "📚", "📖", "🔖", "🧷", "🔗", "📎", "🖇️",
    "📐", "📏", "🧮", "📌", "📍", "✂️", "🖊️", "🖋️", "✒️", "🖌️",
    "🖍️", "📝", "✏️", "🔍", "🔎", "🔏", "🔐", "🔒", "🔓", "🚀",
    "🛸", "🚁", "🛶", "⛵", "🚤", "🛥️", "🛳️", "⛴️", "🚢", "✈️",
    "🛩️", "🛫", "🛬", "💺", "🚟", "🚠", "🚡", "🚇", "🚝", "🚋",
    "🚃", "🚄", "🚅", "🚈", "🚂", "🚆", "🚉", "🚊", "🚞", "🚌",
    "🚍", "🚎", "🚐", "🚑", "🚒", "🚓", "🚔", "🚕", "🚖", "🚗",
    "🚘", "🚙", "🛻", "🚚", "🚛", "🚜", "🏎️", "🏍️", "🛵", "🦽",
    "🦼", "🛺", "🚲", "🛴", "🚏", "🛣️", "🛤️", "🛢️", "⛽", "🚨",
    "🚥", "🚦", "🛑", "🚧", "⚓", "⌛", "⏳", "⌚", "⏰", "⏱️",
    "⏲️", "🕰️", "📱", "📲", "💻", "⌨️", "🖥️", "🖨️", "🖱️", "🖲️",
    "💽", "💾", "💿", "📀", "📼", "📷", "📸", "📹", "🎥", "📽️",
    "🎞️", "📞", "☎️", "📟", "📠", "📺", "📻", "🎙️", "🎚️", "🎛️",
    "🧭", "📡", "🔋", "🔌", "💡", "🔦", "🕯️", "🪔", "🧯", "⚖️",
    "🧰", "🔧", "🔨", "⚒️", "🛠️", "⛏️", "🔩", "⚙️", "🧱", "⛓️",
    "🧲", "🔫", "🧨", "🪓", "🗡️", "⚔️", "🛡️", "🚬", "⚰️", "⚱️",
    "🔮", "📿", "🧿", "💈", "⚗️", "🔭", "🔬", "🕳️", "🩹", "🩺",
    "💊", "💉", "🩸", "🧬", "🦠", "🧫", "🧪", "🌡️", "🧹", "🧺",
    "🧻", "🚽", "🚰", "🚿", "🛁", "🛀", "🧼", "🪥", "🪒", "🧽",
    "🪣", "🧴", "🛎️", "🔑", "🗝️", "🚪", "🪑", "🛋️", "🛏️", "🛌",
    "🧸", "🪆", "🖼️", "🛍️", "🛒", "🎁", "🎈", "🎏", "🎀", "🎊",
    "🎉", "🎎", "🏮", "🎐", "🧧", "🔔", "🔕",
];

const _PATTERNS: Record<number, (string | string[])[]> = {
    1: [_GIVING_VERBS, _OBJECTS, _NICKNAMES],
    2: [_GREETINGS, _GIVING_VERBS, _OBJECTS, _PARTICLES],
    3: [_BLESSINGS, _PARTICLES, _NICKNAMES, "username"],
    4: [_GIVING_VERBS, _OBJECTS, _THANKS],
    5: [_GREETINGS, _OBJECTS, _GIVING_VERBS, "username"],
    6: [_GIVING_VERBS, _BLESSINGS, _EMOJIS],
    7: [_PARTICLES, _THANKS, _NICKNAMES],
    8: [_NICKNAMES, _THANKS, _BLESSINGS],
    9: [_OBJECTS, _OBJECTS, _NICKNAMES],
    10: [_GREETINGS, _NICKNAMES, _GIVING_VERBS, _OBJECTS, _PARTICLES],
    11: [_BLESSINGS, _BLESSINGS, _PARTICLES],
    12: [_GIVING_VERBS, _OBJECTS, _EMOJIS],
};

function _choose(pool: string[]): string {
    return pool[Math.floor(Math.random() * pool.length)];
}

export function generate_safe_saweria_message(user_name: string): string {
    const pattern_no = 1 + Math.floor(Math.random() * 12);
    const parts: string[] = [];
    const pattern = _PATTERNS[pattern_no];
    for (const spec of pattern) {
        if (Array.isArray(spec)) {
            parts.push(_choose(spec as string[]));
        } else {
            parts.push(user_name);
        }
    }

    if (Math.random() > 0.3) {
        parts.push(_choose(_EMOJIS));
    }

    if (Math.random() > 0.6) {
        parts.unshift(_choose(_EMOJIS));
    }

    let final_message = parts.join(" ");

    const casing_style = 1 + Math.floor(Math.random() * 6);
    if (casing_style === 1) {
        final_message = final_message.toLowerCase();
    } else if (casing_style === 2) {
        final_message = final_message.charAt(0).toUpperCase() + final_message.slice(1);
    } else if (casing_style === 3) {
        final_message = final_message
            .split(" ")
            .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
            .join(" ");
    } else if (casing_style === 4) {
        final_message = final_message.toUpperCase();
    } else if (casing_style === 5) {
        final_message = final_message
            .split("")
            .map((c, i) => (i % 2 === 0 ? c.toUpperCase() : c.toLowerCase()))
            .join("");
    }

    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    let unique_code = "";
    const code_len = 5 + Math.floor(Math.random() * 3);
    for (let i = 0; i < code_len; i++) {
        unique_code += chars[Math.floor(Math.random() * chars.length)];
    }
    return `${final_message} (${unique_code})`;
}