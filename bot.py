import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, InlineKeyboardMarkup,
    InlineKeyboardButton, CallbackQuery
)
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from config import (
    BOT_TOKEN, ADMIN_IDS, CHANNEL_ID,
    MAX_SAME_NAME, BLOCK_LIMIT
)
from database import (
    init_db, add_record,
    increase_fullname_count, get_fullname_count,
    increase_user_count, get_user_count
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ============================================================
# HOLATLAR
# ============================================================
class Form(StatesGroup):
    waiting_postdagi = State()   # postdagi odam
    waiting_data = State()       # F.I.Sh. + fakultet + kurs


# ============================================================
# TUGMA
# ============================================================
def next_student_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="➕ Yangi postdagi odamni qo'shish",
            callback_data="change_postdagi"
        )]
    ])


# ============================================================
# /start
# ============================================================
@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "1️⃣ Avval <b>postdagi odamning ismi va familiyasini</b> yozing:\n\n"
        "Misol: <code>Ali Valiyev</code>",
        parse_mode="HTML"
    )
    await state.set_state(Form.waiting_postdagi)


# ============================================================
# 1: Postdagi odam
# ============================================================
@dp.message(Form.waiting_postdagi, F.text)
async def get_postdagi(message: Message, state: FSMContext):
    postdagi = message.text.strip()

    if len(postdagi.split()) < 2:
        await message.answer(
            "❗ Iltimos, <b>ism va familiyani</b> birga yozing.\n\n"
            "Misol: <code>Ali Valiyev</code>",
            parse_mode="HTML"
        )
        return

    await state.update_data(postdagi_odam=postdagi)

    keyboard = next_student_keyboard()

    await message.answer(
        f"✅ Postdagi odam: <b>{postdagi}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 Endi o'quvchining <b>F.I.Sh., fakulteti va kursini</b> bitta xabarda yozing:\n\n"
        f"<b>Format:</b>\n"
        f"<code>Familiya Ism Fakultet Kurs</code>\n\n"
        f"<b>Misol:</b>\n"
        f"<code>Valiyev Ali Informatika 3</code>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.set_state(Form.waiting_data)


@dp.message(Form.waiting_postdagi)
async def wrong_postdagi(message: Message):
    await message.answer("❗ Iltimos, matn ko'rinishida yozing.")


# ============================================================
# TUGMA: Yangi postdagi odam
# ============================================================
@dp.callback_query(F.data == "change_postdagi")
async def change_postdagi(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "➕ <b>Yangi postdagi odamning ismi va familiyasini</b> yozing:\n\n"
        "Misol: <code>Ali Valiyev</code>",
        parse_mode="HTML"
    )
    await state.set_state(Form.waiting_postdagi)


# ============================================================
# 2: F.I.Sh. + Fakultet + Kurs
# ============================================================
@dp.message(Form.waiting_data, F.text)
async def get_data(message: Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split()

    if len(parts) < 4:
        await message.answer(
            "❗ Ma'lumot to'liq emas.\n\n"
            "<b>Format:</b>\n"
            "<code>Familiya Ism Fakultet Kurs</code>\n\n"
            "<b>Misol:</b>\n"
            "<code>Valiyev Ali Informatika 3</code>",
            parse_mode="HTML"
        )
        return

    familiya = parts[0]
    ism = parts[1]
    kurs = parts[-1]
    fakultet = " ".join(parts[2:-1])
    fullname = f"{familiya} {ism}"

    # ============================================================
    # F.I.Sh. bo'yicha hisoblash — o'quvchi 3 marta kech qolsa blok
    # ============================================================
    existing_fio_count = get_fullname_count(fullname)

    # Agar o'quvchi allaqachon 3 marta kech qolgan bo'lsa
    if existing_fio_count >= BLOCK_LIMIT:
        await message.answer(
            f"⛔ <b>Bu o'quvchi allaqachon {BLOCK_LIMIT} marta kech qolgan!</b>\n\n"
            f"👤 <b>{fullname}</b>\n"
            f"🏛 {fakultet} | 📚 {kurs}\n\n"
            f"Bu o'quvchi tizimga <b>kiritilmaydi</b>.",
            parse_mode="HTML"
        )
        return

    # 4 martalik cheklov (bir xil F.I.Sh. juda ko'p takrorlanmasin)
    if existing_fio_count >= MAX_SAME_NAME:
        await message.answer(
            f"⛔ <b>Bu F.I.Sh. allaqachon {MAX_SAME_NAME} marta yozilgan!</b>\n\n"
            f"👤 {fullname}",
            parse_mode="HTML"
        )
        return

    # Bazaga saqlash
    data = await state.get_data()
    postdagi_odam = data.get("postdagi_odam", "Noma'lum")
    user_id = message.from_user.id

    add_record(user_id, postdagi_odam, familiya, ism, fakultet, kurs)

    # F.I.Sh. bo'yicha hisobni oshirish
    new_fio_count = increase_fullname_count(fullname)

    # Postdagi odamning umumiy yozuv soni
    new_user_count = increase_user_count(user_id)

    caption = (
        f"🆕 <b>Yangi kech qolish</b>\n\n"
        f"👤 <b>F.I.Sh.:</b> {fullname}\n"
        f"🏛 <b>Fakultet:</b> {fakultet}\n"
        f"📚 <b>Kurs:</b> {kurs}\n"
        f"📊 <b>Bu o'quvchi:</b> {new_fio_count} marta\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👮 <b>Postdagi odam:</b> {postdagi_odam}\n"
        f"📝 <b>Jami yozuvlar:</b> {new_user_count}"
    )

    # Adminlarga yuborish
    async def send_to_admin(admin_id):
        try:
            await bot.send_message(admin_id, caption, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Admin {admin_id} ga yuborilmadi: {e}")

    await asyncio.gather(*[send_to_admin(aid) for aid in ADMIN_IDS])

    # ============================================================
    # O'QUVCHI 3 MARTA KECH QOLSA — BLOK
    # ============================================================
    if new_fio_count >= BLOCK_LIMIT:
        if CHANNEL_ID:
            try:
                await bot.send_message(
                    CHANNEL_ID,
                    f"🚨 <b>DIQQAT! O'QUVCHI {BLOCK_LIMIT} MARTA KECH QOLDI!</b>\n\n{caption}",
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Kanalga yuborilmadi: {e}")

        await message.answer(
            f"⛔ <b>DIQQAT!</b>\n\n"
            f"👤 <b>{fullname}</b>\n"
            f"🏛 {fakultet} | 📚 {kurs}\n\n"
            f"Bu o'quvchi <b>{BLOCK_LIMIT} marta</b> kech qoldi!\n"
            f"Endi u tizimga <b>kiritilmaydi</b>.",
            parse_mode="HTML"
        )

        # Adminlarga alohida ogohlantirish
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"🚨 <b>DIQQAT!</b>\n\n"
                    f"👤 <b>{fullname}</b>\n"
                    f"🏛 {fakultet} | 📚 {kurs}\n"
                    f"<b>{BLOCK_LIMIT} marta</b> kech qoldi va bloklandi.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    else:
        qolgan = BLOCK_LIMIT - new_fio_count
        await message.answer(
            f"✅ <b>Qabul qilindi!</b>\n\n"
            f"👤 {fullname}\n"
            f"🏛 {fakultet} | 📚 {kurs}\n"
            f"📊 Bu o'quvchi: <b>{new_fio_count}</b> marta\n\n"
            f"⚠️ Yana <b>{qolgan} marta</b> kech qolsa — bloklanadi!",
            parse_mode="HTML"
        )

    # Postdagi odamni saqlab qolamiz
    await state.clear()
    await state.update_data(postdagi_odam=postdagi_odam)

    # Keyingi o'quvchi
    keyboard = next_student_keyboard()
    await message.answer(
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔄 <b>Keyingi o'quvchi uchun tayyor</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👮 <b>Postdagi odam:</b> {postdagi_odam}\n\n"
        f"📝 O'quvchining <b>F.I.Sh., fakulteti va kursini</b> yozing:\n\n"
        f"<code>Familiya Ism Fakultet Kurs</code>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.set_state(Form.waiting_data)


@dp.message(Form.waiting_data)
async def wrong_data(message: Message):
    await message.answer("❗ Iltimos, matn ko'rinishida yozing.")


# ============================================================
# /stats
# ============================================================
@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    import sqlite3
    from config import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT fullname, count FROM fullname_counts ORDER BY count DESC LIMIT 20")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await message.answer("Hozircha ma'lumot yo'q.")
        return

    text = "📊 <b>O'quvchilar statistikasi</b>\n\n"
    for i, (name, count) in enumerate(rows, 1):
        emoji = "🔴" if count >= BLOCK_LIMIT else "🟡" if count == 2 else "🟢"
        text += f"{i}. {emoji} {name} — <b>{count}</b> marta\n"

    await message.answer(text, parse_mode="HTML")


# ============================================================
# /reset
# ============================================================
@dp.message(Command("reset"))
async def reset_cmd(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    import sqlite3
    from config import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM fullname_counts")
    cur.execute("DELETE FROM user_counts")
    conn.commit()
    conn.close()
    await message.answer("✅ Hisoblagichlar nolga tushirildi.")


# ============================================================
# ISHGA TUSHIRISH
# ============================================================
async def main():
    init_db()
    print("=" * 50)
    print("🤖 Bot ishga tushdi...")
    print(f"👤 Adminlar: {ADMIN_IDS}")
    print(f"⛔ O'quvchi blok limiti: {BLOCK_LIMIT} marta")
    print(f"🔁 Bir xil F.I.Sh. limiti: {MAX_SAME_NAME} marta")
    print("=" * 50)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())