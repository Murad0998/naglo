import asyncio
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile
import requests
from yookassa import Configuration, Payment
from datetime import datetime
import json
import sqlite3
from aiogram import Bot, Dispatcher, types, F, Router  # Добавляем импорт F
from aiogram.filters import Command
from aiogram.types import Message
import qrcode
from io import BytesIO
import uuid
from dv import restart,start_markup,start_markup4
DATABASE_FILE = "database6.db"
ADMIN_IDS = [5510185795,1097080977]
SHOP_ID = '1060209'
API_KEY = 'test_bMjswdy-LXNQQCYYlmt4D4B_o2412I7rpkHsYqetirg'
Configuration.account_id = '1060209'    # например, "1020973"
Configuration.secret_key = 'test_bMjswdy-LXNQQCYYlmt4D4B_o2412I7rpkHsYqetirg'
SECOND_BOT_USERNAME = "Stud_VPN_bot"

# Импортируем функции работы с БД из предыдущего кода
from data import (create_database, add_event, get_event, get_all_events,register_participant,verify_ticket,save_ticket,check_ticket_status,mark_ticket_as_scanned,cleanup_past_events)

# Токен вашего бота
BOT_TOKEN = "7741421068:AAEES9SMSegfN1IidcvobaSGpvz7AZ8oLM4"

# Инициализация бота и диспетчера
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)
router = Router()


# Состояния FSM для создания мероприятия
class EventCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_date = State()
    waiting_for_location = State()
    waiting_for_max_participants = State()
    waiting_for_photo = State()
    waiting_for_standard_price = State()
    waiting_for_fasttrack_price = State()
    waiting_for_vip_price = State()

class UserSetup(StatesGroup):
    waiting_for_first_name = State()  # Имя
    waiting_for_last_name = State()   # Фамилия
    waiting_for_middle_name = State() # Отчество
    waiting_for_status = State()      # Статус



@dp.message(Command('start'))
async def cmd_start(message: Message, state: FSMContext):
    print(1)
    # Проверяем, есть ли у пользователя данные в базе
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, last_name, relationship_status FROM users WHERE user_id = ?", (message.from_user.id,))
    user_data = cursor.fetchone()
    conn.close()

    if not user_data:
        # Если данных нет, запускаем процесс ввода данных
        await state.set_state(UserSetup.waiting_for_first_name)
        await message.answer(
            "Привет! Для начала работы необходимо заполнить данные о себе, чтоб генерировать билет и пройти по нему на вечеринку.\n"
            "Введите ваше имя:"
        )
    else:
        # Если данные есть, показываем основное меню
        buttons = await get_main_menu(message.from_user.id)
        await message.answer(
            "Добро пожаловать! Выберите, что хотите сделать:",
            reply_markup=buttons
        )


@dp.message(UserSetup.waiting_for_first_name)
async def process_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text.strip())
    await state.set_state(UserSetup.waiting_for_last_name)
    await message.answer("Введите вашу фамилию:")


@dp.message(UserSetup.waiting_for_last_name)
async def process_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text.strip())
    await state.set_state(UserSetup.waiting_for_middle_name)
    await message.answer("Введите ваше отчество (или отправьте '-' для пропуска):")


@dp.message(UserSetup.waiting_for_middle_name)
async def process_middle_name(message: Message, state: FSMContext):
    middle_name = message.text.strip()
    if middle_name == '-':
        middle_name = None
    await state.update_data(middle_name=middle_name)

    # Переходим к выбору статуса
    await state.set_state(UserSetup.waiting_for_status)

    # Исправленный код создания клавиатуры
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [types.KeyboardButton(text="Ищу отношения"), types.KeyboardButton(text="Занят")]
        ]
    )
    await message.answer("Выберите ваш статус (нажмите на одну из кнопок):", reply_markup=keyboard)


