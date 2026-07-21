import asyncio
import json
import os
import shlex
import sys
import logging
import re
import aiohttp
from typing import Any, Dict, List, Optional
from config import settings

logger = logging.getLogger("bot.services.openstack")


class OpenStackAPIError(Exception):
    """Exception raised for errors occurring during OpenStack API commands."""
    def __init__(self, message: str, stderr: Optional[str] = None) -> None:
        super().__init__(message)
        self.stderr = stderr


def country_code_to_flag(code: str) -> str:
    """Converts a 2-letter country code (e.g., 'FR', 'DE') to its Flag Emoji."""
    if not code or len(code) != 2:
        return "🌐"
    code = code.upper()
    try:
        return chr(127397 + ord(code[0])) + chr(127397 + ord(code[1]))
    except Exception:
        return "🌐"


def extract_ip_from_cidr(cidr: str) -> str:
    """Extracts a queryable IP address from a CIDR notation (e.g., '193.233.1.0/24')."""
    match = re.match(r"^(\d{1,3}\.\d{1,3}\.\d{1,3})\.\d{1,3}(?:/\d+)?$", cidr.strip())
    if match:
        return f"{match.group(1)}.1"
    return ""


class OpenStackService:
    """
    OpenStackService acts as an asynchronous wrapper over OpenStack Client CLI.
    It reads environment/credentials by sourcing openrc.sh, executes commands,
    and returns parsed JSON responses.
    All user-provided inputs are securely escaped to prevent command injections.
    """
    # Class-level in-memory cache for resolved network GeoIP location descriptions
    # format: network_id -> "🇫🇷 France (Internet-12)"
    _geoip_cache: Dict[str, str] = {}

    def __init__(self, openrc_path: str = settings.OPENRC_PATH) -> None:
        self.openrc_path = openrc_path

    async def _run_command(self, command: str) -> Any:
        """
        Helper method to source openrc.sh and run an OpenStack CLI command.
        Appends '-f json' automatically to command, executes in a shell asynchronously,
        and returns parsed JSON output.
        """
        # Formulate shell command: source openrc.sh, and execute the openstack command with JSON output format
        full_command = f"source {self.openrc_path} && {command} -f json"

        # Start async subprocess with shell
        process = await asyncio.create_subprocess_shell(
            full_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            executable="/bin/bash"  # explicitly use bash to support sourcing openrc.sh
        )

        stdout, stderr = await process.communicate()
        stdout_str = stdout.decode("utf-8").strip()
        stderr_str = stderr.decode("utf-8").strip()

        if process.returncode != 0:
            raise OpenStackAPIError(
                message=f"Command execution failed with return code {process.returncode}.",
                stderr=stderr_str
            )

        if not stdout_str:
            return None

        try:
            return json.loads(stdout_str)
        except json.JSONDecodeError as e:
            raise OpenStackAPIError(
                message=f"Failed to parse JSON response from command: {stdout_str[:100]}...",
                stderr=str(e)
            )

    # --- READ OPERATIONS ---

    async def get_flavors(self) -> List[Dict[str, Any]]:
        """
        Retrieves the list of available flavors (VPS plans) from OpenStack.
        """
        result = await self._run_command("openstack flavor list")
        if isinstance(result, list):
            return result
        return []

    async def get_images(self) -> List[Dict[str, Any]]:
        """
        Retrieves the list of available operating system images.
        """
        result = await self._run_command("openstack image list")
        if isinstance(result, list):
            return result
        return []

    async def get_networks(self) -> List[Dict[str, Any]]:
        """
        Retrieves the list of available networks.
        """
        result = await self._run_command("openstack network list")
        if isinstance(result, list):
            return result
        return []

    async def get_subnets(self) -> List[Dict[str, Any]]:
        """
        Retrieves the list of available subnets from OpenStack.
        """
        result = await self._run_command("openstack subnet list")
        if isinstance(result, list):
            return result
        return []

    async def get_servers(self) -> List[Dict[str, Any]]:
        """
        Retrieves a list of all server instances.
        """
        result = await self._run_command("openstack server list")
        if isinstance(result, list):
            return result
        return []

    async def get_server_details(self, server_id: str) -> Dict[str, Any]:
        """
        Retrieves detailed state, status, and IP address configuration of a specific server.
        """
        safe_server_id = shlex.quote(server_id)
        result = await self._run_command(f"openstack server show {safe_server_id}")
        # Server show returns a single object (dict in python or a single item representing attributes)
        if isinstance(result, dict):
            return result
        elif isinstance(result, list):
            # Sometimes a list of key-value properties is returned by CLI, convert to Dict
            return {item.get("Field", item.get("properties", "")): item.get("Value", "") for item in result if "Field" in item}
        return {}

    # --- AUTOMATED GEOIP RESOLVER WITH IN-MEMORY CACHING ---

    async def resolve_network_geoip(self, network_id: str, network_name: str) -> str:
        """
        Automatically resolves the geographic location of a network using its subnets.
        1. Finds corresponding subnet CIDR.
        2. Resolves Country & Country Code using ip-api.com.
        3. Returns a beautifully formatted location name (e.g. '🇫🇷 France (Internet-12)').
        """
        # Return from cache if already resolved
        if network_id in self._geoip_cache:
            return self._geoip_cache[network_id]

        fallback_name = f"🌐 {network_name}"
        logger.info(f"Resolving GeoIP for network: {network_name} ({network_id})")

        try:
            # 1. Fetch subnets and find corresponding CIDR
            subnets = await self.get_subnets()
            target_cidr = ""
            for sub in subnets:
                net_ref = sub.get("Network", sub.get("network_id", ""))
                # Match either Network Name or Network ID
                if net_ref == network_id or net_ref == network_name:
                    target_cidr = sub.get("Subnet", sub.get("cidr", ""))
                    if target_cidr:
                        break

            if not target_cidr:
                logger.warning(f"No subnet found for network {network_name}")
                self._geoip_cache[network_id] = fallback_name
                return fallback_name

            # Extract a queryable IP
            ip_to_query = extract_ip_from_cidr(target_cidr)
            if not ip_to_query:
                logger.warning(f"Could not extract IP from CIDR: {target_cidr}")
                self._geoip_cache[network_id] = fallback_name
                return fallback_name

            # 2. Query ip-api.com for country location metadata
            url = f"http://ip-api.com/json/{ip_to_query}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        country = data.get("country", "")
                        country_code = data.get("countryCode", "")

                        if country and country_code:
                            flag = country_code_to_flag(country_code)
                            beautiful_name = f"{flag} {country} ({network_name})"
                            self._geoip_cache[network_id] = beautiful_name
                            logger.info(f"Successfully resolved: {beautiful_name}")
                            return beautiful_name

        except Exception as e:
            logger.error(f"Error during GeoIP resolution for network {network_name}: {e}")

        # Save fallback to cache to prevent constant failures flooding the external API
        self._geoip_cache[network_id] = fallback_name
        return fallback_name

    # --- WRITE / ACTION OPERATIONS ---

    async def create_server(
        self,
        name: str,
        flavor_id: str,
        image_id: str,
        network_id: str
    ) -> Dict[str, Any]:
        """
        Deploys a new virtual server instance with the specified flavor, image, and network.
        All inputs are securely escaped to prevent shell parameter injections.
        """
        safe_name = shlex.quote(name)
        safe_flavor_id = shlex.quote(flavor_id)
        safe_image_id = shlex.quote(image_id)
        safe_network_id = shlex.quote(network_id)

        cmd = f"openstack server create --flavor {safe_flavor_id} --image {safe_image_id} --network {safe_network_id} {safe_name}"
        result = await self._run_command(cmd)
        if isinstance(result, dict):
            return result
        elif isinstance(result, list):
            return {item.get("Field"): item.get("Value") for item in result if "Field" in item}
        return {}

    async def delete_server(self, server_id: str) -> bool:
        """
        Permanently deletes a VPS server instance.
        """
        safe_server_id = shlex.quote(server_id)
        await self._run_command(f"openstack server delete {safe_server_id}")
        return True

    async def stop_server(self, server_id: str) -> bool:
        """
        Powers off/stops a VPS server instance.
        """
        safe_server_id = shlex.quote(server_id)
        await self._run_command(f"openstack server stop {safe_server_id}")
        return True

    async def start_server(self, server_id: str) -> bool:
        """
        Powers on/starts a stopped VPS server instance.
        """
        safe_server_id = shlex.quote(server_id)
        await self._run_command(f"openstack server start {safe_server_id}")
        return True
