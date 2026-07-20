import aiosqlite


class BaseRepository:
    """
    Base Repository class that receives the database connection.
    All other database repositories inherit from this class.
    """
    def __init__(self, connection: aiosqlite.Connection) -> None:
        self.connection = connection
