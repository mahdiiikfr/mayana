from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any


def get_networks_keyboard(networks: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """
    Builds an inline keyboard representing available network locations.
    Filters out networks with 'RESERVE' or 'NOTWORKING' in their names, and sorts alphabetically.
    """
    builder = InlineKeyboardBuilder()

    filtered_networks = []
    for net in networks:
        name = net.get("Name", net.get("name", "Unknown Network"))
        net_id = net.get("ID", net.get("id", ""))

        # Check for reservation or non-functional keywords
        upper_name = name.upper()
        if "RESERVE" in upper_name or "NOTWORKING" in upper_name:
            continue
        filtered_networks.append((name, net_id))

    # Sort alphabetically by network name
    filtered_networks.sort(key=lambda x: x[0].lower())

    for name, net_id in filtered_networks:
        builder.button(text=f"🌐 {name}", callback_data=f"buy_net:{net_id}")

    builder.button(text="❌ Cancel", callback_data="buy_cancel")
    builder.adjust(1)
    return builder.as_markup()


def get_flavors_keyboard(flavors: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """
    Builds an inline keyboard representing available virtual server plans/flavors.
    """
    builder = InlineKeyboardBuilder()
    # Sort flavors by memory/vcpus for organized presentation
    for flv in flavors[:10]:  # limit display count for tidy Telegram rendering
        name = flv.get("Name", flv.get("name", "Flavor"))
        flv_id = flv.get("ID", flv.get("id", ""))
        ram = flv.get("RAM", "")
        vcpus = flv.get("VCPUs", "")
        disk = flv.get("Disk", "")

        btn_text = f"⚙️ {name} ({ram}MB RAM, {vcpus} vCPU, {disk}G Disk)"
        builder.button(text=btn_text, callback_data=f"buy_flv:{flv_id}")

    builder.button(text="🔙 Back", callback_data="buy_back_net")
    builder.button(text="❌ Cancel", callback_data="buy_cancel")
    builder.adjust(1)
    return builder.as_markup()


def get_images_keyboard(images: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """
    Builds an inline keyboard representing available operating system images.
    """
    builder = InlineKeyboardBuilder()
    for img in images:
        name = img.get("Name", img.get("name", "OS Image"))
        img_id = img.get("ID", img.get("id", ""))
        # Only show active images for cleaner UX
        status = img.get("Status", img.get("status", "active")).lower()
        if status == "active":
            builder.button(text=f"💿 {name}", callback_data=f"buy_img:{img_id}")

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
