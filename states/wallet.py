from aiogram.fsm.state import State, StatesGroup


class DepositState(StatesGroup):
    """
    FSM States for topping up/depositing funds into the wallet.
    """
    enter_amount = State() # User inputs deposit amount
