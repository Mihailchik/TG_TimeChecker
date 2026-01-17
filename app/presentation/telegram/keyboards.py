from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from typing import List

def get_main_menu_keyboard(has_active_shift: bool):
    text = "Завершить смену" if has_active_shift else "Начать работу"
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=text)],
            [KeyboardButton(text="Мой профиль"), KeyboardButton(text="Написать менеджеру")]
        ],
        resize_keyboard=True
    )

def get_sites_keyboard(sites: List[str]):
    buttons = [[KeyboardButton(text=site)] for site in sites]
    buttons.append([KeyboardButton(text="Отмена")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_geo_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить геолокацию", request_location=True)],
            [KeyboardButton(text="Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False # Persist until success
    )

def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True
    )

def get_contact_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить телефон", request_contact=True)],
            [KeyboardButton(text="Отмена")]
        ],
        resize_keyboard=True
    )