@dp.message(UserSetup.waiting_for_status)
async def process_status(message: Message, state: FSMContext):
    if message.text not in ["Ищу отношения", "Занят"]:
        await message.answer("Пожалуйста, выберите статус из предложенных (Ищу отношения или Занят).")
        return

    # Сохраняем отредактированные данные
    user_data = await state.get_data()
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, first_name, last_name, middle_name, relationship_status) 
        VALUES (?, ?, ?, ?, ?)
    ''', (
        message.from_user.id,
        user_data.get('first_name'),
        user_data.get('last_name'),
        user_data.get('middle_name'),
        message.text  # Сохраняем выбранный статус
    ))

    conn.commit()
    conn.close()

    await state.clear()

    # Сообщаем о завершении настройки и показываем главное меню
    buttons = await get_main_menu(message.from_user.id)
    await message.answer(
        "Отлично, регистрация завершена! Вы теперь можете использовать основные функции.",
        reply_markup=buttons
    )

async def get_main_menu(user_id: int) -> types.ReplyKeyboardMarkup:
    if user_id in ADMIN_IDS:
        # Меню для админов
        keyboard = types.ReplyKeyboardMarkup(keyboard=[
            [types.KeyboardButton(text="📅 Показать мероприятия")],
            [types.KeyboardButton(text="➕ Создать мероприятие")],
            [types.KeyboardButton(text="🎫 Мои регистрации")],
            [types.KeyboardButton(text="✅ Отметить билет")],
           # [types.KeyboardButton(text="Дайв")],
            [types.KeyboardButton(text="🗑️ Удалить мероприятие")],  # Добавляем новую кнопку
            [types.KeyboardButton(text="⚙️ Настройки")],
        ], resize_keyboard=True)
    else:
        # Меню для пользователей
        keyboard = types.ReplyKeyboardMarkup(keyboard=[
            [types.KeyboardButton(text="📅 Показать мероприятия")],
            [types.KeyboardButton(text="🎫 Мои регистрации")],
           # [types.KeyboardButton(text="Дайв")],
            [types.KeyboardButton(text="⚙️ Настройки")],
        ], resize_keyboard=True)

    return keyboard



@dp.message(F.text == "Дайв")
async def redirect_to_second_bot(message: Message):
    print(1)
    # Создание кнопки со ссылкой на второго бота
    # second_bot_link = f'https://t.me/{SECOND_BOT_USERNAME}?start'
    # markup = types.InlineKeyboardMarkup()
    # button1 = types.InlineKeyboardButton("Перейти ко второму боту", url=second_bot_link)
    # markup.add(button1)
    # await message.answer("Нажмите на кнопку, чтобы перейти ко второму боту:", reply_markup=markup)


@dp.message(F.text == "📅 Показать мероприятия")
async def show_events(message: Message):
    events = await get_all_events()

    if not events:
        await message.answer("Пока нет запланированных мероприятий.")
        return

    for event in events:
        text = (
            f"🎉 *{event['title']}*\n"
            f"📝 {event['description']}\n"
            f"📅 {event['date_time']}\n"
            f"📍 {event['location']}\n"
            f"👥 Участники: {event['current_participants']}/{event['max_participants']}\n"
        )

        # Дебаг photo_id для проверки
        print("Photo ID: ", event['photo_id'])

        # Проверяем наличие корректного file_id или заменяем тестовым
        if event['photo_id']:
            try:
                await message.answer_photo(
                    photo=event['photo_id'],  # Используем фото из БД
                    caption=text,
                    reply_markup=types.InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                types.InlineKeyboardButton(
                                    text="Зарегистрироваться",
                                    callback_data=f"show_tickets_{event['event_id']}",
                                )
                            ]
                        ]
                    ),
                    parse_mode="Markdown",
                )
            except Exception as e:
                await message.answer(f"Не удалось отправить фото: {e}")
        else:
            await message.answer("Фотография мероприятия отсутствует.")



@dp.callback_query(lambda c: c.data.startswith('show_tickets_'))
async def show_ticket_options(callback_query: types.CallbackQuery):
    event_id = callback_query.data.split('_')[2]
    event = await get_event(event_id)  # Функция для получения информации о мероприятии

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(
            text=f"Стандарт - {event['standard_price']} руб.",
            callback_data=f"register_{event_id}_standard"
        )],
        [types.InlineKeyboardButton(
            text=f"Фаст-трек - {event['fasttrack_price']} руб.",
            callback_data=f"register_{event_id}_fasttrack"
        )],
        [types.InlineKeyboardButton(
            text=f"VIP - {event['vip_price']} руб.",
            callback_data=f"register_{event_id}_vip"
        )]
    ])

    await callback_query.message.edit_reply_markup(reply_markup=keyboard)


@dp.message(F.text == "➕ Создать мероприятие")
async def create_event_start(message: Message, state: FSMContext):
    await state.set_state(EventCreation.waiting_for_title)
    await message.answer("Введите название мероприятия:")


@dp.message(EventCreation.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(EventCreation.waiting_for_description)
    await message.answer("Введите описание мероприятия:")


@dp.message(EventCreation.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(EventCreation.waiting_for_date)
    await message.answer("Введите дату и время мероприятия (формат: ГГГГ-ММ-ДД ЧЧ:ММ):")


@dp.message(EventCreation.waiting_for_date)
async def process_date(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text, '%Y-%m-%d %H:%M')
        await state.update_data(date_time=message.text)
        await state.set_state(EventCreation.waiting_for_location)
        await message.answer("Введите место проведения:")
    except ValueError:
        await message.answer("Неверный формат даты. Попробуйте еще раз (ГГГГ-ММ-ДД ЧЧ:ММ):")


@dp.message(EventCreation.waiting_for_location)
async def process_location(message: Message, state: FSMContext):
    await state.update_data(location=message.text)
    await state.set_state(EventCreation.waiting_for_max_participants)
    await message.answer("Введите максимальное количество участников:")


@dp.message(EventCreation.waiting_for_max_participants)
async def process_max_participants(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число:")
        return

    await state.update_data(max_participants=int(message.text))
    await state.set_state(EventCreation.waiting_for_photo)
    await message.answer("Пожалуйста, отправьте фото мероприятия:")


@dp.message(EventCreation.waiting_for_photo)
async def process_photo(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото мероприятия:")
        return

    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await state.set_state(EventCreation.waiting_for_standard_price)
    await message.answer("Введите стоимость стандартного билета (в рублях):")


@dp.message(EventCreation.waiting_for_standard_price)
async def process_standard_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите числовое значение:")
        return

    await state.update_data(standard_price=int(message.text))
    await state.set_state(EventCreation.waiting_for_fasttrack_price)
    await message.answer("Введите стоимость Fast-Track билета (в рублях):")


@dp.message(EventCreation.waiting_for_fasttrack_price)
async def process_fasttrack_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите числовое значение:")
        return

    await state.update_data(fasttrack_price=int(message.text))
    await state.set_state(EventCreation.waiting_for_vip_price)
    await message.answer("Введите стоимость VIP билета (в рублях):")


@dp.message(EventCreation.waiting_for_vip_price)
async def process_vip_price(message: Message, state: FSMContext):
    try:
        vip_price = int(message.text)
        data = await state.get_data()

        event_id = await add_event(
            title=data['title'],
            description=data['description'],
            date_time=data['date_time'],
            location=data['location'],
            max_participants=data['max_participants'],
            photo_id=data['photo_id'],
            standard_price=data['standard_price'],
            fasttrack_price=data['fasttrack_price'],
            vip_price=vip_price
        )

        await message.answer("Мероприятие успешно создано!")
        await state.clear()

    except ValueError:
        await message.answer("Пожалуйста, введите числовое значение:")


# Функция для генерации QR-кода
async def generate_qr_code_start(ticket_data: dict) -> BytesIO:
    # Создаем уникальный идентификатор билета
    ticket_id = ticket_data.get('ticket_id', str(uuid.uuid4()))

    # Подключаемся к базе и получаем данные о пользователе
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    user_id = ticket_data['user_id']

    # Получаем данные пользователя (ФИО и статус)
    cursor.execute('''
        SELECT first_name, last_name, middle_name, relationship_status
        FROM users
        WHERE user_id = ?
    ''', (user_id,))
    user_data = cursor.fetchone()

    # Проверяем, есть ли данные
    if not user_data:
        conn.close()
        raise ValueError("Пользовательские данные не найдены для формирования QR-кода.")

    # Данные о пользователе
    first_name, last_name, middle_name, relationship_status = user_data

    # Проверяем в базе текущий статус билета
    cursor.execute('''
        SELECT scanned
        FROM tickets
        WHERE ticket_id = ?
    ''', (ticket_id,))
    result = cursor.fetchone()
    conn.close()

    # Формируем данные для QR-кода
    qr_data = {
        "ticket_id": ticket_id,
        "ticket_type": ticket_data['ticket_type'],
        "event_date": ticket_data['event_date'],
        "first_name": first_name,
        "last_name": last_name,
        "middle_name": middle_name or '',  # Если отчество отсутствует, передаем пустую строку
        "status": relationship_status,
        "scanned": bool(result[0]) if result else False,
    }

    # Преобразуем в JSON строку
    qr_json = json.dumps(qr_data, ensure_ascii=False)

    # Создаем QR-код
    buffer = BytesIO()
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_json)
    qr.make(fit=True)

    # Генерируем изображение QR-кода
    qr_image = qr.make_image(fill_color="black", back_color="white")
    qr_image.save(buffer, format="PNG")
    buffer.seek(0)

    # Сохраняем билет в базу
    await save_ticket(ticket_id, ticket_data)

    return buffer, ticket_id


# @dp.callback_query(lambda c: c.data.startswith('register_'))
# async def process_registration(callback_query: types.CallbackQuery):
#     _, event_id, ticket_type = callback_query.data.split('_')
#     user_id = callback_query.from_user.id
#
#     # Регистрируем участника
#     success = await register_participant(event_id, user_id, ticket_type)
#
#     if not success:
#         await callback_query.answer(
#             "К сожалению, регистрация не удалась. Возможно, нет свободных мест.",
#             show_alert=True
#         )
#         return
#
#     # Получаем информацию о мероприятии
#     event = await get_event(event_id)
#
#     # Формируем данные для билета
#     ticket_data = {
#         'event_id': event_id,
#         'event_title': event['title'],
#         'ticket_type': ticket_type,
#         'user_id': user_id,
#         'event_date': event['date_time']
#     }
#     ticket_id = ticket_data.get('ticket_id', str(uuid.uuid4()))
#     try:
#         # Генерируем QR-код
#         qr_buffer, ticket_id = await generate_qr_code_start(ticket_data)
#         caption = (
#             f"🎫 *Ваш билет на мероприятие*\n\n"
#             f"🎉 Мероприятие: {event['title']}\n"
#             f"📅 Дата: {event['date_time']}\n"
#             f"📍 Место: {event['location']}\n"
#             f"🎟️ Тип билета: {ticket_type}\n"
#             f"🔑 ID билета: `{ticket_id}`\n\n"
#             f"_Сохраните этот QR-код, он понадобится вам для входа на мероприятие_"
#         )
#
#         photo = BufferedInputFile(
#             qr_buffer.getvalue(),
#             filename="ticket_qr.png"
#         )
#
#         await callback_query.message.answer_photo(
#             photo=photo,
#             caption=caption,
#             parse_mode="Markdown"
#         )
#
#         await callback_query.answer("Билет успешно сформирован!", show_alert=True)
#
#     except Exception as e:
#         print(f"Ошибка при генерации билета: {e}")
#         await callback_query.answer(
#             "Произошла ошибка при формировании билета",
#             show_alert=True
#         )


@dp.message(F.text == "🎫 Мои регистрации")
async def show_my_registrations(message: Message):
    user_id = message.from_user.id

    # Запрашиваем билеты из базы данных
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ticket_id, ticket_type, title, description, date_time, location, photo_id
        FROM tickets t
        JOIN events e ON t.event_id = e.event_id
        WHERE user_id = ?
    ''', (user_id,))
    tickets = cursor.fetchall()
    conn.close()

    # Проверяем, есть ли билеты у пользователя
    if not tickets:
        await message.answer("Вы пока не зарегистрированы ни на одно мероприятие.")
        return

    # Проходим по всем событиям и отображаем их
    for ticket in tickets:
        ticket_id, ticket_type, title, description, date_time, location, photo_id = ticket

        # Формируем текст сообщения
        text = (f"🎉 *{title}*\n"
                f"📝 {description}\n"
                f"📅 Дата и время: {date_time}\n"
                f"📍 Место: {location}\n"
                f"🎟️ Тип билета: {ticket_type}\n")

        # Если у события есть фото, добавляем его
        # Генерируем кнопку для типа билета
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=f"QR-код ({ticket_type})",
                        callback_data=f"show_qr_{ticket_id}"
                    )
                ]
            ]
        )

        await message.answer_photo(
            photo=photo_id,
            caption=text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


@dp.callback_query(lambda callback_query: callback_query.data.startswith('show_qr_'))
async def show_qr_code(callback_query: types.CallbackQuery):
    ticket_id = callback_query.data.split('_')[2]
    user_id = callback_query.from_user.id

    # Получаем данные билета из базы
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ticket_type, event_id
        FROM tickets
        WHERE ticket_id = ?
    ''', (ticket_id,))
    ticket = cursor.fetchone()

    # Получаем данные о пользователе
    cursor.execute('''
        SELECT first_name, last_name, middle_name, relationship_status
        FROM users
        WHERE user_id = ?
    ''', (user_id,))
    user_data = cursor.fetchone()
    conn.close()

    if not ticket or not user_data:
        await callback_query.message.edit_text("⚠️ QR-код не найден или данные пользователя отсутствуют.")
        return

    ticket_type, event_id = ticket
    first_name, last_name, middle_name, relationship_status = user_data
    print(first_name)
    # Формируем данные для нового QR-кода
    qr_data = {
        "ticket_id": ticket_id,
        "ticket_type": ticket_type,
        "event_id": event_id,
        "first_name": first_name,
        "last_name": last_name,
        "middle_name": middle_name or '',
        "status": relationship_status,
    }

    # Генерируем QR-код
    qr_json = json.dumps(qr_data, ensure_ascii=False)
    qr_buffer = await generate_qr_code(qr_json)

    qr_photo = BufferedInputFile(qr_buffer.getvalue(), filename="ticket_qr.png")
    await callback_query.message.answer_photo(
        photo=qr_photo,
        caption=f"🎟️ Ваш QR-код для билета ({ticket_type})\n"
                f"ID билета: `{ticket_id}`",
        parse_mode="Markdown"
    )



async def generate_qr_code(qr_json: str) -> BytesIO:
    from io import BytesIO
    import qrcode

    buffer = BytesIO()
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_json)  # Добавляем JSON-строку (включены русские буквы)
    qr.make(fit=True)

    qr_image = qr.make_image(fill_color="black", back_color="white")
    qr_image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


@dp.message(F.text == "⚙️ Настройки")
async def user_settings(message: Message):
    user_id = message.from_user.id

    # Подключаемся к базе данных, чтобы получить текущие данные пользователя
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT first_name, last_name, middle_name, relationship_status
        FROM users
        WHERE user_id = ?
    ''', (user_id,))
    user_data = cursor.fetchone()
    conn.close()

    if not user_data:
        await message.answer("⚠️ Вы еще не зарегистрированы. Пожалуйста, начните с команды /start.")
        return

    first_name, last_name, middle_name, relationship_status = user_data

    # Формируем сообщение с текущей информацией пользователя
    text = (
        f"⚙️ *Ваши текущие данные:*\n\n"
        f"👤 Имя: {first_name}\n"
        f"👤 Фамилия: {last_name}\n"
        f"👤 Отчество: {middle_name or 'не указано'}\n"
        f"❤️ Статус: {relationship_status}\n\n"
        f"Выберите, что вы хотите изменить:"
    )

    # Клавиатура с кнопками для изменения данных
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [types.KeyboardButton(text="Изменить имя"), types.KeyboardButton(text="Изменить фамилию")],
            [types.KeyboardButton(text="Изменить отчество"), types.KeyboardButton(text="Изменить статус")],
            [types.KeyboardButton(text="⬅️ Назад")]
        ]
    )

    await message.answer(text, reply_markup=keyboard)


