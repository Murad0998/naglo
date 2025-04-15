import requests
import uuid
from yookassa import Configuration, Payment

# Данные ЮKassa
Configuration.account_id = '1058043'    # например, "1020973"
Configuration.secret_key = 'live_WaOeO9R3nCYzu3PTrW-HH76fEm4LxfiPQfXvppW9X-Q'
"live_FosI0F8F_OqOHsJM4tiWtCfPBSZAVGma8J90WRRK7Ks"
SHOP_ID = '1058043'
API_KEY = 'live_WaOeO9R3nCYzu3PTrW-HH76fEm4LxfiPQfXvppW9X-Q'
RETURN_URL = 'https://t.me/Stud_VPN_bot'

async def create_payment(amount, description, email=None):
    payment_id = str(uuid.uuid4())  # Уникальный ID платежа
    idempotence_key = str(uuid.uuid4())  # Уникальный идемпотентный ключ

    # Формируем базовую структуру платежа
    payment = Payment.create({
        "amount": {
            "value": str(amount),
            "currency": "RUB"
        },
        "capture": True,
        "confirmation": {
            "type": "redirect",
            "return_url": "https://www.example.com/return_url"
        },
        "description": description,
        "metadata": {
            "order_id": payment_id
        },
        "receipt": {
            "customer": {
                "email": "user@example.com"
            },
            "items": [
                {
                    "description": f"Билет на вечеринку {amount}",
                    "quantity": 1,
                    "amount": {
                        "value": str(amount),
                        "currency": "RUB"
                    },
                    "vat_code": 1
                }
            ]
        }
    }, idempotence_key)

    try:
        # Создаём платеж через API ЮKassa

        # Если библиотека возвращает объект с confirmation, получаем нужные поля:
        return payment.confirmation.confirmation_url, payment.id

    except Exception as e:
        print(f"Ошибка при создании платежа: {e}")
        return None


async def check_payment_status(payment_id):
    url = f"https://api.yookassa.ru/v3/payments/{payment_id}"
    try:
        response = requests.get(
            url,
            auth=(SHOP_ID, API_KEY)
        )
        if response.status_code == 200:
            payment_info = response.json()
            return payment_info.get('status')  # Вернёт 'succeeded', 'pending', 'canceled' и т.д.
        else:
            print("Ошибка при проверке статуса платежа:", response.status_code, response.text)
            return None
    except Exception as e:
        print("Ошибка соединения с ЮKassa при проверке статуса:", e)
        return None