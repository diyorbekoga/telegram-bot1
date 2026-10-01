import asyncio
import os
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, FSInputFile, InlineKeyboardMarkup,
    InlineKeyboardButton, CallbackQuery
)
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from config import (
    BOT_TOKEN, ADMIN_IDS, CHANNEL_ID, UPLOAD_DIR,
    MAX_SAME_NAME, BLOCK_LIMIT
)
from database import (
    init_db, add_record, increase_count, get_count,
    increase_fullname_count, get_fullname_count
)
from image_utils import add_warning_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ============================================================
# HOLATLAR
# ============================================================
class Form(StatesGroup):
    waiting_postdagi = State()   # postdagi odam (faqat /start da yoki yangi qo'shganda)
    waiting_fio = State()        # o'quvchi F.I.Sh. + telefon
    waiting_photo = State()      # rasm
    waiting_reason = State()     # sabab


# ============================================================
# YORDAMCHI: keyingi o'quvchi uchun tugma
# ============================================================
def next_student_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="➕ Yangi postdagi odamni qo'shish",
            callback_data="change_postdagi"
        )]
    ])
    return keyboard


# ============================================================
# /start
# ============================================================
@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    count = get_count(user_id)
    if count >= BLOCK_LIMIT:
        await message.answer(
            f"⛔ <b>Siz allaqachon {BLOCK_LIMIT} marta kech qolgansiz!</b>\n\n"
            f"Sizni tizimga kirita olmaymiz.\n"
            f"Rahbariyat bilan bog'laning.",
            parse_mode="HTML"
        )
        return

    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "Bu <b>Kirish-Chiqish nazorati</b> boti.\n\n"
        "1️⃣ Avval <b>postdagi odamning ismi va familiyasini</b> yozing:\n\n"
        "Misol: <code>Ali Valiyev</code>",
        parse_mode="HTML"
    )
    await state.set_state(Form.waiting_postdagi)


