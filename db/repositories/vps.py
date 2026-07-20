import aiosqlite
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from db.base import BaseRepository


class VPSRepository(BaseRepository):
    """
    VPSRepository handles SQLite queries and state management for active/suspended VPS instances.
    """

    async def add_vps(
        self,
        user_id: int,
        openstack_uuid: str,
        server_name: str,
        ip_address: Optional[Any] = None,
        flavor: Optional[Any] = None,
        status: str = "ACTIVE",
        expires_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Saves a newly created OpenStack VPS instance details into the database.
        Ensures complex parameters like lists/dicts are serialized to strings before storing.
        """
        # Secure serialization of any dictionary/list parameters
        if isinstance(ip_address, (dict, list)):
            ip_address_str = json.dumps(ip_address)
        else:
            ip_address_str = str(ip_address) if ip_address is not None else None

        if isinstance(flavor, (dict, list)):
            flavor_str = json.dumps(flavor)
        else:
            flavor_str = str(flavor) if flavor is not None else None

        query = """
        INSERT INTO vps (user_id, openstack_uuid, server_name, ip_address, flavor, status, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        async with self.connection.execute(
            query,
            (user_id, openstack_uuid, server_name, ip_address_str, flavor_str, status, expires_at)
        ) as cursor:
            vps_id = cursor.lastrowid
            await self.connection.commit()
            return await self.get_vps_by_id(vps_id)

    async def get_user_vps_list(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all virtual servers registered under a specific Telegram user.
        """
        query = """
        SELECT vps_id, user_id, openstack_uuid, server_name, ip_address, flavor, status, created_at, expires_at
        FROM vps
        WHERE user_id = ?;
        """
        async with self.connection.execute(query, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            vps_list = []
            for row in rows:
                vps_list.append({
                    "vps_id": row[0],
                    "user_id": row[1],
                    "openstack_uuid": row[2],
                    "server_name": row[3],
                    "ip_address": row[4],
                    "flavor": row[5],
                    "status": row[6],
                    "created_at": row[7],
                    "expires_at": row[8]
                })
            return vps_list

    async def get_vps_by_id(self, vps_id: int) -> Optional[Dict[str, Any]]:
        """
        Gets details of a registered server using its internal table primary key ID.
        """
        query = """
        SELECT vps_id, user_id, openstack_uuid, server_name, ip_address, flavor, status, created_at, expires_at
        FROM vps
        WHERE vps_id = ?;
        """
        async with self.connection.execute(query, (vps_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "vps_id": row[0],
                    "user_id": row[1],
                    "openstack_uuid": row[2],
                    "server_name": row[3],
                    "ip_address": row[4],
                    "flavor": row[5],
                    "status": row[6],
                    "created_at": row[7],
                    "expires_at": row[8]
                }
            return None

    async def get_vps_by_uuid(self, openstack_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Gets details of a registered server using its external OpenStack UUID.
        """
        query = """
        SELECT vps_id, user_id, openstack_uuid, server_name, ip_address, flavor, status, created_at, expires_at
        FROM vps
        WHERE openstack_uuid = ?;
        """
        async with self.connection.execute(query, (openstack_uuid,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "vps_id": row[0],
                    "user_id": row[1],
                    "openstack_uuid": row[2],
                    "server_name": row[3],
                    "ip_address": row[4],
                    "flavor": row[5],
                    "status": row[6],
                    "created_at": row[7],
                    "expires_at": row[8]
                }
            return None

    async def update_vps_status(self, openstack_uuid: str, status: str) -> bool:
        """
        Updates the current runtime status (e.g., ACTIVE, SHUTOFF, SUSPENDED) of a server.
        """
        query = "UPDATE vps SET status = ? WHERE openstack_uuid = ?;"
        async with self.connection.execute(query, (status, openstack_uuid)) as cursor:
            await self.connection.commit()
            return cursor.rowcount > 0
