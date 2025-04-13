import sqlite3
import datetime
import asyncio
import os
import datetime
from datetime import datetime

DATABASE_FILE = "naglobase.db"


async def create_database():
    """Создание базы данных для мероприятий"""
    print("член")
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Создание таблицы мероприятий (оставляем как есть)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            date_time TEXT NOT NULL,
            location TEXT,
            max_participants INTEGER,
            current_participants INTEGER DEFAULT 0,
            photo_id TEXT,
            standard_price REAL,
            fasttrack_price REAL,
            vip_price REAL,
            status TEXT DEFAULT 'active'
        )
        ''')

        cursor.execute('''
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            middle_name TEXT,
            relationship_status TEXT DEFAULT 'ищу отношения'
        )
        ''')

        # Создание таблицы участников (оставляем как есть)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS participants (
            participant_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            user_id INTEGER,
            ticket_type TEXT,
            registration_date TEXT,
            payment_status TEXT DEFAULT 'pending',
            FOREIGN KEY (event_id) REFERENCES events (event_id)
        )
        ''')

        # Добавляем новую таблицу для билетов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                event_id INTEGER,
                user_id INTEGER,
                ticket_type TEXT,
                creation_date TEXT,
                scanned INTEGER DEFAULT 0,
                scan_timestamp TEXT DEFAULT NULL,
                scanner_id TEXT DEFAULT NULL,
                FOREIGN KEY (event_id) REFERENCES events (event_id)
            )
            ''')


        conn.commit()
        conn.close()
        print("База данных успешно создана")

    except sqlite3.Error as e:
        print(f"Ошибка при создании базы данных: {e}")


async def save_ticket(ticket_id: str, ticket_data: dict):
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO tickets (
            ticket_id, event_id, user_id, ticket_type, creation_date, scanned
        )
        VALUES (?, ?, ?, ?, ?, 0)
        ''', (
            ticket_id,
            ticket_data['event_id'],
            ticket_data['user_id'],
            ticket_data['ticket_type'],
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка при сохранении билета: {e}")
        return False


async def verify_ticket(ticket_id: str) -> bool:
    """Проверка и использование билета"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Проверяем, не использован ли билет
        cursor.execute('SELECT used FROM tickets WHERE ticket_id = ?', (ticket_id,))
        result = cursor.fetchone()

        if not result:
            return False

        if result[0] == 1:
            return False  # Билет уже использован

        # Помечаем билет как использованный
        cursor.execute('''
        UPDATE tickets SET used = 1 
        WHERE ticket_id = ?
        ''', (ticket_id,))

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Ошибка при проверке билета: {e}")
        return False


async def check_ticket_status(ticket_id: str) -> dict:
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT scanned, ticket_type, event_id
        FROM tickets
        WHERE ticket_id = ?
    ''', (ticket_id,))

    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            'scanned': bool(result[0]),
            'ticket_type': result[1],
            'event_id': result[2]
        }
    return None


async def mark_ticket_as_scanned(ticket_id: str) -> bool:
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Проверяем, существует ли билет
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE ticket_id = ?", (ticket_id,))
        ticket_exists = cursor.fetchone()[0]

        if not ticket_exists:
            conn.close()
            return False  # Билет не найден

        # Удаляем билет из базы данных
        cursor.execute("DELETE FROM tickets WHERE ticket_id = ?", (ticket_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка при отметке билета: {e}")
        return False


async def add_event(title, description, date_time, location, max_participants, photo_id,
                   standard_price, fasttrack_price, vip_price):
    """Добавление нового мероприятия"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO events (
            title, description, date_time, location, max_participants, 
            photo_id, standard_price, fasttrack_price, vip_price
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, description, date_time, location, max_participants,
              photo_id, standard_price, fasttrack_price, vip_price))

        conn.commit()
        conn.close()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Ошибка при добавлении мероприятия: {e}")
        return None

async def get_event(event_id):
    """Получение информации о мероприятии"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM events WHERE event_id = ?', (event_id,))
        event = cursor.fetchone()

        if event:
            return {
                'event_id': event[0],
                'title': event[1],
                'description': event[2],
                'date_time': event[3],
                'location': event[4],
                'max_participants': event[5],
                'current_participants': event[6],
                'photo_id': event[7],
                'standard_price': event[8],
                'fasttrack_price': event[9],
                'vip_price': event[10],
                'status': event[11]
            }
        conn.close()
        return None
    except sqlite3.Error as e:
        print(f"Ошибка при получении мероприятия: {e}")
        return None

async def register_participant(event_id, user_id, ticket_type):
    """Регистрация участника на мероприятие"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Проверка наличия свободных мест
        cursor.execute('SELECT max_participants, current_participants FROM events WHERE event_id = ?', (event_id,))
        event = cursor.fetchone()

        if event and event[0] > event[1]:
            # Регистрация участника
            registration_date = datetime.now()
            cursor.execute('''
            INSERT INTO participants (event_id, user_id, ticket_type, registration_date)
            VALUES (?, ?, ?, ?)
            ''', (event_id, user_id, ticket_type, registration_date))

            # Обновление количества участников
            cursor.execute('''
            UPDATE events 
            SET current_participants = current_participants + 1 
            WHERE event_id = ?
            ''', (event_id,))

            conn.commit()
            conn.close()
            return True
        return False
    except sqlite3.Error as e:
        print(f"Ошибка при регистрации участника: {e}")
        return False

async def get_all_events():
    """Получение списка всех мероприятий"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM events WHERE status = "active" ORDER BY date_time')
        events = cursor.fetchall()
        conn.close()
        return [{
            'event_id': event[0],
            'title': event[1],
            'description': event[2],
            'date_time': event[3],
            'location': event[4],
            'max_participants': event[5],
            'current_participants': event[6],
            'photo_id': event[7],
            'standard_price': event[8],
            'fasttrack_price': event[9],
            'vip_price': event[10],
            'status': event[11]
        } for event in events]
    except sqlite3.Error as e:
        print(f"Ошибка при получении списка мероприятий: {e}")
        return []


async def cleanup_past_events():
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Получаем текущую дату и время
        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Сначала получаем ID всех прошедших мероприятий
        cursor.execute('''
            SELECT event_id FROM events 
            WHERE datetime(date_time) < datetime(?)
        ''', (current_datetime,))
        past_events = cursor.fetchall()

        # Удаляем связанные билеты
        cursor.execute('''
            DELETE FROM tickets 
            WHERE event_id IN (
                SELECT event_id FROM events 
                WHERE datetime(date_time) < datetime(?)
            )
        ''', (current_datetime,))

        # Удаляем сами мероприятия
        cursor.execute('''
            DELETE FROM events 
            WHERE datetime(date_time) < datetime(?)
        ''', (current_datetime,))

        conn.commit()
        conn.close()

        return len(past_events)
    except Exception as e:
        print(f"Ошибка при удалении прошедших мероприятий: {e}")
        return 0

# Пример использования:
async def main():
    # Создание базы данных
    await create_database()

    # Добавление мероприятия

    # Получение информации о мероприятии

    # Регистрация участника

    # Получение всех мероприятий
    all_events = await get_all_events()
    print("Все мероприятия:", all_events)

if __name__ == '__main__':
    asyncio.run(main())
