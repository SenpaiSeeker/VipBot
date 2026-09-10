from pyrogram import filters

from .. import command, ctx, is_bot_owner


def _settings_layout(client):
    return [
        [
            {
                "text": "🖼️ Atur Foto Start",
                "callback_data": "set_start_photo",
                "style": "blue",
                "emoji": client.ns.emoji.id("frame"),
            },
            {
                "text": "✍️ Atur Teks Start",
                "callback_data": "set_start_text",
                "style": "blue",
                "emoji": client.ns.emoji.id("writing_hand"),
            },
        ],
        [
            {
                "text": "➕ Tambah VVIP",
                "callback_data": "setup_listvvip",
                "style": "green",
                "emoji": client.ns.emoji.id("plus"),
            },
            {
                "text": "➖ Hapus VVIP",
                "callback_data": "delete_listvvip",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            },
        ],
        [
            {
                "text": "✏️ Edit Harga VVIP",
                "callback_data": "edit_price_listvvip",
                "style": "blue",
                "emoji": client.ns.emoji.id("pencil"),
            }
        ],
        [
            {
                "text": "👥 Total Pengguna",
                "callback_data": "total_users_count",
                "style": "blue",
                "emoji": client.ns.emoji.id("busts_in_silhouette"),
            },
            {
                "text": "👥 Cek Member VVIP",
                "callback_data": "list_members_0",
                "style": "blue",
                "emoji": client.ns.emoji.id("busts_in_silhouette"),
            },
        ],
        [
            {
                "text": "🕵️ Cek Member Aktif",
                "callback_data": "check_active_menu_init",
                "style": "blue",
                "emoji": client.ns.emoji.id("mag"),
            },
            {
                "text": "🔍 Cek Status Grup VVIP",
                "callback_data": "check_vvip_status",
                "style": "blue",
                "emoji": client.ns.emoji.id("mag_right"),
            },
        ],
        [
            {
                "text": "📢 Buat Broadcast",
                "callback_data": "broadcast",
                "style": "green",
                "emoji": client.ns.emoji.id("loudspeaker"),
            },
            {
                "text": "🌟 Harga Broadcast Paid",
                "callback_data": "set_broadcast_price",
                "style": "green",
                "emoji": client.ns.emoji.id("glowing_star"),
            },
        ],
        [
            {
                "text": "🔑 Kelola Kunci API",
                "callback_data": "api_settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("key"),
            },
            {
                "text": "🎟️ Kelola Kupon",
                "callback_data": "manage_coupons",
                "style": "blue",
                "emoji": client.ns.emoji.id("ticket_admit"),
            },
        ],
        [
            {
                "text": "🔔 Atur Tempat Notifikasi",
                "callback_data": "set_notif_chat",
                "style": "blue",
                "emoji": client.ns.emoji.id("bell"),
            }
        ],
        [
            {
                "text": "💰 Pendapatan VIP",
                "callback_data": "vip_revenue_menu",
                "style": "green",
                "emoji": client.ns.emoji.id("money_bag"),
            },
            {
                "text": "⭐ Statistik Stars",
                "callback_data": "stats_0",
                "style": "green",
                "emoji": client.ns.emoji.id("star"),
            },
        ],
        [
            {
                "text": "• Kembali ke Menu Utama •",
                "callback_data": "start",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]


@command(
    lambda ctx: filters.regex("^settings$"),
    handler_type="callback",
)
async def settings(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            show_alert=True,
        )

    txt_content = (
        f"**{client.ns.emoji.toolbox} Panel Pengaturan Owner**\n\n"
        "Selamat datang di pusat kendali bot Anda! Silakan pilih menu di bawah "
        "untuk mengelola berbagai aspek bot."
    )
    btn = client.ns.telegram.button.build_button_grid(_settings_layout(client))
    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt_content, reply_markup=btn)
    else:
        await callback_query.edit_message_text(txt_content, reply_markup=btn)