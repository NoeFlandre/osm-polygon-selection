"""PBF metadata: dates and Geofabrik URLs.

Tiny helpers used by the build/publish pipeline to record provenance
on each country (when the source PBF was fetched, where it came from).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

# Default raw-PBF directory on the external HDD.
DEFAULT_RAW_DIR = Path("/Volumes/Seagate M3/osm-polygon-selection/raw")

# Countries outside the /europe/ Geofabrik tree. Add new regions
# here as we expand the project. The URL pattern is
# ``https://download.geofabrik.de/<region>/<country>.html``.
NON_EUROPE_COUNTRIES: dict[str, str] = {
    # North Africa
    "morocco": "africa",
    "tunisia": "africa",
    "algeria": "africa",
    "libya": "africa",
    "egypt": "africa",
    # West Africa
    "senegal-and-gambia": "africa",
    "guinea-bissau": "africa",
    "guinea": "africa",
    "sierra-leone": "africa",
    "liberia": "africa",
    "ivory-coast": "africa",
    "ghana": "africa",
    "togo": "africa",
    "benin": "africa",
    "burkina-faso": "africa",
    "mali": "africa",
    "mauritania": "africa",
    "niger": "africa",
    "nigeria": "africa",
    # Central Africa
    "cameroon": "africa",
    "central-african-republic": "africa",
    "chad": "africa",
    "congo-brazzaville": "africa",
    "congo-democratic-republic": "africa",
    "equatorial-guinea": "africa",
    "gabon": "africa",
    # East Africa
    "burundi": "africa",
    "comores": "africa",
    "djibouti": "africa",
    "eritrea": "africa",
    "ethiopia": "africa",
    "kenya": "africa",
    "rwanda": "africa",
    "seychelles": "africa",
    "somalia": "africa",
    "south-sudan": "africa",
    "sudan": "africa",
    "tanzania": "africa",
    "uganda": "africa",
    "mauritius": "africa",
    "madagascar": "africa",
    # Southern Africa
    "angola": "africa",
    "botswana": "africa",
    "lesotho": "africa",
    "malawi": "africa",
    "mozambique": "africa",
    "namibia": "africa",
    "south-africa": "africa",
    "swaziland": "africa",
    "zambia": "africa",
    "zimbabwe": "africa",
    # Island territories
    "canary-islands": "africa",
    "sao-tome-and-principe": "africa",
    "saint-helena-ascension-and-tristan-da-cunha": "africa",
    "mayotte": "africa",
    # South America
    "argentina": "south-america",
    "bolivia": "south-america",
    "brazil": "south-america",
    "brazil-norte": "south-america",
    "brazil-centro-oeste": "south-america",
    "brazil-nordeste": "south-america",
    "brazil-sudeste": "south-america",
    "brazil-sul": "south-america",
    "chile": "south-america",
    "colombia": "south-america",
    "ecuador": "south-america",
    "guyana": "south-america",
    "paraguay": "south-america",
    "peru": "south-america",
    "suriname": "south-america",
    "uruguay": "south-america",
    "venezuela": "south-america",
    # Asia
    "afghanistan": "asia",
    "armenia": "asia",
    "azerbaijan": "asia",
    "bangladesh": "asia",
    "bhutan": "asia",
    "cambodia": "asia",
    "east-timor": "asia",
    "gcc-states": "asia",
    "india": "asia",
    "indonesia": "asia",
    "iran": "asia",
    "iraq": "asia",
    "israel-and-palestine": "asia",
    "japan": "asia",
    "jordan": "asia",
    "kazakhstan": "asia",
    "kyrgyzstan": "asia",
    "laos": "asia",
    "lebanon": "asia",
    "malaysia-singapore-brunei": "asia",
    "maldives": "asia",
    "mongolia": "asia",
    "myanmar": "asia",
    "nepal": "asia",
    "north-korea": "asia",
    "pakistan": "asia",
    "philippines": "asia",
    "south-korea": "asia",
    "sri-lanka": "asia",
    "syria": "asia",
    "taiwan": "asia",
    "tajikistan": "asia",
    "thailand": "asia",
    "turkmenistan": "asia",
    "uzbekistan": "asia",
    "vietnam": "asia",
    "yemen": "asia",
    # China (processed by province/territory to keep PBFs < 200 MB)
    "china-anhui": "asia",
    "china-beijing": "asia",
    "china-chongqing": "asia",
    "china-fujian": "asia",
    "china-gansu": "asia",
    "china-guangdong": "asia",
    "china-guangxi": "asia",
    "china-guizhou": "asia",
    "china-hainan": "asia",
    "china-hebei": "asia",
    "china-heilongjiang": "asia",
    "china-henan": "asia",
    "china-hong-kong": "asia",
    "china-hubei": "asia",
    "china-hunan": "asia",
    "china-inner-mongolia": "asia",
    "china-jiangsu": "asia",
    "china-jiangxi": "asia",
    "china-jilin": "asia",
    "china-liaoning": "asia",
    "china-macau": "asia",
    "china-ningxia": "asia",
    "china-qinghai": "asia",
    "china-shaanxi": "asia",
    "china-shandong": "asia",
    "china-shanghai": "asia",
    "china-shanxi": "asia",
    "china-sichuan": "asia",
    "china-tianjin": "asia",
    "china-tibet": "asia",
    "china-xinjiang": "asia",
    "china-yunnan": "asia",
    "china-zhejiang": "asia",
    # India (processed by zone)
    "india-central-zone": "asia",
    "india-eastern-zone": "asia",
    "india-north-eastern-zone": "asia",
    "india-northern-zone": "asia",
    "india-southern-zone": "asia",
    "india-western-zone": "asia",
    # Indonesia (processed by island group)
    "indonesia-java": "asia",
    "indonesia-kalimantan": "asia",
    "indonesia-maluku": "asia",
    "indonesia-nusa-tenggara": "asia",
    "indonesia-papua": "asia",
    "indonesia-sulawesi": "asia",
    "indonesia-sumatra": "asia",
    # Japan (processed by region)
    "japan-chubu": "asia",
    "japan-chugoku": "asia",
    "japan-hokkaido": "asia",
    "japan-kansai": "asia",
    "japan-kanto": "asia",
    "japan-kyushu": "asia",
    "japan-shikoku": "asia",
    "japan-tohoku": "asia",
    # Oceania / Australia
    "american-oceania": "australia-oceania",
    "cook-islands": "australia-oceania",
    "fiji": "australia-oceania",
    "ile-de-clipperton": "australia-oceania",
    "kiribati": "australia-oceania",
    "marshall-islands": "australia-oceania",
    "micronesia": "australia-oceania",
    "nauru": "australia-oceania",
    "new-caledonia": "australia-oceania",
    "new-zealand": "australia-oceania",
    "niue": "australia-oceania",
    "palau": "australia-oceania",
    "papua-new-guinea": "australia-oceania",
    "pitcairn-islands": "australia-oceania",
    "polynesie-francaise": "australia-oceania",
    "samoa": "australia-oceania",
    "solomon-islands": "australia-oceania",
    "tokelau": "australia-oceania",
    "tonga": "australia-oceania",
    "tuvalu": "australia-oceania",
    "vanuatu": "australia-oceania",
    "wallis-et-futuna": "australia-oceania",
    "australia": "australia-oceania",
    # North America
    "greenland": "north-america",
    "mexico": "north-america",
    # US states (under /north-america/us/<state>/)
    "us-alabama": "north-america",
    "us-alaska": "north-america",
    "us-arizona": "north-america",
    "us-arkansas": "north-america",
    "us-california": "north-america",
    "us-colorado": "north-america",
    "us-connecticut": "north-america",
    "us-delaware": "north-america",
    "us-district-of-columbia": "north-america",
    "us-florida": "north-america",
    "us-georgia": "north-america",
    "us-hawaii": "north-america",
    "us-idaho": "north-america",
    "us-illinois": "north-america",
    "us-indiana": "north-america",
    "us-iowa": "north-america",
    "us-kansas": "north-america",
    "us-kentucky": "north-america",
    "us-louisiana": "north-america",
    "us-maine": "north-america",
    "us-maryland": "north-america",
    "us-massachusetts": "north-america",
    "us-michigan": "north-america",
    "us-minnesota": "north-america",
    "us-mississippi": "north-america",
    "us-missouri": "north-america",
    "us-montana": "north-america",
    "us-nebraska": "north-america",
    "us-nevada": "north-america",
    "us-new-hampshire": "north-america",
    "us-new-jersey": "north-america",
    "us-new-mexico": "north-america",
    "us-new-york": "north-america",
    "us-north-carolina": "north-america",
    "us-north-dakota": "north-america",
    "us-ohio": "north-america",
    "us-oklahoma": "north-america",
    "us-oregon": "north-america",
    "us-pennsylvania": "north-america",
    "us-rhode-island": "north-america",
    "us-south-carolina": "north-america",
    "us-south-dakota": "north-america",
    "us-tennessee": "north-america",
    "us-texas": "north-america",
    "us-utah": "north-america",
    "us-vermont": "north-america",
    "us-virginia": "north-america",
    "us-washington": "north-america",
    "us-west-virginia": "north-america",
    "us-wisconsin": "north-america",
    "us-wyoming": "north-america",
    # Canada provinces (under /north-america/canada/<province>/)
    "canada-alberta": "north-america",
    "canada-british-columbia": "north-america",
    "canada-manitoba": "north-america",
    "canada-new-brunswick": "north-america",
    "canada-newfoundland-and-labrador": "north-america",
    "canada-northwest-territories": "north-america",
    "canada-nova-scotia": "north-america",
    "canada-nunavut": "north-america",
    "canada-ontario": "north-america",
    "canada-prince-edward-island": "north-america",
    "canada-quebec": "north-america",
    "canada-saskatchewan": "north-america",
    "canada-yukon": "north-america",
    # Russia federal districts (under /russia/<district>/)
    "russia-central-fed-district": "russia",
    "russia-crimean-fed-district": "russia",
    "russia-far-eastern-fed-district": "russia",
    "russia-kaliningrad": "russia",
    "russia-north-caucasus-fed-district": "russia",
    "russia-northwestern-fed-district": "russia",
    "russia-siberian-fed-district": "russia",
    "russia-south-fed-district": "russia",
    "russia-ural-fed-district": "russia",
    "russia-volga-fed-district": "russia",
}


# Geofabrik's own US sub-regions (midwest / northeast / pacific /
# south / west) live as flat /north-america/us-<region>-latest.osm.pbf
# files, NOT under /us/<state>/. We must not treat these as state
# slugs and accidentally nest them.
_US_GEOFABRIK_REGIONS = {"midwest", "northeast", "pacific", "south", "west"}


def geofabrik_url(country: str) -> str:
    """Return the Geofabrik overview URL for a country.

    Geofabrik organizes extracts into continent-scale subtrees
    (e.g. ``/europe/``, ``/africa/``). Most of our countries
    live under ``/europe/``; the few exceptions are listed in
    ``NON_EUROPE_COUNTRIES``.

    Some large countries (brazil, china, india, indonesia, japan,
    us) are split into sub-regions to keep each PBF manageable.
    The slug convention is ``<country>-<region>`` and the URL
    pattern is ``/asia/<country>/<region>``,
    ``/south-america/<country>/<region>``, or
    ``/north-america/us/<state>`` (US states nest under ``us/``).
    """
    # Sub-region slugs (country-region) get a nested path.
    sub_region_parents = {"brazil", "china", "india", "indonesia", "japan", "canada"}
    for parent in sub_region_parents:
        if country.startswith(f"{parent}-"):
            region = country[len(parent) + 1:]
            continent = NON_EUROPE_COUNTRIES.get(country, "asia")
            return (
                f"https://download.geofabrik.de/{continent}/"
                f"{parent}/{region}.html"
            )
    # Russia IS its own top-level folder on Geofabrik
    # (https://download.geofabrik.de/russia/), so sub-PBFs nest
    # directly under /russia/, not /russia/russia/.
    if country.startswith("russia-"):
        region = country[len("russia-"):]
        return f"https://download.geofabrik.de/russia/{region}.html"
    if country.startswith("us-"):
        # US states live under /north-america/us/<state>/, but
        # Geofabrik's own US sub-regions (us-midwest etc.) are
        # flat at /north-america/us-<region>.osm.pbf.
        rest = country[len("us-"):]
        if rest in _US_GEOFABRIK_REGIONS:
            continent = NON_EUROPE_COUNTRIES.get(country, "north-america")
            return (
                f"https://download.geofabrik.de/{continent}/{country}.html"
            )
        continent = NON_EUROPE_COUNTRIES.get(country, "north-america")
        return f"https://download.geofabrik.de/{continent}/us/{rest}.html"
    region = NON_EUROPE_COUNTRIES.get(country, "europe")
    return f"https://download.geofabrik.de/{region}/{country}.html"


def format_pbf_date(raw: str) -> str:
    """Normalize a PBF date string to YYYY-MM-DD or 'unknown'.

    Pass-through for already-formatted ISO dates; defensive for
    empty/unknown strings.
    """
    if not raw or raw == "unknown":
        return "unknown"
    return raw


def pbf_date_for(country: str, raw_dir: Path = DEFAULT_RAW_DIR) -> str:
    """Return the mtime of ``<country>-latest.osm.pbf`` as YYYY-MM-DD.

    Returns "unknown" if the PBF doesn't exist at the conventional
    location.
    """
    pbf = raw_dir / f"{country}-latest.osm.pbf"
    if not pbf.is_file():
        return "unknown"
    mtime = pbf.stat().st_mtime
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
