"""
Aahar-Rx Medicine Box Service
Tracks tablet stock, expiry date, triggers 3-days-before-run-out alerts,
and generates deep-links for reordering (1mg / PharmEasy).
"""

import uuid
import urllib.parse
from datetime import datetime, date
from typing import Dict, Any, Optional

class MedicineBoxService:
    _inventory: Dict[str, dict] = {}

    @classmethod
    def add_medicine(
        cls,
        brand: str,
        salt: str,
        expiry_date_str: str,
        initial_count: int,
        remaining_count: Optional[int] = None,
        daily_dosage_count: int = 1
    ) -> Dict[str, Any]:
        item_id = f"BOX-{uuid.uuid4().hex[:8].upper()}"
        remaining = initial_count if remaining_count is None else remaining_count
        
        item = {
            "item_id": item_id,
            "brand": brand,
            "salt": salt,
            "expiry_date": expiry_date_str,
            "initial_count": initial_count,
            "remaining_count": remaining,
            "daily_dosage_count": max(1, daily_dosage_count),
        }
        cls._inventory[item_id] = item
        return cls._format_item_response(item)

    @classmethod
    def consume_dose(cls, item_id: str, doses: int = 1) -> Optional[Dict[str, Any]]:
        item = cls._inventory.get(item_id)
        if not item:
            return None
        
        item["remaining_count"] = max(0, item["remaining_count"] - doses)
        return cls._format_item_response(item)

    @classmethod
    def get_item(cls, item_id: str) -> Optional[Dict[str, Any]]:
        item = cls._inventory.get(item_id)
        if not item:
            return None
        return cls._format_item_response(item)

    @classmethod
    def _format_item_response(cls, item: dict) -> Dict[str, Any]:
        remaining = item["remaining_count"]
        daily_dosage = item["daily_dosage_count"]
        days_left = remaining // daily_dosage

        # 3-days-before-run-out alert
        low_stock = days_left <= 3
        alert_msg = None
        reorder_url = None

        encoded_brand = urllib.parse.quote(item["brand"])
        # Deep-link to 1mg search for convenient reordering
        reorder_url = f"https://www.1mg.com/search/all?name={encoded_brand}"

        if low_stock:
            alert_msg = (
                f"🚨 LOW STOCK ALERT: Only {remaining} tablet(s) ({days_left} day(s) supply) remaining "
                f"for '{item['brand']}'. Reorder now to avoid missed doses."
            )

        # Check expiry
        is_expired = False
        try:
            exp_date = datetime.strptime(item["expiry_date"], "%Y-%m-%d").date()
            if date.today() >= exp_date:
                is_expired = True
                alert_msg = f"⚠️ EXPIRED MEDICATION: '{item['brand']}' expired on {item['expiry_date']}. Do not consume."
        except Exception:
            pass

        return {
            "item_id": item["item_id"],
            "brand": item["brand"],
            "salt": item["salt"],
            "expiry_date": item["expiry_date"],
            "initial_count": item["initial_count"],
            "remaining_count": remaining,
            "daily_dosage_count": daily_dosage,
            "days_of_stock_left": days_left,
            "low_stock_alert": low_stock,
            "alert_message": alert_msg,
            "reorder_url": reorder_url,
            "is_expired": is_expired
        }

medicine_box_service = MedicineBoxService()
