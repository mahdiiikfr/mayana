from aiogram.fsm.state import State, StatesGroup


class BroadcastState(StatesGroup):
    """
    FSM States for administrator broadcast messages.
    """
    enter_message = State() # Admin inputs broadcast message text/media


class ChargeUserState(StatesGroup):
    """
    FSM States for manual user wallet top ups.
    """
    enter_user_id = State() # Admin inputs target user telegram ID
    enter_amount = State()  # Admin inputs amount to credit/debit
