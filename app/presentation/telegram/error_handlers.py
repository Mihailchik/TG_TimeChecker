from aiogram import Router, F
from aiogram.types import Message
from app.presentation.telegram.states import StartShiftStates, EndShiftStates
from app.presentation.telegram.keyboards import get_geo_keyboard

router = Router()

@router.message(StartShiftStates.waiting_for_geo, ~F.location)
async def invalid_start_geo(message: Message):
    await message.answer("⚠️ Ошибка: Вы отправили что-то другое.\nНужно отправить геолокацию, нажав на кнопку ниже.", reply_markup=get_geo_keyboard())

@router.message(StartShiftStates.waiting_for_video, ~(F.video_note | F.video))
async def invalid_start_video(message: Message):
    await message.answer("⚠️ Ошибка: Это не видео.\nПожалуйста, отправьте видео-кружок или обычное видео.")

@router.message(EndShiftStates.waiting_for_geo, ~F.location)
async def invalid_end_geo(message: Message):
    await message.answer("⚠️ Ошибка: Жду геолокацию для завершения.", reply_markup=get_geo_keyboard())

@router.message(EndShiftStates.waiting_for_video, ~(F.video_note | F.video))
async def invalid_end_video(message: Message):
    await message.answer("⚠️ Ошибка: Для завершения смены нужно видео.")
