from aiogram import Router, F, html
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from app.use_cases.shift_manager import ShiftController
from app.presentation.telegram.keyboards import (
    get_main_menu_keyboard, get_sites_keyboard, get_geo_keyboard, 
    get_cancel_keyboard, get_contact_keyboard
)
from app.presentation.telegram.states import StartShiftStates, EndShiftStates, RegistrationStates, MessageManagerState
from app.use_cases.video.video_upload import VideoUploadService

router = Router()
_controller: ShiftController = None
_video_service: VideoUploadService = None

def setup_router(controller: ShiftController, video_service: VideoUploadService = None):
    global _controller, _video_service
    _controller = controller
    _video_service = video_service
    return router

@router.message(CommandStart())
async def command_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    # Check Registration
    if not _controller.is_user_registered(user_id):
        await message.answer(
            f"Привет, {html.bold(message.from_user.full_name)}! 👋\n"
            "Для начала работы нужно зарегистрироваться.\n"
            "Как вас зовут? (Введите ФИО)",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(RegistrationStates.waiting_for_name)
        return

    active_shift = _controller.get_active_shift(user_id)
    await message.answer(
        "Добро пожаловать в систему учёта времени.",
        reply_markup=get_main_menu_keyboard(bool(active_shift))
    )

# --- REGISTRATION ---
@router.message(RegistrationStates.waiting_for_name)
async def process_reg_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Отлично! Теперь отправьте ваш номер телефона (нажмите кнопку).", reply_markup=get_contact_keyboard())
    await state.set_state(RegistrationStates.waiting_for_phone)

@router.message(RegistrationStates.waiting_for_phone, F.contact)
async def process_reg_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    full_name = data['full_name']
    phone = message.contact.phone_number
    
    _controller.register_user(message.from_user.id, message.from_user.username, full_name, phone)
    
    await state.clear()
    await message.answer("Регистрация успешна! ✅\nТеперь вы можете начать работу.", reply_markup=get_main_menu_keyboard(False))

@router.message(RegistrationStates.waiting_for_phone, ~F.contact)
async def invalid_reg_phone(message: Message):
    await message.answer("Пожалуйста, нажмите кнопку 'Отправить телефон'.", reply_markup=get_contact_keyboard())

# --- CANCEL ---
@router.message(F.text == "Отмена")
async def process_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None: return

    # If canceling, we assume shift tracking aborts? 
    # User said: "if problem -> row hangs".
    # If they press cancel, we probably shouldn't kill the shift record in DB (keep it as abandoned log?),
    # but for UI user needs to reset.
    await state.clear()
    user_id = message.from_user.id
    active_shift = _controller.get_active_shift(user_id)
    await message.answer("Действие отменено.", reply_markup=get_main_menu_keyboard(bool(active_shift)))

@router.message(F.text == "Мой профиль")
async def process_profile(message: Message):
    user_id = message.from_user.id
    user = _controller.user_manager.get_user(user_id)
    if not user:
        await message.answer("Профиль не найден. Нажмите /start для регистрации.")
        return
        
    await message.answer(
        f"👤 <b>Ваш профиль</b>\n\n"
        f"ФИО: {user['full_name']}\n"
        f"Телефон: {user['phone']}\n"
        f"ID: {user['user_id']}"
    )

# --- START SHIFT ---
@router.message(F.text == "Начать работу")
async def start_shift_btn(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Strict Registration Check
    if not _controller.is_user_registered(user_id):
        await message.answer("⚠️ Вы не зарегистрированы. Введите /start")
        return

    active_shift = _controller.get_active_shift(user_id)
    
    if active_shift:
        project = active_shift['project'] or "Не выбран"
        start_time = active_shift['start_time'].strftime("%H:%M")
        
        await message.answer(
            f"❌ <b>Смена уже активна!</b>\n\n"
            f"Объект: {project}\n"
            f"Время начала: {start_time}\n\n"
            "Чтобы начать новую, завершите текущую.", 
            reply_markup=get_main_menu_keyboard(True)
        )
        return
    
    # Init Record
    if not _controller.init_shift(user_id):
        await message.answer("Ошибка создания смены.")
        return

    sites = await _controller.get_available_sites()
    await message.answer("Выберите объект:", reply_markup=get_sites_keyboard(sites))
    await state.set_state(StartShiftStates.waiting_for_site)

@router.message(StartShiftStates.waiting_for_site)
async def process_site(message: Message, state: FSMContext):
    sites = await _controller.get_available_sites()
    if message.text not in sites:
        await message.answer("Выберите объект из меню.", reply_markup=get_sites_keyboard(sites))
        return
    
    _controller.set_shift_site(message.from_user.id, message.text)
    
    await message.answer("Отправьте геолокацию.", reply_markup=get_geo_keyboard())
    await state.set_state(StartShiftStates.waiting_for_geo)

@router.message(StartShiftStates.waiting_for_geo, F.location)
async def process_start_geo(message: Message, state: FSMContext):
    geo = f"{message.location.latitude},{message.location.longitude}"
    _controller.set_shift_start_geo(message.from_user.id, geo)
    
    await message.answer("Геолокация принята. Отправьте видео.", reply_markup=get_cancel_keyboard())
    await state.set_state(StartShiftStates.waiting_for_video)

@router.message(StartShiftStates.waiting_for_video, F.video_note | F.video)
async def process_start_video(message: Message, state: FSMContext):
    video_type = "file" if message.video else "circle"
    obj = message.video if message.video else message.video_note
    file_id = obj.file_id
    
    # Store only "ID|TYPE" - video will be uploaded to Drive later
    stored_id = f"{file_id}|{video_type}"
    user_id = message.from_user.id
    
    # 1. Upload Start Video Immediately
    msg = await message.answer("⏳ Смена началась. Видео загружается в облако...")
    video_link = None
    
    shift = _controller.get_active_shift(user_id)
    if shift and _video_service:
        try:
            from datetime import datetime
            shift_id = shift['shift_id']
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"{shift_id}_start_{date_str}.mp4"
            
            video_link = await _video_service.upload_telegram_video(message.bot, file_id, filename)
        except Exception as e:
            await message.answer(f"⚠️ Ошибка загрузки видео: {e}")
            
    # 2. Set Status (and Log to Sheets)
    await _controller.set_shift_start_video(user_id, stored_id, video_link)
    
    await msg.delete()
    await state.clear()
    
    # Get ID again or just generate from start_time? Not needed.
    await message.answer("✅ Смена успешно начата!\nДанные сохранены в таблице.", reply_markup=get_main_menu_keyboard(True))

# --- END SHIFT ---
@router.message(F.text.in_({"Завершить работу", "Завершить смену"}))
async def end_shift_btn(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not _controller.is_user_registered(user_id):
        await message.answer("⚠️ Вы не зарегистрированы. Введите /start")
        return

    if not _controller.get_active_shift(user_id):
        await message.answer("Нет активной смены.", reply_markup=get_main_menu_keyboard(False))
        return

    await message.answer("Отправьте геолокацию для завершения.", reply_markup=get_geo_keyboard())
    await state.set_state(EndShiftStates.waiting_for_geo)

@router.message(EndShiftStates.waiting_for_geo, F.location)
async def process_end_geo(message: Message, state: FSMContext):
    geo = f"{message.location.latitude},{message.location.longitude}"
    _controller.set_shift_end_geo(message.from_user.id, geo)
    
    await message.answer("Отправьте финальное видео.", reply_markup=get_cancel_keyboard())
    await state.set_state(EndShiftStates.waiting_for_video)

@router.message(EndShiftStates.waiting_for_video, F.video_note | F.video)
async def process_end_video(message: Message, state: FSMContext):
    video_type = "file" if message.video else "circle"
    obj = message.video if message.video else message.video_note
    file_id = obj.file_id
    
    # Store only "ID|TYPE" - video will be uploaded to Drive later
    stored_id = f"{file_id}|{video_type}"
    
    user_id = message.from_user.id
    
    # Clear state immediately
    await state.clear()
    
    # Respond to user immediately
    await message.answer("✅ Смена завершается, данные сохраняются...", reply_markup=get_main_menu_keyboard(False))
    
    # Process in background
    import asyncio
    async def finalize_in_background():
        try:
            # Get shift data to upload start video too
            shift = _controller.get_active_shift(user_id)
            
            # Upload videos to Drive if service available
            start_video_link = None
            end_video_link = None
            
            if _video_service and shift:
                from datetime import datetime
                shift_id = shift.get('shift_id', 'unknown')
                date_str = datetime.now().strftime("%Y-%m-%d")

                # Upload start video
                start_vid_parts = shift.get('start_video_id', '').split('|')
                if len(start_vid_parts) >= 2:
                    start_file_id = start_vid_parts[0]
                    start_filename = f"{shift_id}_start_{date_str}.mp4"
                    
                    start_video_link = await _video_service.upload_telegram_video(
                        message.bot, start_file_id, start_filename
                    )
                
                # Upload end video
                end_filename = f"{shift_id}_end_{date_str}.mp4"
                end_video_link = await _video_service.upload_telegram_video(
                    message.bot, file_id, end_filename
                )
            
            # Finalize shift with video links
            success, err, res = await _controller.finalize_shift(
                user_id, stored_id, start_video_link, end_video_link
            )
            
            if success:
                hours = int(res['hours'])
                minutes = int((res['hours'] * 60) % 60)
                await message.answer(f"🏁 Смена завершена!\nВремя: {hours}ч {minutes}м\nСтатус: {res['status']}")
            else:
                await message.answer(f"⚠️ Ошибка при сохранении: {err}")
        except Exception as e:
            print(f"Background finalize error: {e}")
            import traceback
            traceback.print_exc()
            await message.answer(f"⚠️ Ошибка: {str(e)}")
    
    # Start background task
    asyncio.create_task(finalize_in_background())

# --- MESSAGE TO MANAGER ---
@router.message(F.text == "Написать менеджеру")
async def msg_manager_start(message: Message, state: FSMContext):
    """Emergency reset and message sending."""
    await state.clear()
    await message.answer(
        "📝 Введите ваше сообщение для менеджера.\n\n"
        "⚠️ ВНИМАНИЕ: Если у вас была начата смена, она будет ПРИНУДИТЕЛЬНО ЗАВЕРШЕНА.",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(MessageManagerState.waiting_for_message)

@router.message(MessageManagerState.waiting_for_message)
async def msg_manager_send(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    
    # Process emergency message
    await _controller.handle_manager_message(user_id, text)
    
    await state.clear()
    await message.answer(
        "✅ Сообщение отправлено.\nТекущая смена (если была) закрыта.\nБот готов к новой регистрации/смене.",
        reply_markup=get_main_menu_keyboard(False)
    )
