from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()

class StartShiftStates(StatesGroup):
    waiting_for_site = State()
    waiting_for_geo = State()
    waiting_for_video = State()

class EndShiftStates(StatesGroup):
    waiting_for_geo = State()
    waiting_for_video = State()
    waiting_for_comment = State()

class MessageManagerState(StatesGroup):
    waiting_for_message = State() # If error occurs
