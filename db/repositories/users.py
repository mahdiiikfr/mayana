import aiosqlite
from typing import Optional, Dict, Any
from db.base import BaseRepository


class UserRepository(BaseRepository):
    """
    UserRepository handles all direct queries and operations related to users table.
    """

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves user information by their Telegram User ID.
        """
        query = "SELECT user_id, username, language_code, phone_number, is_verified, created_at FROM users WHERE user_id = ?;"
        async with self.connection.execute(query, (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "user_id": row[0],
                    "username": row[1],
                    "language_code": row[2],
                    "phone_number": row[3],
                    "is_verified": bool(row[4]),
                    "created_at": row[5]
                }
            return None

    async def create_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        language_code: str = 'fa'
    ) -> Dict[str, Any]:
        """
        Creates a new user record if they do not exist, or returns the existing user.
        """
        existing_user = await self.get_user(user_id)
        if existing_user:
            return existing_user

        query = """
        INSERT INTO users (user_id, username, language_code)
        VALUES (?, ?, ?)
        """
        await self.connection.execute(query, (user_id, username, language_code))
        await self.connection.commit()

        return await self.get_user(user_id)

    async def update_language(self, user_id: int, language_code: str) -> bool:
        """
        Updates the selected language code for a user.
        """
        query = "UPDATE users SET language_code = ? WHERE user_id = ?;"
        async with self.connection.execute(query, (language_code, user_id)) as cursor:
            await self.connection.commit()
            return cursor.rowcount > 0

    async def update_phone(self, user_id: int, phone_number: str, is_verified: bool = True) -> bool:
        """
        Saves the verified phone number and updates the user's verification status.
        """
        query = "UPDATE users SET phone_number = ?, is_verified = ? WHERE user_id = ?;"
        async with self.connection.execute(query, (phone_number, int(is_verified), user_id)) as cursor:
            await self.connection.commit()
            return cursor.rowcount > 0
