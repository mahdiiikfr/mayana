from aiogram.fsm.state import State, StatesGroup


class BuyVPSState(StatesGroup):
    """
    FSM States for purchasing a new virtual private server.
    """
    select_location = State()  # Network selection representing data center location
    select_flavor = State()    # Flavor / plan selection
    select_image = State()     # Operating System image selection
    confirm_purchase = State() # Final verification state
