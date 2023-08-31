from seleniumuser import User
import time
import json
from printbuddies import print_in_place
from pathlib import Path

root = Path(__file__).parent

url = "https://airtable.com/embed/shrI8dno1rMGKZM8y/tblKU0jQiyIX182uU?backgroundColor=cyan&viewControls=on"


def get_rows():
    soup = user.get_soup()
    left = soup.find_all(
        "div", class_="dataRow leftPane rowExpansionEnabled rowSelectionEnabled"
    )
    right = soup.find_all(
        "div", class_="dataRow rightPane rowExpansionEnabled rowSelectionEnabled"
    )
    rows = {}
    for l in left:
        id_ = l.get("data-rowid")
        name = l.find_all(
            "div",
            class_="line-height-4 overflow-hidden truncate-block-2-lines pre-wrap break-word",
        )[0].text
        link = l.find_all(
            "a",
            class_="link-quiet pointer flex-inline items-center justify-center z1 strong text-decoration-none rounded print-color-exact text-white purple border-box border-thick border-transparent border-darken2-focus px1",
        )[0].get("href")
        hiring_eng = (
            "Hiring Eng"
            in soup.find(
                "div",
                class_="dataRow rightPane rowExpansionEnabled rowSelectionEnabled",
                attrs={"data-rowid": id_},
            ).text
        )
        if hiring_eng:
            rows[name] = link
    return rows


stillhiring_path = root / "stillhiring.json"
with User(headless=False) as user:
    user.get(url)
    while True:
        foundrows = json.loads(stillhiring_path.read_text())
        try:
            newrows = get_rows()
        except Exception as e:
            newrows = {}
        foundrows |= newrows
        print_in_place(f"row count: {len(foundrows)}")
        stillhiring_path.write_text(json.dumps(foundrows, indent=2))
