import requests

DIKIDI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "X-Requested-With": "XMLHttpRequest",
}

def get_free_slots(company_id, service_id, day_month=""):
    url = "https://dikidi.net/ru/mobile/ajax/newrecord/get_datetimes/"
    params = {
        "company_id": company_id,
        "service_id[]": service_id,
        "with_first": "1",
        "day_month": day_month,
    }
    headers = dict(DIKIDI_HEADERS)
    headers["Referer"] = f"https://dikidi.net/{company_id}"
    r = requests.get(url, params=params, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()
    slots = []
    masters = data.get("masters") or {}
    for master_id, times in (data.get("times") or {}).items():
        master_name = masters.get(str(master_id), {}).get("username", str(master_id))
        for t in times:
            slots.append({"master_id": str(master_id), "master": master_name, "datetime": t})
    slots.sort(key=lambda s: s["datetime"])
    return slots
