import uuid

import pyrogram
from pyrogram import filters

from helpers.modules import Modules

from .. import get_notification_target


async def successful_donation_handler(client, message):
    if not message.successful_payment.invoice_payload.startswith("donation_"):
        return

    user = message.from_user
    stars_donated = message.successful_payment.total_amount
    charge_id = message.successful_payment.telegram_payment_charge_id
    current_bot_id = client.me.id
    super_admin_id = client.owner_id

    try:
        await client.send_rich_message(
            chat_id=user.id,
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('party_popper')} **Terima Kasih Banyak, {user.first_name}!**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Donasi', f"**{stars_donated} Stars ({client.ns.emoji.md('star')})**"], ['Status', 'Kami telah menerima donasi Anda'], ['Catatan', 'Dukungan Anda adalah bahan bakar semangat bagi kami. Semoga hari Anda menyenangkan!']])}"
                )
            ),
        )
    except Exception as e:
        client.log.print(f"Gagal mengirim ucapan donasi: {e}")

    charge_marker = f"stars_charge_{charge_id}"
    if not await client.db.setVarsOnce(current_bot_id, charge_marker, True):
        return

    owner_of_this_bot = await get_notification_target(client)
    main_bot_client = client.manager.main_bot_client

    try:
        user_mention_str = client.ns.telegram.arg.getMention(user, md=True)
        bot_mention_str = client.ns.telegram.arg.getMention(client.me, md=True)

        notification_text = (
            f"{client.ns.emoji.md('sparkles')} **Donasi Baru Diterima!**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], [['Jumlah', f'`{stars_donated}` Stars ({client.ns.emoji.md('star')})'], ['Dari', f'{user_mention_str} (`{user.id}`)'], ['Melalui Bot', f'{bot_mention_str}']])}"
        )

        refund_key = uuid.uuid4().hex[:16]
        refund_data = {
            "user_id": user.id,
            "charge_id": charge_id,
        }

        await client.db.setVars(
            current_bot_id,
            f"refund_{refund_key}",
            refund_data,
        )

        refund_callback_data = f"refund_stars_{refund_key}"
        layout = [
            [
                {
                    "text": "🔙 Kembalikan Donasi",
                    "callback_data": refund_callback_data,
                    "style": "red",
                    "emoji": client.ns.emoji.id("minus"),
                }
            ]
        ]
        refund_btn = client.ns.telegram.button.build_button_grid(layout)

        await client.send_rich_message(
            chat_id=owner_of_this_bot,
            rich_message=pyrogram.types.InputRichMessage(markdown=notification_text),
            reply_markup=refund_btn,
        )

    except pyrogram.errors.UserIsBlocked:
        if main_bot_client and owner_of_this_bot != super_admin_id:
            user_mention_str = client.ns.telegram.arg.getMention(user, md=True)

            await main_bot_client.send_rich_message(
                super_admin_id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('exclamation')} **Notifikasi Gagal Terkirim**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], [['Donasi', f'`{stars_donated}` Stars'], ['Dari', user_mention_str], ['Owner Bot', f'`{client.me.first_name}`'], ['Penyebab', 'Bot diblokir oleh owner']])}"
                    )
                ),
            )

    except Exception as e:
        client.log.print(f"Gagal mengirim notifikasi donasi: {e}")


class PaymentStars(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_message(filters.successful_payment)(
            self.handle(successful_donation_handler)
        )