@dp.message(F.text == "Изменить имя")
async def change_first_name(message: Message, state: FSMContext):
    await state.set_state(UserSetup.waiting_for_first_name)
    await message.answer("Введите ваше новое имя:")

@dp.message(F.text == "Изменить фамилию")
async def change_last_name(message: Message, state: FSMContext):
    await state.set_state(UserSetup.waiting_for_last_name)
    await message.answer("Введите вашу новую фамилию:")

@dp.message(F.text == "Изменить отчество")
async def change_middle_name(message: Message, state: FSMContext):
    await state.set_state(UserSetup.waiting_for_middle_name)
    await message.answer("Введите ваше новое отчество (или '-' для пропуска):")

@dp.message(F.text == "Изменить статус")
async def change_status(message: Message, state: FSMContext):
    await state.set_state(UserSetup.waiting_for_status)

    # Клавиатура для выбора статуса
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [types.KeyboardButton(text="Ищу отношения"), types.KeyboardButton(text="Занят")],
            [types.KeyboardButton(text="⬅️ Назад")]
        ]
    )
    await message.answer("Выберите ваш новый статус (нажмите на одну из кнопок):", reply_markup=keyboard)

@dp.message(F.text == "⬅️ Назад")
async def back_to_settings_menu(message: Message):
    buttons = await get_main_menu(message.from_user.id)
    await message.answer("Вы вернулись в главное меню.", reply_markup=buttons)







