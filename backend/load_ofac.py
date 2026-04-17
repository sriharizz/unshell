import os
import sqlite3
import urllib.request
from lxml import etree

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "sanctions.db")
XML_PATH = os.path.join(os.path.dirname(__file__), "data", "ofac_sdn.xml")
OFAC_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"


def download_xml():
    if not os.path.exists(XML_PATH):
        print("Downloading OFAC SDN XML...")
        urllib.request.urlretrieve(OFAC_URL, XML_PATH)
        print(f"Downloaded to {XML_PATH}")
    else:
        print(f"Using existing {XML_PATH}")


def build_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS sdn_list")
    cur.execute("""
        CREATE TABLE sdn_list (
            id      INTEGER PRIMARY KEY,
            name    TEXT NOT NULL,
            type    TEXT,
            program TEXT,
            aliases TEXT
        )
    """)

    tree = etree.parse(XML_PATH)
    root = tree.getroot()
    ns = {"o": root.nsmap.get(None, "")}
    tag = lambda t: f"{{{root.nsmap[None]}}}{t}" if None in root.nsmap else t

    entries = root.findall(f".//{tag('sdnEntry')}")
    count = 0
    batch = []

    for entry in entries:
        last = entry.findtext(f"{tag('lastName')}", default="")
        first = entry.findtext(f"{tag('firstName')}", default="")
        sdn_type = entry.findtext(f"{tag('sdnType')}", default="")
        programs = [p.text for p in entry.findall(f".//{tag('program')}") if p.text]
        akas = [
            " ".join(filter(None, [
                a.findtext(f"{tag('lastName')}", ""),
                a.findtext(f"{tag('firstName')}", ""),
            ]))
            for a in entry.findall(f".//{tag('aka')}")
        ]
        full_name = " ".join(filter(None, [first, last])).strip()

        batch.append((
            full_name,
            sdn_type,
            "; ".join(programs),
            "; ".join(akas),
        ))
        count += 1
        if count % 1000 == 0:
            print(f"  Processed {count} entries...")

    cur.executemany(
        "INSERT INTO sdn_list (name, type, program, aliases) VALUES (?,?,?,?)",
        batch,
    )
    conn.commit()
    conn.close()
    print(f"✅ Loaded {count} SDN entries to sanctions.db")


def seed_known_addresses():
    addr_db = os.path.join(os.path.dirname(__file__), "data", "known_addresses.db")
    conn = sqlite3.connect(addr_db)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS shell_addresses")
    cur.execute("""
        CREATE TABLE shell_addresses (
            id               INTEGER PRIMARY KEY,
            address_text     TEXT NOT NULL,
            confidence_score REAL,
            source           TEXT
        )
    """)
    addresses = [
        ("1 Victoria Street, London, SW1H 0ET", 0.9, "HMRC watch-list"),
        ("27 Old Gloucester Street, London, WC1N 3AX", 0.95, "Companies House filing anomaly"),
        ("71-75 Shelton Street, London, WC2H 9JQ", 0.9, "Covent Garden shell cluster"),
        ("12 Gough Square, London, EC4A 3DW", 0.85, "Multiple dormant companies"),
        ("20 St Dunstans Hill, London, EC3R 8HL", 0.8, "City of London nominee hub"),
        ("128 City Road, London, EC1V 2NX", 0.9, "High-volume incorporation address"),
        ("85 Great Portland Street, London, W1W 7LT", 0.75, "Known agent address"),
        ("167-169 Great Portland Street, London, W1W 5PF", 0.8, "Nominee director cluster"),
        ("Kemp House, 152-160 City Road, London, EC1V 2NX", 0.9, "Virtual office — high risk"),
        ("71 Baggot Street Lower, Dublin 2, Ireland", 0.7, "Cross-border shell hub"),
    ]
    cur.executemany(
        "INSERT INTO shell_addresses (address_text, confidence_score, source) VALUES (?,?,?)",
        addresses,
    )
    conn.commit()
    conn.close()
    print(f"✅ Seeded {len(addresses)} known shell addresses to known_addresses.db")


if __name__ == "__main__":
    download_xml()
    build_db()
    seed_known_addresses()
