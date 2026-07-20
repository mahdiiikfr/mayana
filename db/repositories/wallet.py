import aiosqlite
from typing import Optional, List, Dict, Any
from db.base import BaseRepository


class WalletRepository(BaseRepository):
    """
    WalletRepository handles users' balances and transaction logs.
    Includes methods for deposit, deduction, and getting current balance safely.
    """

    async def get_balance(self, user_id: int) -> float:
        """
        Retrieves the user's current net balance from the transaction logs.
        Calculates balance based on latest transaction balance_after, falling back to 0.0.
        """
        query = """
        SELECT balance_after
        FROM wallet
        WHERE user_id = ? AND status = 'COMPLETED'
        ORDER BY transaction_id DESC
        LIMIT 1;
        """
        async with self.connection.execute(query, (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return float(row[0])
            return 0.0

    async def add_transaction(
        self,
        user_id: int,
        amount: float,
        transaction_type: str,  # 'charge' or 'deduction'
        status: str = "COMPLETED"
    ) -> Dict[str, Any]:
        """
        Saves a transaction record and updates the user's wallet.
        Auto-calculates the balance_after based on current balance and requested type.
        """
        current_balance = await self.get_balance(user_id)

        # Calculate new balance
        if status == "COMPLETED":
            if transaction_type == "charge":
                balance_after = current_balance + amount
            elif transaction_type == "deduction":
                balance_after = current_balance - amount
            else:
                raise ValueError("Invalid transaction_type. Must be 'charge' or 'deduction'.")
        else:
            balance_after = current_balance

        query = """
        INSERT INTO wallet (user_id, balance_after, transaction_type, amount, status)
        VALUES (?, ?, ?, ?, ?);
        """
        async with self.connection.execute(
            query,
            (user_id, balance_after, transaction_type, amount, status)
        ) as cursor:
            transaction_id = cursor.lastrowid
            await self.connection.commit()

            return {
                "transaction_id": transaction_id,
                "user_id": user_id,
                "balance_after": balance_after,
                "transaction_type": transaction_type,
                "amount": amount,
                "status": status
            }

    async def get_user_transactions(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieves historical transaction log entries for a user.
        """
        query = """
        SELECT transaction_id, user_id, balance_after, transaction_type, amount, status, created_at
        FROM wallet
        WHERE user_id = ?
        ORDER BY transaction_id DESC
        LIMIT ?;
        """
        async with self.connection.execute(query, (user_id, limit)) as cursor:
            rows = await cursor.fetchall()
            transactions = []
            for row in rows:
                transactions.append({
                    "transaction_id": row[0],
                    "user_id": row[1],
                    "balance_after": row[2],
                    "transaction_type": row[3],
                    "amount": row[4],
                    "status": row[5],
                    "created_at": row[6]
                })
            return transactions
