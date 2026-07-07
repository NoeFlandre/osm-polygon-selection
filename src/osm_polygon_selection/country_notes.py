"""Curated country notes + regional sub-PBF lists.

Sourced from Geofabrik per-country pages. Used by
organize_dataset.py to render the per-country READMEs.
"""

from __future__ import annotations

REGIONAL_SUB_PBFS: dict[str, list[str]] = {
    "france": [
        "alsace", "aquitaine", "auvergne", "basse-normandie", "bourgogne",
        "bretagne", "centre", "champagne-ardenne", "corse", "franche-comte",
        "ile-de-france", "languedoc-roussillon", "limousin", "lorraine",
        "midi-pyrenees", "nord-pas-de-calais", "pays-de-la-loire",
        "picardie", "poitou-charentes", "provence-alpes-cote-d-azur",
        "rhone-alpes",
        # plus overseas: guadeloupe, guyane, martinique, mayotte, reunion
        "guadeloupe", "guyane", "martinique", "mayotte", "reunion",
    ],
    "germany": [
        "baden-wuerttemberg", "bayern", "berlin", "brandenburg", "bremen",
        "hamburg", "hessen", "mecklenburg-vorpommern", "niedersachsen",
        "nordrhein-westfalen", "rheinland-pfalz", "saarland", "sachsen",
        "sachsen-anhalt", "schleswig-holstein", "thueringen",
    ],
    "italy": ["centro", "isole", "nord-est", "nord-ovest", "sud"],
    "netherlands": [
        "drenthe", "flevoland", "friesland", "gelderland", "groningen",
        "limburg", "noord-brabant", "noord-holland", "overijssel",
        "utrecht", "zeeland", "zuid-holland",
    ],
    "norway": [
        "nord-norge", "ostlandet", "sorlandet", "svalbard-janmayen",
        "trondelag", "vestlandet",
    ],
    "poland": [
        "dolnoslaskie", "kujawsko-pomorskie", "lodzkie", "lubelskie",
        "lubuskie", "malopolskie", "mazowieckie", "opolskie",
        "podkarpackie", "podlaskie", "pomorskie", "slaskie",
        "swietokrzyskie", "warminsko-mazurskie", "wielkopolskie",
        "zachodniopomorskie",
    ],
    "spain": [
        "andalucia", "aragon", "asturias", "cantabria",
        "castilla-la-mancha", "castilla-y-leon", "cataluna", "ceuta",
        "extremadura", "galicia", "islas-baleares", "la-rioja",
        "madrid", "melilla", "murcia", "navarra", "pais-vasco",
        "valencia",
    ],
    "united-kingdom": ["england", "scotland", "wales"],
}

