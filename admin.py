import asyncio
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile
from datetime import datetime
import json
import sqlite3
from aiogram import Bot, Dispatcher, types, F, Router  # Добавляем импорт F
from aiogram.filters import Command
from aiogram.types import Message
import qrcode
from io import BytesIO
import uuid
DATABASE_FILE = "events6.db"
ADMIN_IDS = [5510185795]
@dp.message(F.text == "✅ Отметить билет")
async def scan_ticket_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет прав для сканирования билетов.")
        return

    await state.set_state(TicketScanning.waiting_for_ticket_id)
    await message.answer("Введите ID билета для отметки:")

if __name__ == '__main__':
    asyncio.run(main())
