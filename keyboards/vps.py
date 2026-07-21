import re
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any
from services.openstack import OpenStackService

openstack = OpenStackService()


async def get_networks_keyboard(networks: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """
    Builds an inline keyboard representing available network locations.
    - Filters out networks with 'RESERVE', 'NOTWORKING', or 'IPv6-only' in their names.
    - Resolves network names automatically using OpenStack's subnets and GeoIP API.
    - Sorts alphabetically.
    """
    builder = InlineKeyboardBuilder()

    filtered_networks = []
    for net in networks:
        raw_name = net.get("Name", net.get("name", "Unknown Network"))
        net_id = net.get("ID", net.get("id", ""))

        # Check for reservation, broken or IPv6-only keywords
        upper_name = raw_name.upper()
        if "RESERVE" in upper_name or "NOTWORKING" in upper_name or "IPV6" in upper_name:
            continue

        # Resolve network geographic name asynchronously
        display_name = await openstack.resolve_network_geoip(net_id, raw_name)
        filtered_networks.append((display_name, net_id))

    # Sort alphabetically by network display name
    filtered_networks.sort(key=lambda x: x[0].lower())

    for display_name, net_id in filtered_networks:
        builder.button(text=display_name, callback_data=f"buy_net:{net_id}")

    builder.button(text="❌ Cancel", callback_data="buy_cancel")
    builder.adjust(1)
    return builder.as_markup()


def get_flavors_keyboard(flavors: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """
    Builds an inline keyboard representing available virtual server plans/flavors.
    - Sorts flavors numerically by RAM capacity (from small to large).
    """
    builder = InlineKeyboardBuilder()

    sorted_flavors = []
    for flv in flavors:
        name = flv.get("Name", flv.get("name", "Flavor"))
        flv_id = flv.get("ID", flv.get("id", ""))

        # Try to extract ram numerical value for sorting
        ram_val = flv.get("RAM", 0)
        try:
            ram_val = int(ram_val)
        except (ValueError, TypeError):
            # Parse ram from name if possible (e.g. vds.1c.1g)
            match = re.search(r"(\d+)\s*[gG]", name)
            if match:
                ram_val = int(match.group(1)) * 1024
            else:
                ram_val = 0

        vcpus = flv.get("VCPUs", "")
        disk = flv.get("Disk", "")
        sorted_flavors.append((ram_val, flv_id, name, vcpus, disk))

    # Sort flavors from smallest RAM to largest
    sorted_flavors.sort(key=lambda x: x[0])

    for ram, flv_id, name, vcpus, disk in sorted_flavors[:12]:  # display reasonable count
        btn_text = f"⚙️ {name} ({ram if ram > 0 else 'N/A'}MB RAM, {vcpus} vCPU, {disk}G Disk)"
        builder.button(text=btn_text, callback_data=f"buy_flv:{flv_id}")

    builder.button(text="🔙 Back", callback_data="buy_back_net")
    builder.button(text="❌ Cancel", callback_data="buy_cancel")
    builder.adjust(1)
    return builder.as_markup()


def beautify_image_name(name: str) -> str:
    """
    Cleans and structures raw OpenStack image names into sleek presentation names.
    - Removes '-amd64' or '.raw' suffixes.
    - Prefixes standard platforms with corresponding cute emojis.
    """
    clean_name = name.replace("-amd64", "").replace(".raw", "").replace("_", " ").strip()

    lower_name = clean_name.lower()
    if "ubuntu" in lower_name:
        if "3x-ui" in lower_name or "3xui" in lower_name:
            return f"⚡️ 3x-ui (Ubuntu {clean_name.replace('ubuntu', '').strip()})"
        return f"🐧 Ubuntu {clean_name.replace('ubuntu', '').strip()}"
    elif "debian" in lower_name:
        return f"🌀 Debian {clean_name.replace('debian', '').strip()}"
    elif "centos" in lower_name:
        return f"🎯 CentOS {clean_name.replace('centos', '').strip()}"
    elif "windows" in lower_name:
        return f"🪟 Windows {clean_name.replace('windows', '').strip()}"
    elif "prebuilt" in lower_name:
        return f"🚀 {clean_name}"

    return f"💿 {clean_name}"


def get_images_keyboard(images: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """
    Builds an inline keyboard representing available operating system images.
    - Excludes images starting with 'OLD_'.
    - Excludes inactive images.
    - Beautifies operating system names (removes '-amd64' etc.).
    """
    builder = InlineKeyboardBuilder()

    for img in images:
        name = img.get("Name", img.get("name", "OS Image"))
        img_id = img.get("ID", img.get("id", ""))
        status = img.get("Status", img.get("status", "active")).lower()

        # Check active status
        if status != "active":
            continue

        # Exclude legacy OLD_ prefix images
        if name.upper().startswith("OLD_"):
            continue

        # Beautify display OS names
        display_name = beautify_image_name(name)
        builder.button(text=display_name, callback_data=f"buy_img:{img_id}")

    builder.button(text="🔙 Back", callback_data="buy_back_flv")
    builder.button(text="❌ Cancel", callback_data="buy_cancel")
    builder.adjust(1)
    return builder.as_markup()


def get_confirm_purchase_keyboard() -> InlineKeyboardMarkup:
    """
    Creates final purchase confirmation inline buttons.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Confirm & Deploy", callback_data="buy_confirm_deploy")
    builder.button(text="❌ Cancel", callback_data="buy_cancel")
    builder.adjust(1)
    return builder.as_markup()


def get_server_control_keyboard(openstack_uuid: str) -> InlineKeyboardMarkup:
    """
    Builds localized inline control buttons for active server lifecycles (Start, Stop, Delete, Details).
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="🟢 Start", callback_data=f"vps_start:{openstack_uuid}")
    builder.button(text="🔴 Stop", callback_data=f"vps_stop:{openstack_uuid}")
    builder.button(text="🗑 Delete", callback_data=f"vps_delete:{openstack_uuid}")
    builder.button(text="🔄 Refresh", callback_data=f"vps_refresh:{openstack_uuid}")
    builder.adjust(2, 2)
    return builder.as_markup()
