import json
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

def get_bnr_eur_ron():
    try:
        r = requests.get("https://www.bnr.ro/nbrfxrates.xml", timeout=15)
        root = ET.fromstring(r.content)
        for rate in root.iter("{http://www.bnr.ro/xsd}Rate"):
            if rate.attrib.get("currency") == "EUR":
                return float(rate.text)
    except Exception:
        pass
    return 4.9770

def fetch_opcom_day(target_date):
    # Citește direct pagina publică de rezultate PZU de pe opcom.ro (fără cont/token)
    url = "https://www.opcom.ro/grafice-ip-raportPIP-si-volumTranzactionat/ro"
    payload = {
        "day": target_date.day,
        "month": target_date.month,
        "year": target_date.year,
        "buton": "Refresh"
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.post(url, data=payload, headers=headers, timeout=20)
    
    # Extrage valorile ROPEX_DAM (EUR/MWh) din tabelul HTML
    # Dacă OPCOM afișează pe 15 min (96 valori) le păstrează; dacă e orar (24 valori) le multiplică la 4 sferturi
    matches = re.findall(r'ROPEX_DAM[^<]*</td>\s*<td[^>]*>\s*([\d.,-]+)', r.text)
    if not matches:
        # Fallback pe celulele tabelului de prețuri de închidere
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', r.text, re.S)
        vals = []
        for row in rows:
            cols = re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)
            clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cols]
            if len(clean) >= 3 and re.match(r'^\d{1,2}$', clean[0]):
                try:
                    # Prețul în EUR/MWh este de obicei pe coloana 2 sau 3
                    num = float(clean[2].replace(',', '.'))
                    vals.append(num)
                except ValueError:
                    pass
        matches = vals

    prices = [float(str(x).replace(',', '.')) for x in matches]
    if len(prices) == 24:
        prices = [p for p in prices for _ in range(4)]
    return prices[:96]

def main():
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    eur_ron = get_bnr_eur_ron()

    today_prices = fetch_opcom_day(today)
    tomorrow_prices = fetch_opcom_day(tomorrow)

    data = {
        "updated_at": today.strftime("%Y-%m-%d %H:%M"),
        "eur_ron": eur_ron,
        "today": {
            "date": today.strftime("%Y-%m-%d"),
            "eur_mwh": today_prices
        },
        "tomorrow": {
            "date": tomorrow.strftime("%Y-%m-%d"),
            "eur_mwh": tomorrow_prices
        }
    }

    with open("prices.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    main()