# ============================================================
# 1: Postdagi odam (faqat 1 marta)
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

    # Tepadagi tugma bilan xabar
    keyboard = next_student_keyboard()

    await message.answer(
        f"✅ <b>Postdagi odam saqlandi:</b> {postdagi}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 Endi o'quvchining <b>F.I.Sh. va telefon raqamini</b> bitta xabarda yozing:\n\n"
        f"<b>Format:</b>\n"
        f"<code>Familiya Ism Otasining_ismi +998901234567</code>\n\n"
        f"<b>Misol:</b>\n"
        f"<code>Valiyev Ali Valiyevich +998901234567</code>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.set_state(Form.waiting_fio)


@dp.message(Form.waiting_postdagi)
async def wrong_postdagi(message: Message):
    await message.answer("❗ Iltimos, matn ko'rinishida yozing.")


# ============================================================
# TUGMA: Yangi postdagi odamni qo'shish
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
# 2: O'quvchi F.I.Sh. + telefon
# ============================================================
@dp.message(Form.waiting_fio, F.text)
async def get_fio(message: Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split()

    if len(parts) < 4:
        await message.answer(
            "❗ Ma'lumot to'liq emas.\n\n"
            "<b>Format:</b>\n"
            "<code>Familiya Ism Otasining_ismi +998901234567</code>\n\n"
            "<b>Misol:</b>\n"
            "<code>Valiyev Ali Valiyevich +998901234567</code>",
            parse_mode="HTML"
        )
        return

    telefon = parts[-1]
    telefon_clean = telefon.replace("+", "").replace(" ", "").replace("-", "")
    if not telefon_clean.isdigit() or len(telefon_clean) < 9:
        await message.answer(
            "❗ Telefon raqam noto'g'ri.\n\n"
            "Misol: <code>+998901234567</code>",
            parse_mode="HTML"
        )
        return

    fio_parts = parts[:-1]
    if len(fio_parts) < 3:
        await message.answer(
            "❗ F.I.Sh. to'liq emas.\n\n"
            "Misol: <code>Valiyev Ali Valiyevich +998901234567</code>",
            parse_mode="HTML"
        )
        return

    familiya = fio_parts[0]
    ism = fio_parts[1]
    otasining_ismi = " ".join(fio_parts[2:])
    fullname = f"{familiya} {ism} {otasining_ismi}"

    existing = get_fullname_count(fullname)
    if existing >= MAX_SAME_NAME:
        await state.clear()
        await message.answer(
            f"⛔ <b>Bu F.I.Sh. allaqachon {MAX_SAME_NAME} marta yozilgan!</b>\n\n"
            f"👤 {fullname}\n\n"
            f"Boshqa F.I.Sh. bilan qaytadan urinib ko'ring.\n\n"
            f"Qaytadan boshlash uchun /start bosing.",
            parse_mode="HTML"
        )
        return

    await state.update_data(
        familiya=familiya,
        ism=ism,
        otasining_ismi=otasining_ismi,
        fullname=fullname,
        telefon=telefon
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📷 Rasm qo'yish", callback_data="put_photo")],
        [InlineKeyboardButton(text="⏭️ Rasm kerak emas", callback_data="skip_photo")]
    ])

    await message.answer(
        f"✅ Ma'lumot qabul qilindi!\n\n"
        f"👤 <b>{fullname}</b>\n"
        f"📞 {telefon}\n\n"
        f"3️⃣ Endi <b>rasm</b> bosqichi:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.set_state(Form.waiting_photo)


@dp.message(Form.waiting_fio)
async def wrong_fio(message: Message):
    await message.answer("❗ Iltimos, matn ko'rinishida yozing.")


# ============================================================
# 3: Rasm bosqichi
# ============================================================
@dp.callback_query(F.data == "put_photo")
async def put_photo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "📷 Endi <b>rasmni yuboring</b>.\n\n"
        "Pastdagi 📎 (skrepka) tugmasini bosib, <b>Galereya</b> ni tanlang.",
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "skip_photo")
async def skip_photo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(photo_path=None)

    await callback.message.edit_text(
        "✅ Rasm o'tkazib yuborildi.\n\n"
        "4️⃣ Endi <b>kechga qolish sababini</b> yozing:",
        parse_mode="HTML"
    )
    await state.set_state(Form.waiting_reason)


@dp.message(Form.waiting_photo, F.photo)
async def get_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_path = os.path.join(UPLOAD_DIR, f"{message.from_user.id}_{photo.file_id}.jpg")
    await bot.download_file(file.file_path, file_path)

    await state.update_data(photo_path=file_path)
    await message.answer(
        "✅ Rasm qabul qilindi.\n\n"
        "4️⃣ Endi <b>kechga qolish sababini</b> yozing:",
        parse_mode="HTML"
    )
    await state.set_state(Form.waiting_reason)


@dp.message(Form.waiting_photo)
async def wrong_photo(message: Message):
    await message.answer(
        "❗ Iltimos, rasm yuboring yoki tugmalardan birini bosing."
    )


# ============================================================
# 4: Sabab va saqlash
# ============================================================
@dp.message(Form.waiting_reason, F.text)
async def get_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    postdagi_odam = data.get("postdagi_odam", "Noma'lum")
    familiya = data.get("familiya", "")
    ism = data.get("ism", "")
    otasining_ismi = data.get("otasining_ismi", "")
    fullname = data.get("fullname", f"{familiya} {ism}")
    telefon = data.get("telefon", "")
    photo_path = data.get("photo_path")
    reason = message.text.strip()
    user_id = message.from_user.id

    new_fio_count = increase_fullname_count(fullname)

    add_record(user_id, postdagi_odam, familiya, ism, otasining_ismi,
               telefon, photo_path, reason)

    new_count = increase_count(user_id)

    # Caption — tagida postdagi odam ismi
    caption = (
        f"🆕 <b>Yangi kech qolish</b>\n\n"
        f"👤 <b>F.I.Sh.:</b> {fullname}\n"
        f"📞 <b>Telefon:</b> {telefon}\n"
        f"📌 <b>Sabab:</b> {reason}\n"
        f"🔢 <b>Jami:</b> {new_count} marta\n"
        f"📊 <b>Bu F.I.Sh.:</b> {new_fio_count} marta\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👮 <b>Postdagi odam:</b> {postdagi_odam}"
    )

    has_photo = photo_path and os.path.exists(photo_path)

    async def send_to_admin(admin_id):
        try:
            if has_photo:
                await bot.send_photo(
                    admin_id,
                    FSInputFile(photo_path),
                    caption=caption,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    admin_id,
                    caption + "\n\n📷 <i>Rasm yo'q</i>",
                    parse_mode="HTML"
                )
        except Exception as e:
            logging.error(f"Admin {admin_id} ga yuborilmadi: {e}")

    await asyncio.gather(*[send_to_admin(aid) for aid in ADMIN_IDS])

    # 3 marta blok
    if new_count >= BLOCK_LIMIT:
        warn_path = None
        if has_photo:
            warn_path = photo_path.replace(".jpg", "_warning.jpg")
            try:
                add_warning_text(photo_path, warn_path, f"{BLOCK_LIMIT} MARTA KECH QOLGAN!")
            except Exception as e:
                logging.error(f"Rasmga yozuv xato: {e}")
                warn_path = photo_path

        if CHANNEL_ID:
            try:
                if warn_path and os.path.exists(warn_path):
                    await bot.send_photo(
                        CHANNEL_ID,
                        FSInputFile(warn_path),
                        caption=f"🚨 <b>DIQQAT!</b>\n\n{caption}",
                        parse_mode="HTML"
                    )
                else:
                    await bot.send_message(
                        CHANNEL_ID,
                        f"🚨 <b>DIQQAT!</b>\n\n{caption}",
                        parse_mode="HTML"
                    )
            except Exception as e:
                logging.error(f"Kanalga yuborilmadi: {e}")

        await message.answer(
            f"⛔ <b>SIZ {BLOCK_LIMIT} MARTA KECH QOLDINGIZ!</b>\n\n"
            f"Endi sizni tizimga <b>kirita olmaymiz</b>.\n"
            f"Iltimos, rahbariyat bilan bog'laning.",
            parse_mode="HTML"
        )
    else:
        qolgan = BLOCK_LIMIT - new_count
        await message.answer(
            f"✅ <b>Qabul qilindi!</b>\n\n"
            f"👤 {fullname}\n"
            f"📞 {telefon}\n"
            f"📌 {reason}\n"
            f"🔢 Sizning kech qolishlaringiz: <b>{new_count}</b>\n\n"
            f"⚠️ Yana <b>{qolgan} marta</b> kech qolsangiz — bloklanasiz!",
            parse_mode="HTML"
        )

    await state.clear()

    # Keyingi o'quvchi — postdagi odam ESKI qoladi
    keyboard = next_student_keyboard()
    await message.answer(
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔄 <b>Keyingi o'quvchi uchun tayyor</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👮 <b>Postdagi odam:</b> {postdagi_odam}\n\n"
        f"📝 Endi o'quvchining <b>F.I.Sh. va telefon raqamini</b> bitta xabarda yozing:\n\n"
        f"<code>Familiya Ism Otasining_ismi +998901234567</code>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    # ⚠️ MUHIM: postdagi_odam ni saqlab qolamiz!
    await state.update_data(postdagi_odam=postdagi_odam)
    await state.set_state(Form.waiting_fio)


@dp.message(Form.waiting_reason)
async def wrong_reason(message: Message):
    await message.answer("❗ Iltimos, sababni matn ko'rinishida yozing.")


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
    cur.execute("SELECT full_name, count FROM late_counts ORDER BY count DESC LIMIT 20")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await message.answer("Hozircha ma'lumot yo'q.")
        return

    text = "📊 <b>Kech qolish statistikasi</b>\n\n"
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
    cur.execute("DELETE FROM late_counts")
    cur.execute("DELETE FROM fullname_counts")
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
    print(f"⛔ Blok limiti: {BLOCK_LIMIT} marta")
    print(f"🔁 Bir xil F.I.Sh. limiti: {MAX_SAME_NAME} marta")
    print("=" * 50)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())