COUNTRY_NOTES: dict[str, str] = {
    "georgia": "Caucasus country with the Greater and Lesser Caucasus "
               "mountain ranges forming the northern border. OSM coverage "
               "is good in Tbilisi and along the Black Sea coast. "
               "Source: Geofabrik Europe/Georgia extract (note: Geofabrik "
               "still files it under 'europe/' despite being in Asia — "
               "we keep that placement for consistency with the dataset).",
    "ireland-and-northern-ireland": "Combined extract covering the "
               "Republic of Ireland and Northern Ireland (UK). The "
               "Geofabrik page offers this as a single PBF rather than "
               "two separate ones. OSM coverage is strong in Dublin, "
               "Belfast, and the major road network.",
    "macedonia": "Landlocked Balkan country, renamed in 2019 to "
               "'North Macedonia' but Geofabrik still publishes the "
               "PBF under the legacy 'macedonia' name. Coverage is "
               "good around Skopje and the major valleys; the "
               "mountainous west is sparser.",
    "albania": "Albania's OSM coverage has grown sharply since 2017; "
               "Tirana and the coastal strip are well-mapped. "
               "Source: Geofabrik Europe/Albania extract.",
    "andorra": "Tiny principality in the Pyrenees. The whole country "
               "fits in a single tile, so even the small extract yields "
               "good coverage of hiking trails, landuse, and buildings.",
    "austria": "Strong community mapping across all nine Bundesländer. "
               "Excellent coverage of landuse (agriculture, forest) "
               "and alpine hiking infrastructure.",
    "azores": "Portuguese archipelago in the Atlantic. Polygons cover "
              "the nine inhabited islands; remote islets are mostly "
              "absent from OSM.",
    "belarus": "Mapping is active but uneven. Minsk and regional capitals "
               "have dense coverage; rural landuse is patchier.",
    "belgium": "Dense, high-quality mapping across Flanders, Wallonia, "
               "and Brussels. Excellent for benchmarking against "
               "official cadastral data.",
    "bosnia-herzegovina": "Coverage is solid in urban areas and along "
                          "the main road network; mountain terrain "
                          "(Dinaric Alps) is sparser.",
    "bulgaria": "Sofia, Plovdiv, and the Black Sea coast have dense "
                "landuse and building footprints; mountain areas "
                "(Rila, Pirin, Rhodopes) are better-mapped for hiking.",
    "croatia": "Coast and islands are well-mapped for tourism; the "
               "interior (Slavonia) has solid agricultural landuse.",
    "cyprus": "The divided island. OSM coverage is strong in the "
              "Republic of Cyprus; the north is mapped but partially "
              "via imports.",
    "czech-republic": "One of the best-mapped countries in central "
                      "Europe. Excellent address, landuse, and "
                      "building data.",
    "denmark": "Among the world's best-mapped countries. Comprehensive "
               "address data, full landuse, and very fresh updates.",
    "estonia": "Strong nationwide mapping, including detailed landuse "
               "and forestry. Tallinn has excellent building footprints.",
    "faroe-islands": "Small, well-mapped archipelago. The 18 main "
                     "islands are all covered.",
    "finland": "Excellent nationwide mapping. Strong coverage of "
               "forests, lakes, and the very long coastline.",
    "france": "Processed via 26 Geofabrik regional sub-PBFs "
              "(régions + overseas). The country PBF was removed in "
              "favor of the regional breakdown because the parent "
              "extract was too large to process in one pass.",
    "germany": "Processed via 16 Geofabrik regional sub-PBFs "
               "(Bundesländer). Highest polygon count of any country "
               "in the dataset, reflecting the very active German "
               "OSM community.",
    "greece": "Athens and Thessaloniki have excellent urban coverage. "
              "The islands and mainland mountain areas are well-mapped "
              "for hiking.",
    "guernsey-jersey": "Channel Islands. Two crown dependencies mapped "
                       "as a single extract.",
    "hungary": "Budapest has dense urban mapping; the Great Plain "
               "(Alföld) has good agricultural landuse.",
    "iceland": "Sparse but comprehensive: roads, landuse, and the "
               "small settled areas are all well-mapped. The highlands "
               "are intentionally not in OSM (no trails).",
    "isle-of-man": "British Crown dependency. Small island, good coverage.",
    "italy": "Processed via 5 Geofabrik regional sub-PBFs (centro, "
             "isole, nord-est, nord-ovest, sud). Strong urban mapping "
             "across all regions.",
    "kosovo": "Recognized by many OSM contributors as a separate "
              "territory. Polygons reflect the boundary used by "
              "Geofabrik.",
    "latvia": "Solid nationwide coverage; Riga has detailed urban data.",
    "liechtenstein": "One of the smallest dataset countries — fewer "
                     "than 600 polygons but well-mapped for hiking "
                     "and landuse.",
    "lithuania": "Good nationwide coverage. Vilnius has detailed "
                 "urban data; forestry is well-mapped.",
    "luxembourg": "Small but very densely mapped. Full landuse and "
                  "building footprints nationwide.",
    "malta": "Tiny archipelago, fully covered. Buildings and roads "
             "are exhaustively mapped.",
    "moldova": "Capital Chișinău is well-mapped; rural landuse is "
               "patchier.",
    "monaco": "The smallest country in the dataset by polygon count. "
              "Only 2 polygons survive the [0.1, 100] km² area filter "
              "— Monaco's land area is 2.02 km², so most of the country "
              "fits in one large polygon.",
    "montenegro": "Coast and Bay of Kotor are well-mapped; the "
                  "Dinaric interior has good hiking infrastructure.",
    "morocco": "First non-European country in the dataset. Source "
               "PBF is from Geofabrik's /africa/ subtree. Strong "
               "urban mapping in coastal cities (Casablanca, Rabat, "
               "Marrakech); rural and Saharan regions are sparser.",
    "tunisia": "Second North-African country in the dataset "
               "(Geofabrik /africa/). Smallest PBF of the African "
               "pair. Strong urban mapping along the Mediterranean "
               "coast (Tunis, Sfax, Sousse); interior and Saharan "
               "fringe have thinner coverage.",
    "algeria": "Largest North-African country by land area; "
               "Geofabrik /africa/ PBF (~280 MB). Largest African "
               "PBF in the dataset by file size. Strong urban mapping "
               "in coastal cities (Algiers, Oran, Constantine); the "
               "vast Saharan interior is sparsely mapped with mostly "
               "natural feature polygons (ergs, regs, wadis).",
    # Tiny island nations / territories (Geofabrik /africa/)
    "sao-tome-and-principe": "Small archipelago in the Gulf of "
                              "Guinea. Geofabrik /africa/ PBF (~1.2 MB). "
                              "One of the smallest countries in the "
                              "dataset.",
    "comores": "Volcanic archipelago in the Mozambique Channel. "
               "Geofabrik /africa/ PBF (~4 MB).",
    "seychelles": "Indian-ocean archipelago of 115+ islands. "
                  "Geofabrik /africa/ PBF (~2.6 MB).",
    "saint-helena-ascension-and-tristan-da-cunha": "British Overseas "
                                                    "Territory in the "
                                                    "South Atlantic. "
                                                    "Geofabrik /africa/ "
                                                    "PBF (~850 KB); "
                                                    "smallest country "
                                                    "in the dataset.",
    "equatorial-guinea": "Central African country spanning islands "
                         "and mainland. Geofabrik /africa/ PBF "
                         "(~6 MB).",
    "djibouti": "Horn-of-Africa country on the Red Sea. Geofabrik "
                "/africa/ PBF (~7 MB).",
    "mauritius": "Indian-ocean island nation east of Madagascar. "
                 "Geofabrik /africa/ PBF (~9 MB).",
    "guinea-bissau": "Small West-African country on the Atlantic. "
                     "Geofabrik /africa/ PBF (~11 MB).",
    "cape-verde": "Atlantic archipelago off West Africa. Geofabrik "
                  "/africa/ PBF (~11 MB).",
    "canary-islands": "Spanish archipelago off the coast of Morocco; "
                      "classified under Geofabrik /africa/. PBF "
                      "(~57 MB).",
    "mayotte": "French overseas department in the Indian Ocean "
               "(Comoros archipelago). Geofabrik /africa/ PBF "
               "(~10 MB).",
    "gabon": "Central African country on the equator; mostly "
             "rainforest. Geofabrik /africa/ PBF (~24 MB).",
    "congo-brazzaville": "Republic of the Congo (Brazzaville). "
                         "Geofabrik /africa/ PBF (~31 MB).",
    "burundi": "Small landlocked country in the African Great Lakes "
               "region. Geofabrik /africa/ PBF (~44 MB).",
    "sierra-leone": "West African country on the Atlantic coast. "
                    "Geofabrik /africa/ PBF (~41 MB).",
    "benin": "West African country (former Dahomey). Geofabrik "
             "/africa/ PBF (~46 MB).",
    "liberia": "West African country founded by freed US slaves. "
               "Geofabrik /africa/ PBF (~36 MB).",
    "namibia": "Southern African country with the Namib desert "
               "stretching along the Atlantic coast. Geofabrik "
               "/africa/ PBF (~52 MB).",
    "rwanda": "Landlocked East African country. Geofabrik /africa/ "
              "PBF (~63 MB).",
    "togo": "Narrow West African country stretching north from the "
            "Gulf of Guinea. Geofabrik /africa/ PBF (~59 MB).",
    "libya": "North African country with mostly desert terrain "
             "(Sahara). Geofabrik /africa/ PBF (~73 MB). Sparse "
             "polygon coverage outside Tripoli and Benghazi.",
    "niger": "Landlocked West African country; mostly Sahara and "
             "Sahel. Geofabrik /africa/ PBF (~72 MB).",
    "swaziland": "Small landlocked Southern African country "
                 "(officially Eswatini). Geofabrik /africa/ PBF "
                 "(~29 MB).",
    "eritrea": "Horn-of-Africa country on the Red Sea. Geofabrik "
               "/africa/ PBF (~30 MB).",
    "mauritania": "North-West African country; mostly Sahara. "
                  "Geofabrik /africa/ PBF (~29 MB).",
    "botswana": "Landlocked Southern African country dominated by "
                "the Kalahari Desert, with the Okavango Delta (a "
                "UNESCO World Heritage site) in the northwest and "
                "the Chobe/Linyanti wetlands in the north. "
                "Geofabrik /africa/ PBF (~84 MB). OSM coverage is "
                "strongest around Gaborone and the protected-area "
                "boundaries; the central and southwestern Kalahari "
                "have sparser polygon coverage.",
    "central-african-republic": "Landlocked Central African country "
                "straddling the savanna and equatorial forest belts, "
                "with the Ubangi River forming much of its southern "
                "border with the Democratic Republic of Congo. "
                "Geofabrik /africa/ PBF (~94 MB). Capital Bangui is "
                "the only large urban mapping centre; the rest of "
                "the country has patchy OSM coverage that improved "
                "after the 2013 HOT Mapping Initiative.",
    "ivory-coast": "West African country on the Gulf of Guinea "
                "(official name Côte d'Ivoire) with the political "
                "capital Yamoussoukro and the economic capital "
                "Abidjan. The southern coastal belt has excellent "
                "OSM coverage around Abidjan's districts and the "
                "Banco National Park; the northern savanna is more "
                "sparsely mapped. Geofabrik /africa/ PBF (~85 MB). "
                "Notable features include the Comoé National Park "
                "(a UNESCO World Heritage site) and the Taï "
                "National Park in the southwest.",
    "burkina-faso": "Landlocked West African country (formerly "
                "Upper Volta) crossed by three tributaries of the "
                "Volta River and transitioning from the "
                "Sudano-Sahelian savanna in the south to the Sahel "
                "in the north. Capital Ouagadougou and second city "
                "Bobo-Dioulasso have good OSM coverage; the "
                "northern Sahel is sparsely mapped. Geofabrik "
                "/africa/ PBF (~81 MB). Notable protected areas "
                "include the Arly and W National Parks (the latter "
                "a transboundary UNESCO site shared with Niger and "
                "Benin).",
    "angola": "Large Southern African country on the Atlantic "
                "coast, former Portuguese colony, with a long "
                "coastline from the Congo River mouth in the north "
                "to the Namib Desert in the south. Capital Luanda "
                "has good OSM coverage; the interior is sparsely "
                "mapped. Geofabrik /africa/ PBF (~81 MB). Notable "
                "protected areas include Iona National Park (in "
                "the Namib fringe), Kissama (Quiçama) National "
                "Park near Luanda, and the Calandula / Kalandula "
                "waterfalls.",
    "guinea": "West African country on the Atlantic (former "
                "French colony) with the Fouta Djallon highlands "
                "forming the headwaters of the Niger, Gambia, and "
                "Senegal Rivers. Capital Conakry and the Fouta "
                "Djallon region have good OSM coverage; the "
                "forested southeast (the Guinea Highlands / Nimba "
                "mountains) is sparsely mapped. Geofabrik /africa/ "
                "PBF (~111 MB). Notable protected areas include "
                "the Mount Nimba Strict Nature Reserve (a "
                "transboundary UNESCO site shared with Liberia "
                "and Côte d'Ivoire).",
    "ghana": "West African country on the Gulf of Guinea (former "
                "British colony) with the political capital Accra "
                "on the Atlantic coast and the second city Kumasi "
                "in the central Ashanti region. The Volta Basin "
                "(Lake Volta / Volta River) dominates the eastern "
                "half of the country. OSM coverage is excellent "
                "around Accra, Kumasi, and the cocoa belt; the "
                "northern savanna is sparser. Geofabrik /africa/ "
                "PBF (~107 MB). Notable protected areas include "
                "Kakum National Park (the canopy walkway) and "
                "Mole National Park in the north.",
    "senegal-and-gambia": "Geofabrik combined file covering "
                "Senegal (West African country on the Atlantic, "
                "former French colony, capital Dakar) plus The "
                "Gambia (a narrow enclave inside Senegal along "
                "the Gambia River, capital Banjul). Dakar has "
                "excellent OSM coverage; the Sine-Saloum Delta "
                "and the Niokolo-Koba National Park (a UNESCO "
                "World Heritage site in eastern Senegal) are "
                "well-mapped. The Gambia's riverbanks are "
                "similarly well-traced. Geofabrik /africa/ "
                "combined PBF (~100 MB).",
    "lesotho": "Small landlocked Southern African country, "
                "entirely surrounded by South Africa and known "
                "as the 'Kingdom in the Sky' for its high-"
                "altitude terrain. The Drakensberg and Maluti "
                "mountains cover most of the country, with the "
                "lowest point still above 1,000 m. Capital "
                "Maseru has reasonable OSM coverage; the "
                "highlands are sparser. Geofabrik /africa/ PBF "
                "(~120 MB). Notable protected areas include "
                "Sehlabathebe National Park (a UNESCO World "
                "Heritage site) and the Maloti-Drakensberg "
                "Transfrontier Park (shared with South Africa).",
    "chad": "Large landlocked Central African country (formerly "
                "French Equatorial Africa), with three climatic "
                "zones stretching from the Saharan north "
                "(Tibesti Mountains) through the Sahelian belt "
                "to the Sudano-Guinean south. Capital N'Djamena "
                "(on the border with Cameroon) has decent OSM "
                "coverage; the northern Sahara and the eastern "
                "Ennedi Plateau are extremely sparsely mapped. "
                "Geofabrik /africa/ PBF (~128 MB). The shrinking "
                "of Lake Chad (a UNESCO Biosphere Reserve) is "
                "the country's most prominent geographic feature.",
    "south-sudan": "East African landlocked country, gained "
                "independence from Sudan in 2011 and home to "
                "the vast Sudd wetland (one of the world's "
                "largest tropical wetlands). Capital Juba is "
                "the only large urban mapping centre; the rest "
                "of the country is extremely sparsely mapped due "
                "to ongoing conflict and limited road access. "
                "Geofabrik /africa/ PBF (~131 MB). The White "
                "Nile traverses the country south to north "
                "through the Sudd.",
    "ethiopia": "Large East African country (formerly Abyssinia, "
                "never colonized) dominated by the Ethiopian "
                "Highlands, a massive plateau rising above "
                "1,500 m. Capital Addis Ababa has good OSM "
                "coverage; the highlands and the Rift Valley "
                "are progressively mapped. Geofabrik /africa/ "
                "PBF (~132 MB). Notable features include the "
                "Simien Mountains and Bale Mountains National "
                "Parks (both UNESCO sites), the Danakil "
                "Depression (one of the hottest places on "
                "Earth), and the rock-hewn churches of "
                "Lalibela and the ancient obelisks of Aksum.",
    "malawi": "Landlocked Southeast African country dominated "
                "by Lake Malawi (Lake Nyasa), the ninth-largest "
                "lake in the world and home to more species of "
                "fish than any other. Capital Lilongwe has "
                "decent OSM coverage; the shoreline of Lake "
                "Malawi and the southern Shire Highlands are "
                "progressively mapped. Geofabrik /africa/ PBF "
                "(~147 MB). Notable protected areas include "
                "Lake Malawi National Park (a UNESCO World "
                "Heritage site) and Nyika National Park on "
                "the Zambia border.",
    "somalia": "Horn of Africa country on the Indian Ocean, "
                "with the self-declared republic of Somaliland "
                "in the north and Puntland in the northeast. "
                "Capital Mogadishu has limited OSM coverage due "
                "to ongoing conflict; Somaliland (Hargeisa, "
                "Berbera port) has somewhat better mapping. "
                "Geofabrik /africa/ PBF (~156 MB). Notable "
                "features include the Horn of Africa's northern "
                "coastline, the Shabelle and Jubba river "
                "valleys in the south, and the Bajuni / "
                "Banaadir coastal islands.",
    "mali": "Large landlocked West African country (formerly "
                "French Sudan), with most of its territory in "
                "the Saharan and Sahelian zones. Capital Bamako "
                "on the Niger River has good OSM coverage; the "
                "historic cities of Timbuktu, Djenné, and Gao "
                "are progressively mapped. Geofabrik /africa/ "
                "PBF (~164 MB). Notable features include the "
                "Bandiagara Escarpment (home to the Dogon "
                "people and a UNESCO World Heritage site), the "
                "Niger River Inner Delta, and the historic "
                "trans-Saharan trade route cities.",
    "zimbabwe": "Southern African landlocked country (formerly "
                "Rhodesia) with the high plateau of the "
                "Zimbabwe Craton. Capital Harare has good OSM "
                "coverage; Bulawayo and the Victoria Falls "
                "area are progressively mapped. Geofabrik "
                "/africa/ PBF (~170 MB). Notable features "
                "include Victoria Falls / Mosi-oa-Tunya (a "
                "transboundary UNESCO site shared with Zambia), "
                "the Great Zimbabwe ruins, Hwange National Park "
                "(one of Africa's largest elephant sanctuaries), "
                "and Lake Kariba (one of the world's largest "
                "artificial lakes).",
    "egypt": "Large North African country dominated by the "
                "Nile Valley and the Sahara Desert, with a "
                "small but dense population along the river. "
                "Capital Cairo is the largest city in the Arab "
                "world with very good OSM coverage; Alexandria "
                "and the Nile Delta are similarly well-mapped. "
                "Geofabrik /africa/ PBF (~169 MB). Notable "
                "features include the pyramids of Giza, the "
                "ancient sites of Luxor and Karnak, the Sinai "
                "Peninsula, and the Red Sea coast with its "
                "coral reefs.",
    "sudan": "Large North African country on the Red Sea "
                "(formerly Anglo-Egyptian Sudan), with most of "
                "its territory in the Sahara and Sahel. Capital "
                "Khartoum (at the confluence of the Blue and "
                "White Nile) has decent OSM coverage; the "
                "Darfur region and the eastern mountains are "
                "extremely sparsely mapped due to conflict. "
                "Geofabrik /africa/ PBF (~193 MB). Notable "
                "features include the ancient Nubian pyramids "
                "at Meroë (a UNESCO World Heritage site), the "
                "Red Sea coast with its coral reefs, and the "
                "Nile cataracts.",
    "cameroon": "Central African country on the Gulf of "
                "Guinea (formerly French Cameroun, then a "
                "British-French trusteeship), often called "
                "'Africa in miniature' for its geographic and "
                "cultural diversity. Capital Yaoundé and "
                "economic capital Douala both have good OSM "
                "coverage. Geofabrik /africa/ PBF (~213 MB). "
                "Notable features include Mount Cameroon (the "
                "highest peak in West Africa at 4,095 m), the "
                "Waza National Park in the north, and the Dja "
                "Faunal Reserve (a UNESCO World Heritage site).",
    "zambia": "Landlocked Southern African country (formerly "
                "Northern Rhodesia) with the high plateau of "
                "the Zambezi watershed. Capital Lusaka has "
                "good OSM coverage; the Copperbelt and Victoria "
                "Falls are progressively mapped. Geofabrik "
                "/africa/ PBF (~240 MB). Notable features "
                "include Victoria Falls / Mosi-oa-Tunya (a "
                "transboundary UNESCO site shared with "
                "Zimbabwe), Lake Kariba (one of the world's "
                "largest artificial lakes), the Kafue and "
                "South Luangwa National Parks, and the "
                "Copperbelt mining region.",
    "mozambique": "Southeast African country on the Indian "
                "Ocean (formerly Portuguese East Africa), with "
                "a long coastline and the Zambezi River "
                "crossing the country. Capital Maputo has "
                "good OSM coverage; the northern provinces and "
                "the Zambezi Delta are sparser. Geofabrik "
                "/africa/ PBF (~243 MB). Notable features "
                "include the Bazaruto Archipelago (a marine "
                "national park), the port city of Beira, and "
                "Gorongosa National Park (a major ecotourism "
                "destination in the Rift Valley).",
    "kenya": "East African country on the Indian Ocean, "
                "crossed by the equator and the Great Rift "
                "Valley. Capital Nairobi has very good OSM "
                "coverage; Mombasa on the coast and the "
                "Maasai Mara / Serengeti ecosystem are well-"
                "mapped. Geofabrik /africa/ PBF (~331 MB). "
                "Notable features include Mount Kenya (5,199 "
                "m), the Maasai Mara National Reserve (famous "
                "for the annual wildebeest migration), "
                "Amboseli and Tsavo National Parks, and the "
                "Rift Valley lakes (Naivasha, Nakuru, "
                "Bogoria).",
    "uganda": "Landlocked East African country (formerly the "
                "British Protectorate of Uganda), sitting on "
                "the East African Plateau. Capital Kampala "
                "has good OSM coverage; the western Rift "
                "Valley and the source of the White Nile at "
                "Lake Victoria are progressively mapped. "
                "Geofabrik /africa/ PBF (~353 MB). Notable "
                "features include Bwindi Impenetrable "
                "National Park (home to half the world's "
                "mountain gorillas, a UNESCO World Heritage "
                "site), Murchison Falls National Park, and "
                "the Rwenzori Mountains ('Mountains of the "
                "Moon').",
    "south-africa": "Large Southern African country on the "
                "Atlantic and Indian Oceans, with three "
                "capital cities: Pretoria (administrative), "
                "Cape Town (legislative), and Bloemfontein "
                "(judicial). Cape Town and Johannesburg have "
                "very good OSM coverage; Durban, Pretoria, "
                "and the Garden Route are progressively "
                "mapped. Geofabrik /africa/ PBF (~396 MB). "
                "Notable features include Table Mountain, "
                "Kruger National Park (one of Africa's "
                "largest game reserves), the Drakensberg "
                "mountains, the Cape Winelands, and Robben "
                "Island.",
    "congo-democratic-republic": "Large Central African "
                "country (formerly Zaire), the second-largest "
                "country in Africa, dominated by the Congo "
                "River basin and the equatorial rainforest. "
                "Capital Kinshasa (across the river from "
                "Brazzaville) has decent OSM coverage; "
                "Lubumbashi in the Katanga Copperbelt and "
                "Goma in the east are progressively mapped. "
                "Geofabrik /africa/ PBF (~393 MB). Notable "
                "features include the Virunga National Park "
                "(a UNESCO site, home to mountain gorillas), "
                "the Okapi Wildlife Reserve, and the Congo "
                "River and its tributaries.",
    "nigeria": "Large West African country, the most populous "
                "in Africa (formerly British Nigeria), with "
                "diverse geography from the Atlantic coast to "
                "the Sahel. Capital Abuja and economic capital "
                "Lagos both have very good OSM coverage. "
                "Geofabrik /africa/ PBF (~678 MB, the largest "
                "in /africa/). Notable features include the "
                "Niger Delta (one of the world's largest "
                "wetlands), the Jos Plateau, the Sahel regions "
                "in the north, and Yankari National Park.",
    "netherlands": "Processed via 12 Geofabrik provincial sub-PBFs. "
                   "Among the best-mapped countries in the world.",
    "norway": "Processed via 6 Geofabrik regional sub-PBFs "
              "(landsdeler + Svalbard). Very long coastline and "
              "fjords make this a polygon-rich dataset.",
    "poland": "Processed via 16 Geofabrik voivodeship sub-PBFs. "
              "Active community; urban mapping is strong across "
              "all 16 regions.",
    "portugal": "Mainland and Madeira/Azores are well-mapped. "
                "Lisbon and Porto have detailed urban data.",
    "romania": "Bucharest and the major cities have strong urban "
               "coverage; the Carpathians are well-mapped for "
               "hiking.",
    "serbia": "Belgrade has dense urban mapping; rural landuse "
              "is moderate.",
    "slovakia": "Strong mapping in the lowlands and around "
                "Bratislava; the Tatras are well-mapped for "
                "hiking.",
    "slovenia": "Small, densely-mapped country. The Julian Alps and "
                "the Karst are particularly well-covered.",
    "spain": "Processed via 17 Geofabrik autonomous-community "
             "sub-PBFs (comunidades + Ceuta/Melilla). Excellent "
             "coverage nationwide.",
    "sweden": "Strong nationwide mapping. The northern forest and "
              "mountain areas are well-covered despite low "
              "population.",
    "switzerland": "Among the world's best-mapped countries. "
                   "Excellent landuse, buildings, and the famous "
                   "Swiss hiking trail network.",
    "turkey": "Istanbul, Ankara, and the Aegean coast have strong "
              "urban mapping; eastern Anatolia is sparser. The "
              "European portion of Turkey (Eastern Thrace) is "
              "what's in this dataset.",
    "ukraine": "Active mapping despite the conflict. Kyiv, Lviv, "
               "Kharkiv, and Odesa have strong urban coverage.",
    "united-kingdom": "Processed via 3 Geofabrik sub-PBFs (england, "
                      "scotland, wales). Among the world's best-mapped "
                      "countries.",
}


def country_source_description(country: str) -> str:
    """One-line description of the source PBF(s) used for this country."""
    if country in REGIONAL_SUB_PBFS:
        n = len(REGIONAL_SUB_PBFS[country])
        return f"`{country}-latest.osm.pbf` *processed via {n} Geofabrik regional sub-PBFs*"
    return f"`{country}-latest.osm.pbf`"


def country_note(country: str, n_polygons: int, extract_status: str) -> str:
    """Return a 1-paragraph blurb for a country, falling back to a generic line."""
    if country in COUNTRY_NOTES:
        return COUNTRY_NOTES[country]
    from osm_polygon_selection.pbf_meta import geofabrik_url
    return (
        f"{country.title()} has {n_polygons:,} polygons in this dataset. "
        f"Extract status: **{extract_status}**. "
        f"Source: Geofabrik [`{country}-latest.osm.pbf`]({geofabrik_url(country)})."
    )


__all__ = [
    "COUNTRY_NOTES",
    "REGIONAL_SUB_PBFS",
    "country_note",
    "country_source_description",
]