#ADMIN
class TicketScanning(StatesGroup):
    waiting_for_ticket_id = State()

@dp.message(F.text == "✅ Отметить билет")
async def scan_ticket_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет прав для сканирования билетов.")
        return

    await state.set_state(TicketScanning.waiting_for_ticket_id)
    await message.answer("Введите ID билета для отметки:")


@dp.message(TicketScanning.waiting_for_ticket_id)
async def process_ticket_scanning(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет прав для сканирования билетов.")
        return

    ticket_id = message.text.strip()

    # Проверяем статус билета
    ticket_status = await check_ticket_status(ticket_id)

    if not ticket_status:
        await message.answer("❌ Билет не найден.")
        await state.clear()
        return

    if ticket_status['scanned']:
        await message.answer("⚠️ Этот билет уже был использован!")
        await state.clear()
        return

    # Отмечаем билет как использованный
    await mark_ticket_as_scanned(ticket_id)

    await message.answer("✅ Билет успешно отмечен как использованный!")
    await state.clear()


@dp.message(Command('cleanup'))
async def manual_cleanup(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    deleted_count = await cleanup_past_events()

    if deleted_count > 0:
        await message.answer(
            f"✅ Очистка завершена!\n"
            f"Удалено {deleted_count} прошедших мероприятий и связанных с ними билетов."
        )
    else:
        await message.answer("🔍 Прошедших мероприятий не найдено.")


async def create_payment(event_id: int, ticket_type: str, amount: float) -> dict:
    """Создание платежа в ЮKassa"""
    try:
        payment = Payment.create({
            "amount": {
                "value": str(amount),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/Stud_VPN_bot"  # URL для возврата после оплаты
            },
            "capture": True,
            "description": f"Билет {ticket_type} на мероприятие {event_id}",
            "metadata": {
                "event_id": event_id,
                "ticket_type": ticket_type,
            }
        })
        return {
            "payment_id": payment.id,
            "payment_url": payment.confirmation.confirmation_url
        }
    except Exception as e:
        print(f"Ошибка при создании платежа: {e}")
        return None


@dp.callback_query(lambda c: c.data.startswith('register_'))
async def process_registration(callback_query: types.CallbackQuery):
    _, event_id, ticket_type = callback_query.data.split('_')
    user_id = callback_query.from_user.id

    # Получаем информацию о мероприятии
    event = await get_event(event_id)

    # Определяем цену в зависимости от типа билета
    price_map = {
        'standard': event['standard_price'],
        'fasttrack': event['fasttrack_price'],
        'vip': event['vip_price']
    }
    amount = price_map.get(ticket_type)

    # Создаем платеж
    payment_data = await create_payment(event_id, ticket_type, amount)

    if not payment_data:
        await callback_query.answer("Ошибка при создании платежа", show_alert=True)
        return

    # Создаем клавиатуру с кнопкой оплаты
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(
            text="Оплатить",
            url=payment_data["payment_url"]
        )],
        [types.InlineKeyboardButton(
            text="Проверить оплату",
            callback_data=f"check_payment_{payment_data['payment_id']}_{event_id}_{ticket_type}"
        )]
    ])

    await callback_query.message.answer(
        f"Для получения билета, пожалуйста, оплатите {amount} руб.",
        reply_markup=keyboard
    )


@dp.callback_query(lambda c: c.data.startswith('check_payment_'))
async def check_payment_status(callback_query: types.CallbackQuery):
    data = callback_query.data[14:]  # Пропускаем 'check_payment_'

    # Находим последние два элемента после последнего дефиса
    parts = data.rsplit('_', 2)  # Разделяем строку на 3 части с конца
    if len(parts) != 3:
        await callback_query.answer("Ошибка в формате данных", show_alert=True)
        return

    payment_id = parts[0]  # Полный ID платежа
    event_id = parts[1]  # ID события
    ticket_type = parts[2]  # Тип билета

    url = f"https://api.yookassa.ru/v3/payments/{payment_id}"
    print(payment_id)
    try:
        response = requests.get(
            url,
            auth=(SHOP_ID, API_KEY)
        )
        if response.status_code == 200:
            payment_info = response.json()
            x = payment_info.get('status')


            if x == "succeeded":
                # Регистрируем участника
                success = await register_participant(event_id, callback_query.from_user.id, ticket_type)
                print(1)

                if success:
                    # Получаем информацию о мероприятии
                    event = await get_event(event_id)
                    print(2)
                    # Формируем данные для билета
                    ticket_data = {
                        'event_id': event_id,
                        'event_title': event['title'],
                        'ticket_type': ticket_type,
                        'user_id': callback_query.from_user.id,
                        'event_date': event['date_time']
                    }

                    # Генерируем QR-код
                    qr_buffer, ticket_id = await generate_qr_code_start(ticket_data)
                    print(3)
                    caption = (
                        f"🎫 *Ваш билет на мероприятие*\n\n"
                        f"🎉 Мероприятие: {event['title']}\n"
                        f"📅 Дата: {event['date_time']}\n"
                        f"📍 Место: {event['location']}\n"
                        f"🎟️ Тип билета: {ticket_type}\n"
                        f"🔑 ID билета: `{ticket_id}`"
                    )

                    photo = BufferedInputFile(qr_buffer.getvalue(), filename="ticket_qr.png")
                    print(4)
                    await callback_query.message.answer_photo(
                        photo=photo,
                        caption=caption,
                        parse_mode="Markdown"
                    )

                    await callback_query.answer("Оплата прошла успешно! Билет сформирован.", show_alert=True)
                else:
                    await callback_query.answer("Ошибка при регистрации участника", show_alert=True)
            else:
                await callback_query.answer("Оплата еще не произведена", show_alert=True)
        else:
            await callback_query.answer("Оплата", show_alert=True)
    except Exception as e:
        print(f"Ошибка при создании платежа: {e}")


async def delete_event(event_id: int) -> bool:
    """Удаление мероприятия и всех связанных данных."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Удаление билетов, связанных с мероприятием
        cursor.execute("DELETE FROM tickets WHERE event_id = ?", (event_id,))

        # Удаление самого мероприятия
        cursor.execute("DELETE FROM events WHERE event_id = ?", (event_id,))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка при удалении мероприятия: {e}")
        return False


@dp.message(F.text == "🗑️ Удалить мероприятие")
async def start_event_deletion(message: Message):
    """Начало процесса удаления мероприятия."""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⚠️ У вас нет прав для удаления мероприятий.")
        return

    events = await get_all_events()
    if not events:
        await message.answer("⚠️ Нет мероприятий для удаления.")
        return

    # Формируем список кнопок
    buttons = [
        [
            types.InlineKeyboardButton(
                text=f"{event['title']} ({event['date_time']})",
                callback_data=f"delete_event_{event['event_id']}"
            )
        ]
        for event in events
    ]

    # Создаем клавиатуру
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer("Выберите мероприятие для удаления:", reply_markup=keyboard)




@dp.callback_query(lambda c: c.data.startswith("delete_event_"))
async def confirm_event_deletion(callback_query: types.CallbackQuery):
    """Подтверждение удаления мероприятия."""
    event_id = int(callback_query.data.split("_")[2])
    event = await get_event(event_id)

    if not event:
        await callback_query.answer("Мероприятие не найдено.", show_alert=True)
        return

    # Клавиатура подтверждения
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{event_id}"),
            types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")
        ]
    ])

    await callback_query.message.answer(
        f"Вы уверены, что хотите удалить мероприятие *{event['title']}*?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@dp.callback_query(lambda c: c.data.startswith("confirm_delete_"))
async def delete_event_handler(callback_query: types.CallbackQuery):
    """Обработчик удаления мероприятия."""
    event_id = int(callback_query.data.split("_")[2])

    success = await delete_event(event_id)
    if success:
        await callback_query.message.answer("✅ Мероприятие успешно удалено вместе со всеми связанными данными.")
    else:
        await callback_query.message.answer("❌ Произошла ошибка при удалении мероприятия.")


@dp.callback_query(lambda c: c.data == "cancel_delete")
async def cancel_event_deletion(callback_query: types.CallbackQuery):
    """Отмена удаления мероприятия."""
    await callback_query.message.answer("❌ Удаление мероприятия отменено!")


async def main():
    await create_database()
    print(1)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
