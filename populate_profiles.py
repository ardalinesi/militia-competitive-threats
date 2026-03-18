#!/usr/bin/env python3
# Auto-populate competitive profiles for all Militia holdings
import json

# Load the existing template
with open("holdings_competitive_profile.json", "r") as f:
    profiles = json.load(f)

# Define profiles for all operating companies
# Skip: Cash&Other, JPY, FGXXX (money market), ETFs (IWM, QQQ, SDIV, MSOS)
company_profiles = {
    # ============================================================
    # US LONG POSITIONS
    # ============================================================
    "TSM": {
        "sector": "Semiconductors",
        "products": "Advanced semiconductor foundry services, chip manufacturing (3nm/5nm/7nm), wafer fabrication, packaging",
        "competitor_keywords": ["semiconductor foundry", "chip manufacturing", "wafer fabrication", "advanced packaging", "AI chips"],
    },
    "GOOG": {
        "sector": "Technology / Internet",
        "products": "Search engine, digital advertising, cloud computing (GCP), Android, AI/ML, YouTube",
        "competitor_keywords": ["search engine", "digital advertising", "cloud computing", "AI platform", "generative AI", "video streaming"],
    },
    "AMZN": {
        "sector": "E-commerce / Cloud Computing",
        "products": "Online retail marketplace, AWS cloud services, Prime streaming, logistics/fulfillment, Alexa/devices",
        "competitor_keywords": ["ecommerce marketplace", "cloud computing", "fulfillment logistics", "online retail", "AI cloud services"],
    },
    "ET": {
        "sector": "Midstream Energy",
        "products": "Natural gas pipelines, NGL fractionation, crude oil transportation, LNG export terminal",
        "competitor_keywords": ["natural gas pipeline", "midstream energy", "NGL fractionation", "LNG terminal", "energy infrastructure"],
    },
    "WES": {
        "sector": "Midstream Energy",
        "products": "Natural gas gathering/processing, crude oil transportation, produced water disposal",
        "competitor_keywords": ["natural gas gathering", "midstream services", "produced water disposal", "gas processing"],
    },
    "MPLX": {
        "sector": "Midstream Energy",
        "products": "Natural gas gathering/processing, crude oil/NGL logistics, pipeline transportation",
        "competitor_keywords": ["natural gas processing", "NGL logistics", "midstream pipeline", "crude oil transport"],
    },
    "SFM": {
        "sector": "Grocery Retail",
        "products": "Natural/organic grocery stores, fresh produce, health-focused food retail",
        "competitor_keywords": ["organic grocery", "natural food store", "health food retail", "fresh grocery delivery", "specialty grocery"],
    },
    "AX": {
        "sector": "Digital Banking",
        "products": "Online banking, commercial/industrial lending, mortgage lending, auto lending, fintech banking",
        "competitor_keywords": ["digital bank", "online banking", "neobank", "fintech lending", "digital mortgage"],
    },
    "CSWC": {
        "sector": "Business Development Company",
        "products": "Middle market lending, direct lending, mezzanine financing, equity co-investments",
        "competitor_keywords": ["direct lending", "middle market lending", "private credit", "BDC"],
    },
    "AGM": {
        "sector": "Agricultural Finance",
        "products": "Agricultural mortgage loans, farm/ranch financing, rural infrastructure lending, USDA-backed securities",
        "competitor_keywords": ["agricultural lending", "farm mortgage", "rural finance", "ag-tech lending"],
    },
    "MEDP": {
        "sector": "Clinical Research / CRO",
        "products": "Contract research organization, clinical trial management, bioanalytical lab services, regulatory consulting",
        "competitor_keywords": ["clinical trial", "CRO", "contract research", "clinical data management", "decentralized trials", "biotech services"],
    },
    "CCS": {
        "sector": "Homebuilding",
        "products": "Single-family homes, attached homes, entry-level/move-up housing, mortgage origination",
        "competitor_keywords": ["homebuilder", "residential construction", "modular homes", "proptech", "3D printed homes"],
    },
    "MS": {
        "sector": "Investment Banking / Financial Services",
        "products": "Investment banking, wealth management, institutional securities, asset management",
        "competitor_keywords": ["investment banking", "wealth management", "fintech trading", "robo-advisor", "digital wealth"],
    },
    "PKBK": {
        "sector": "Community Banking",
        "products": "Commercial banking, residential mortgage lending, SBA loans, business banking",
        "competitor_keywords": ["community bank", "digital banking", "fintech lending", "small business lending"],
    },
    "TX": {
        "sector": "Steel Manufacturing",
        "products": "Flat steel products, long steel products, iron ore mining, steel distribution",
        "competitor_keywords": ["steel manufacturing", "flat steel", "steel distribution", "green steel"],
    },

    # ============================================================
    # MEXICAN LONG POSITIONS
    # ============================================================
    "OMAB": {
        "sector": "Airport Operations",
        "products": "Airport management (13 airports in central/northern Mexico), aeronautical/non-aeronautical revenue",
        "competitor_keywords": ["airport operations", "airport concession", "aeronautical services", "airport technology"],
    },
    "PAC": {
        "sector": "Airport Operations",
        "products": "Airport management (12 airports in Pacific Mexico incl Guadalajara/Tijuana), duty-free, parking",
        "competitor_keywords": ["airport operations", "airport concession", "aeronautical services", "airport technology"],
    },
    "ASR": {
        "sector": "Airport Operations",
        "products": "Airport management (9 airports in SE Mexico incl Cancun), hotel, cargo terminal",
        "competitor_keywords": ["airport operations", "airport concession", "aeronautical services", "airport technology"],
    },
    "GRUMAB MM": {
        "sector": "Food Manufacturing",
        "products": "Corn flour (Maseca), tortillas, flatbreads, wheat flour, rice, palm oil",
        "competitor_keywords": ["corn flour", "tortilla manufacturing", "flatbread", "food manufacturing", "plant-based flour"],
    },
    "WALMEX* MM": {
        "sector": "Retail",
        "products": "Supermarkets (Walmart, Bodega Aurrera), Sam's Club Mexico, ecommerce, Bait (fintech)",
        "competitor_keywords": ["Mexico retail", "supermarket", "ecommerce Mexico", "quick commerce", "discount retail"],
    },

    # ============================================================
    # EUROPEAN / OTHER LONG POSITIONS
    # ============================================================
    "BNP FP": {
        "sector": "Banking",
        "products": "Corporate/institutional banking, retail banking, asset management, insurance, securities services",
        "competitor_keywords": ["digital banking Europe", "neobank", "fintech payments", "European banking", "trade finance platform"],
    },
    "MC FP": {
        "sector": "Luxury Goods",
        "products": "Fashion/leather goods (Louis Vuitton, Dior), wines/spirits (Hennessy, Moët), watches/jewelry (Bulgari, Tiffany), perfume/cosmetics, selective retail (Sephora, DFS)",
        "competitor_keywords": ["luxury fashion", "luxury ecommerce", "DTC luxury brand", "prestige beauty", "luxury resale"],
    },
    "AENA SM": {
        "sector": "Airport Operations",
        "products": "Airport management (46 Spanish airports + London Luton), aeronautical/commercial revenue",
        "competitor_keywords": ["airport operations", "airport concession", "airport technology", "aeronautical services"],
    },
    "JFN SW": {
        "sector": "Tourism / Transportation",
        "products": "Jungfrau railway, mountain tourism (Jungfraujoch, Grindelwald), hotels, ski operations",
        "competitor_keywords": ["mountain tourism", "adventure tourism", "travel experience platform", "outdoor recreation tech"],
    },
    "FHZN SW": {
        "sector": "Airport Operations",
        "products": "Zurich Airport management, airport commercial services, airport real estate, international concessions",
        "competitor_keywords": ["airport operations", "airport concession", "airport technology", "aeronautical services"],
    },
    "CAAP": {
        "sector": "Airport Operations",
        "products": "Airport concessions in Argentina, Brazil, Uruguay, Ecuador, Armenia, Italy",
        "competitor_keywords": ["airport operations", "airport concession", "Latin America airports", "aeronautical services"],
    },
    "1913 HK": {
        "sector": "Luxury Fashion",
        "products": "Prada leather goods/fashion, Miu Miu fashion, Church's shoes, Car Shoe, luxury retail",
        "competitor_keywords": ["luxury fashion", "luxury handbags", "luxury ecommerce", "DTC luxury", "luxury resale platform"],
    },

    # ============================================================
    # US SHORT POSITIONS
    # ============================================================
    "KMX": {
        "sector": "Used Car Retail",
        "products": "Used car retail superstores, auto financing, wholesale auctions, online car buying",
        "competitor_keywords": ["online car sales", "used car marketplace", "auto ecommerce", "digital car dealer", "car subscription"],
    },
    "CVNA": {
        "sector": "Online Used Car Sales",
        "products": "Online car buying/selling platform, auto financing, vehicle delivery, car vending machines",
        "competitor_keywords": ["online car sales", "used car marketplace", "auto ecommerce", "digital car dealer", "car subscription"],
    },
    "WFC": {
        "sector": "Banking",
        "products": "Consumer banking, commercial banking, mortgage lending, wealth management, credit cards",
        "competitor_keywords": ["digital bank", "neobank", "fintech lending", "digital mortgage", "BNPL", "embedded finance"],
    },
    "BN": {
        "sector": "Alternative Asset Management",
        "products": "Infrastructure investing, real estate, private equity, renewable energy, credit, insurance",
        "competitor_keywords": ["alternative asset management", "infrastructure investing", "private equity platform", "tokenized real estate"],
    },
    "SBUX": {
        "sector": "Coffee / Quick Service Restaurant",
        "products": "Coffee shops, specialty coffee drinks, food items, packaged coffee, mobile ordering",
        "competitor_keywords": ["specialty coffee", "coffee chain", "coffee delivery", "DTC coffee", "automated coffee"],
    },
    "DLR": {
        "sector": "Data Center REIT",
        "products": "Colocation data centers, interconnection, managed hosting, hyperscale data centers",
        "competitor_keywords": ["data center", "colocation", "edge computing", "cloud infrastructure", "AI data center"],
    },
    "TCPC": {
        "sector": "Business Development Company",
        "products": "Direct lending to middle-market tech/venture companies, mezzanine debt, equity investments",
        "competitor_keywords": ["direct lending", "venture debt", "private credit", "fintech lending platform"],
    },
    "TPVG": {
        "sector": "Venture Lending BDC",
        "products": "Venture growth stage lending, equipment financing, direct equity investments in tech startups",
        "competitor_keywords": ["venture debt", "growth lending", "startup lending", "revenue-based financing"],
    },
    "RWAY": {
        "sector": "Growth Stage BDC",
        "products": "Senior secured lending to growth-stage companies, term loans, revolving credit",
        "competitor_keywords": ["growth lending", "venture debt", "revenue-based financing", "startup lending"],
    },
    "OXLC": {
        "sector": "CLO Fund",
        "products": "CLO equity/debt tranches, leveraged loan investments, structured credit",
        "competitor_keywords": ["CLO", "structured credit", "leveraged lending", "private credit platform"],
    },
    "PSEC": {
        "sector": "Business Development Company",
        "products": "Middle market lending, real estate lending, structured credit, online lending",
        "competitor_keywords": ["direct lending", "middle market lending", "private credit", "online lending platform"],
    },

    # ============================================================
    # JAPANESE TRADING HOUSES (SOGO SHOSHA)
    # ============================================================
    "8058 JP": {
        "sector": "Trading / Conglomerate",
        "products": "Energy, metals, machinery, chemicals, food, industrial finance, urban development",
        "competitor_keywords": ["commodity trading", "supply chain platform", "B2B marketplace", "energy trading technology"],
    },
    "8053 JP": {
        "sector": "Trading / Conglomerate",
        "products": "Metal products, transportation/construction, infrastructure, media/digital, mineral resources, energy",
        "competitor_keywords": ["commodity trading", "supply chain platform", "B2B marketplace", "energy trading technology"],
    },
    "8001 JP": {
        "sector": "Trading / Conglomerate",
        "products": "Textiles, machinery, metals/minerals, energy, food, chemicals, ICT, real estate, finance",
        "competitor_keywords": ["commodity trading", "supply chain platform", "B2B marketplace", "trade finance technology"],
    },
    "8031 JP": {
        "sector": "Trading / Conglomerate",
        "products": "Iron ore, LNG, machinery, chemicals, food, finance, real estate, ICT",
        "competitor_keywords": ["commodity trading", "supply chain platform", "B2B marketplace", "energy trading technology"],
    },
    "2768 JP": {
        "sector": "Trading / Conglomerate",
        "products": "Automotive, aerospace, energy/infrastructure, metals/coal, chemicals, food/agriculture, retail",
        "competitor_keywords": ["commodity trading", "supply chain platform", "B2B marketplace", "trade finance technology"],
    },
    "8078 JP": {
        "sector": "Steel / Materials Trading",
        "products": "Steel products trading, non-ferrous metals, food distribution, petroleum, chemicals, lumber",
        "competitor_keywords": ["steel trading", "metals marketplace", "B2B materials trading", "steel supply chain"],
    },

    # ============================================================
    # JAPANESE REAL ESTATE
    # ============================================================
    "3003 JP": {
        "sector": "Real Estate",
        "products": "Office buildings, commercial facilities, hotels, senior housing, real estate leasing, asset management",
        "competitor_keywords": ["real estate tech", "proptech", "office leasing platform", "coworking space", "flexible office"],
    },
    "8830 JP": {
        "sector": "Real Estate",
        "products": "Office buildings, residential development, real estate leasing, custom-built housing",
        "competitor_keywords": ["real estate tech", "proptech", "office leasing platform", "coworking space", "flexible office"],
    },
    "8804 JP": {
        "sector": "Real Estate",
        "products": "Office buildings, condominiums, commercial facilities, asset management, real estate fund management",
        "competitor_keywords": ["real estate tech", "proptech", "online condo marketplace", "coworking", "flexible office"],
    },
    "3288 JP": {
        "sector": "Real Estate / Homebuilding",
        "products": "Detached housing, condominiums, real estate brokerage, wealth consulting, US real estate",
        "competitor_keywords": ["proptech", "online real estate", "iBuyer", "digital mortgage Japan", "real estate marketplace"],
    },
    "8850 JP": {
        "sector": "Real Estate / Property Management",
        "products": "Condominium development, property management, construction, real estate brokerage, senior living",
        "competitor_keywords": ["proptech", "property management tech", "real estate marketplace", "smart building"],
    },
    "8935 JP": {
        "sector": "Real Estate / Condominiums",
        "products": "Investment condominiums for individuals, property management, real estate fund management",
        "competitor_keywords": ["proptech", "real estate crowdfunding", "investment property platform", "condo marketplace"],
    },

    # ============================================================
    # JAPANESE SEMICONDUCTOR / ELECTRONICS
    # ============================================================
    "6920 JP": {
        "sector": "Semiconductor Equipment",
        "products": "Semiconductor mask inspection/review equipment, EUV mask blank inspection, SEM review systems",
        "competitor_keywords": ["semiconductor inspection", "EUV lithography", "mask inspection", "wafer inspection", "chip metrology"],
    },
    "6323 JP": {
        "sector": "Semiconductor Equipment",
        "products": "Semiconductor wafer handling robots, EFEM (Equipment Front End Module), wafer sorters, transfer systems",
        "competitor_keywords": ["semiconductor automation", "wafer handling", "cleanroom robotics", "fab automation", "semiconductor robotics"],
    },
    "3445 JP": {
        "sector": "Semiconductor Materials",
        "products": "Silicon wafer reclaim/repolishing, silicon parts for semiconductor equipment, SiC substrates",
        "competitor_keywords": ["silicon wafer", "semiconductor materials", "SiC substrate", "wafer reclaim", "compound semiconductor"],
    },
    "4966 JP": {
        "sector": "Specialty Chemicals / Semiconductor",
        "products": "Surface finishing chemicals (plating for electronics), semiconductor packaging chemicals, industrial plating",
        "competitor_keywords": ["electroplating chemicals", "semiconductor packaging", "surface treatment", "advanced packaging materials"],
    },
    "6626 JP": {
        "sector": "Electronic Components",
        "products": "Thermistors (temperature sensors), sensor modules, automotive sensors, industrial sensors",
        "competitor_keywords": ["temperature sensor", "thermistor", "IoT sensor", "MEMS sensor", "automotive sensor"],
    },
    "8154 JP": {
        "sector": "Electronics Distribution",
        "products": "Electronic component distribution, EMS (contract manufacturing), IoT solutions, LED systems",
        "competitor_keywords": ["electronic component distribution", "EMS manufacturing", "IoT platform", "electronics marketplace"],
    },
    "7609 JP": {
        "sector": "Electronics Distribution",
        "products": "Semiconductor distribution, electronic component sales, manufacturing equipment, FA systems",
        "competitor_keywords": ["semiconductor distribution", "electronic components", "FA equipment", "electronics marketplace"],
    },
    "6670 JP": {
        "sector": "PC / Electronics",
        "products": "Desktop PCs (mouse brand), gaming PCs, peripherals, iiyama monitors, EMS services",
        "competitor_keywords": ["PC manufacturing", "gaming PC", "custom PC", "direct-to-consumer electronics"],
    },
    "6676 JP": {
        "sector": "Computer Peripherals / Networking",
        "products": "Wi-Fi routers, NAS storage, external drives, flash memory, networking equipment (Buffalo brand)",
        "competitor_keywords": ["networking equipment", "NAS storage", "WiFi router", "smart home networking", "mesh WiFi"],
    },
    "7725 JP": {
        "sector": "Semiconductor Equipment",
        "products": "Light source equipment for semiconductor inspection, LED inspection, solar simulators",
        "competitor_keywords": ["semiconductor inspection", "optical inspection", "LED inspection", "light source equipment"],
    },

    # ============================================================
    # JAPANESE FINANCIAL SERVICES
    # ============================================================
    "8697 JP": {
        "sector": "Financial Exchange",
        "products": "Tokyo Stock Exchange, Osaka Exchange (derivatives), Japan Securities Clearing, market data",
        "competitor_keywords": ["stock exchange", "trading platform", "crypto exchange", "DeFi", "digital asset exchange"],
    },
    "8473 JP": {
        "sector": "Online Financial Services",
        "products": "Online securities (SBI Securities), banking, insurance, crypto exchange, asset management, biotech investments",
        "competitor_keywords": ["online brokerage", "neobank", "crypto exchange", "robo-advisor", "fintech platform"],
    },
    "8604 JP": {
        "sector": "Investment Banking / Securities",
        "products": "Securities brokerage, investment banking, asset management, wholesale trading, retail financial services",
        "competitor_keywords": ["online brokerage", "digital wealth management", "robo-advisor", "fintech trading"],
    },
    "7326 JP": {
        "sector": "Insurance",
        "products": "Online life insurance, insurance comparison platform, small-amount short-term insurance",
        "competitor_keywords": ["insurtech", "online insurance", "embedded insurance", "insurance comparison", "digital insurance"],
    },
    "8704 JP": {
        "sector": "Online Securities",
        "products": "Online FX trading, securities brokerage, financial derivatives trading",
        "competitor_keywords": ["online trading", "FX platform", "retail trading", "crypto trading", "social trading"],
    },
    "9435 JP": {
        "sector": "Telecom / IT Services",
        "products": "Telecom sales (NTT/KDDI reseller), OA equipment, insurance sales, IoT, mobile, broadband",
        "competitor_keywords": ["telecom reseller", "IT services", "managed services", "digital transformation", "business telecom"],
    },

    # ============================================================
    # JAPANESE FOOD & BEVERAGE
    # ============================================================
    "2208 JP": {
        "sector": "Confectionery / Snacks",
        "products": "Biscuits, snacks, chocolates, rice crackers, gummies (Alfort, Petit, LuMonde brands)",
        "competitor_keywords": ["snack food", "confectionery", "DTC snacks", "healthy snacks", "premium confectionery"],
    },
    "2801 JP": {
        "sector": "Food / Condiments",
        "products": "Soy sauce, teriyaki sauce, food seasonings, soy milk, Del Monte canned foods, Oriental Trading",
        "competitor_keywords": ["soy sauce", "Asian condiments", "plant-based food", "DTC food brand", "specialty sauce"],
    },
    "2201 JP": {
        "sector": "Confectionery",
        "products": "Caramels, chocolates (DARS, Bake), biscuits, ice cream, frozen desserts, health food (in:bar)",
        "competitor_keywords": ["confectionery", "chocolate brand", "healthy snacks", "DTC sweets", "functional food"],
    },
    "2001 JP": {
        "sector": "Flour Milling / Food",
        "products": "Wheat flour, premixes, frozen food, pasta (Oh'my brand), healthcare food",
        "competitor_keywords": ["flour milling", "frozen food", "plant-based food", "alternative protein", "food manufacturing"],
    },
    "2602 JP": {
        "sector": "Edible Oil / Food",
        "products": "Cooking oils (soybean, canola, olive), MCT oil, margarines, soy protein, fine chemicals",
        "competitor_keywords": ["edible oil", "plant-based oil", "specialty oil", "healthy cooking oil", "food ingredients"],
    },
    "2924 JP": {
        "sector": "Food Packaging / Distribution",
        "products": "Food packaging materials, disposable food containers, food ingredients distribution, household goods",
        "competitor_keywords": ["food packaging", "sustainable packaging", "biodegradable containers", "food service supplies"],
    },
    "8043 JP": {
        "sector": "Meat / Food Distribution",
        "products": "Meat processing (beef/pork), meat wholesale/distribution, imported meat, deli products",
        "competitor_keywords": ["meat processing", "alternative protein", "plant-based meat", "cultured meat", "food distribution tech"],
    },
    "2222 JP": {
        "sector": "Spirits / Beverages",
        "products": "Shochu spirits, liqueurs, sake, fruit wines, soft drinks",
        "competitor_keywords": ["craft spirits", "DTC alcohol", "premium spirits", "RTD beverages", "non-alcoholic spirits"],
    },

    # ============================================================
    # JAPANESE CONSTRUCTION / ENGINEERING
    # ============================================================
    "1828 JP": {
        "sector": "Construction Engineering",
        "products": "Plant engineering, environmental engineering, water treatment, civil engineering, building construction",
        "competitor_keywords": ["construction tech", "water treatment", "environmental tech", "modular construction", "green building"],
    },
    "1866 JP": {
        "sector": "Construction",
        "products": "General construction, civil engineering, architecture, real estate development in Hokkaido region",
        "competitor_keywords": ["construction tech", "modular construction", "BIM software", "construction robotics"],
    },
    "1847 JP": {
        "sector": "Construction",
        "products": "Building construction, renovation, commercial facilities, condominiums, office buildings",
        "competitor_keywords": ["construction tech", "renovation tech", "modular construction", "smart building"],
    },
    "1879 JP": {
        "sector": "Construction",
        "products": "Building construction, renovation, seismic retrofitting, environmental solutions, real estate",
        "competitor_keywords": ["construction tech", "seismic retrofitting", "modular construction", "renovation tech"],
    },
    "1867 JP": {
        "sector": "Construction / Civil Engineering",
        "products": "Civil engineering, building construction, ground improvement, infrastructure maintenance, real estate",
        "competitor_keywords": ["construction tech", "infrastructure maintenance", "ground improvement", "construction robotics"],
    },
    "1911 JP": {
        "sector": "Forestry / Housing",
        "products": "Custom-built wooden homes, timber/building materials, overseas housing, renewable energy, real estate",
        "competitor_keywords": ["prefab housing", "modular homes", "sustainable construction", "mass timber", "green building"],
    },

    # ============================================================
    # JAPANESE INDUSTRIAL / MACHINERY
    # ============================================================
    "6432 JP": {
        "sector": "Construction Equipment",
        "products": "Compact excavators, compact track loaders, wheel loaders, compact equipment for global markets",
        "competitor_keywords": ["compact excavator", "construction equipment", "electric excavator", "autonomous construction"],
    },
    "6250 JP": {
        "sector": "Outdoor Power Equipment",
        "products": "Chain saws, brush cutters, lawn mowers, agricultural sprayers, generators (Kioritz/Echo/Shindaiwa)",
        "competitor_keywords": ["outdoor power equipment", "electric lawn tools", "battery-powered tools", "robotic mower"],
    },
    "6125 JP": {
        "sector": "Machine Tools",
        "products": "Surface grinders, internal grinders, machining centers, semiconductor-related grinding machines",
        "competitor_keywords": ["machine tools", "CNC grinding", "precision machining", "smart manufacturing", "digital twin manufacturing"],
    },
    "6340 JP": {
        "sector": "Packaging Machinery",
        "products": "Beverage filling/packaging systems, bottle-making machinery, water treatment, mechatronics",
        "competitor_keywords": ["packaging automation", "bottling equipment", "food processing machinery", "packaging robotics"],
    },
    "6490 JP": {
        "sector": "Industrial Seals / Fluid Control",
        "products": "Mechanical seals, bellows, packing/gaskets, expansion joints for semiconductor/chemical/energy plants",
        "competitor_keywords": ["mechanical seal", "fluid control", "industrial sealing", "semiconductor fluid control"],
    },
    "6845 JP": {
        "sector": "Building Automation / Control",
        "products": "Building automation systems (HVAC control), factory automation, life science instruments (process control)",
        "competitor_keywords": ["building automation", "smart building", "HVAC control", "IoT building management", "factory automation"],
    },
    "6745 JP": {
        "sector": "Fire Safety Equipment",
        "products": "Fire alarms, fire extinguishing systems, security systems, emergency communication systems",
        "competitor_keywords": ["fire safety", "smart fire detection", "IoT safety", "connected building safety", "fire prevention tech"],
    },
    "6420 JP": {
        "sector": "Commercial Refrigeration",
        "products": "Commercial refrigerators/freezers, display cases for retail, cold chain equipment, kitchen equipment",
        "competitor_keywords": ["commercial refrigeration", "cold chain technology", "smart refrigeration", "food retail equipment"],
    },
    "6951 JP": {
        "sector": "Scientific Instruments",
        "products": "Electron microscopes (SEM/TEM), mass spectrometers, NMR, semiconductor inspection, medical equipment",
        "competitor_keywords": ["electron microscope", "mass spectrometer", "scientific instruments", "semiconductor metrology", "cryo-EM"],
    },
    "7740 JP": {
        "sector": "Optical Equipment",
        "products": "Camera lenses (interchangeable), surveillance camera lenses, automotive camera lenses, drone lenses",
        "competitor_keywords": ["camera lens", "machine vision lens", "automotive camera", "surveillance optics", "computational photography"],
    },
    "7235 JP": {
        "sector": "Auto Parts",
        "products": "Automotive radiators, EGR coolers, oil coolers, EV thermal management, heat exchangers",
        "competitor_keywords": ["EV thermal management", "automotive cooling", "heat exchanger", "EV battery cooling"],
    },
    "7864 JP": {
        "sector": "Packaging",
        "products": "Shrink sleeve labels, shrink packaging, packaging systems, pouch packaging, overseas packaging",
        "competitor_keywords": ["sustainable packaging", "shrink labels", "smart packaging", "eco-friendly packaging"],
    },
    "6333 JP": {
        "sector": "Electric Equipment / Motors",
        "products": "Motors, pumps, power generators, ship automation systems, industrial fans, environmental equipment",
        "competitor_keywords": ["electric motor", "industrial pump", "energy-efficient motor", "marine automation"],
    },

    # ============================================================
    # JAPANESE MATERIALS / CHEMICALS
    # ============================================================
    "5393 JP": {
        "sector": "Industrial Materials",
        "products": "Thermal insulation (Rockwool), sealing materials (gaskets), industrial packing, fluororesin products, brake friction",
        "competitor_keywords": ["thermal insulation", "sealing materials", "industrial gaskets", "advanced materials", "aerogel insulation"],
    },
    "5480 JP": {
        "sector": "Specialty Steel",
        "products": "Stainless steel, nickel alloys, high-temperature alloys, corrosion-resistant alloys for chemical/energy/semiconductor",
        "competitor_keywords": ["specialty steel", "nickel alloy", "high-performance alloy", "advanced materials"],
    },
    "5351 JP": {
        "sector": "Refractories",
        "products": "Refractory products for steel/cement/glass industries, ceramic fiber, monolithic refractories, engineering",
        "competitor_keywords": ["refractory materials", "high-temperature materials", "advanced ceramics", "industrial furnace materials"],
    },
    "5363 JP": {
        "sector": "Refractories / Ceramics",
        "products": "Refractory products, fine ceramics, kiln furniture, functional ceramics for semiconductor/energy",
        "competitor_keywords": ["refractory", "fine ceramics", "advanced ceramics", "high-temperature materials"],
    },
    "4975 JP": {
        "sector": "Specialty Chemicals",
        "products": "Electroplating chemicals (for electronics/semiconductor), specialty chemicals for copper plating, surface treatment",
        "competitor_keywords": ["electroplating", "semiconductor chemicals", "surface treatment chemicals", "PCB chemicals"],
    },
    "4465 JP": {
        "sector": "Industrial Chemicals / Hygiene",
        "products": "Industrial detergents, food sanitation chemicals, dishwasher detergents, sanitizers for food service",
        "competitor_keywords": ["industrial cleaning", "food safety chemicals", "sanitation technology", "enzymatic cleaners"],
    },
    "4231 JP": {
        "sector": "Rubber / Polymer Products",
        "products": "Industrial hoses, automotive hoses, rubber sheets, polyurethane products, antivibration rubber",
        "competitor_keywords": ["industrial hose", "automotive rubber parts", "polymer products", "EV rubber components"],
    },
    "4251 JP": {
        "sector": "Functional Films / Materials",
        "products": "Optical films for LCD/OLED displays, diffusion sheets, cushioning materials, semiconductor tape",
        "competitor_keywords": ["optical film", "display materials", "functional film", "semiconductor tape", "OLED materials"],
    },
    "4628 JP": {
        "sector": "Paints / Coatings",
        "products": "Architectural coatings, fireproof coatings, floor coatings, waterproofing, civil engineering materials",
        "competitor_keywords": ["architectural coatings", "fireproof paint", "smart coatings", "eco-friendly coatings"],
    },

    # ============================================================
    # JAPANESE RETAIL / CONSUMER
    # ============================================================
    "8194 JP": {
        "sector": "Supermarket Retail",
        "products": "Life supermarket chain, natural/organic food, prepared foods, fresh produce (Kanto/Kinki area)",
        "competitor_keywords": ["online grocery", "grocery delivery", "quick commerce", "food delivery", "dark store"],
    },
    "2742 JP": {
        "sector": "Supermarket Retail",
        "products": "Halows supermarket chain (Chugoku region), fresh food, everyday groceries",
        "competitor_keywords": ["online grocery", "grocery delivery", "quick commerce", "food delivery", "dark store"],
    },
    "9823 JP": {
        "sector": "Supermarket Retail",
        "products": "Mammy Mart supermarket chain (Saitama/Kanto), fresh food, daily necessities",
        "competitor_keywords": ["online grocery", "grocery delivery", "quick commerce", "food delivery", "dark store"],
    },
    "7520 JP": {
        "sector": "Supermarket Retail",
        "products": "Eco's/Tairaya supermarket chain (Kanto), fresh food, everyday groceries",
        "competitor_keywords": ["online grocery", "grocery delivery", "quick commerce", "food delivery", "dark store"],
    },
    "5888 JP": {
        "sector": "Bicycle Retail",
        "products": "Daiwa Cycle bicycle retail chain, bicycles, cycling accessories, repair services",
        "competitor_keywords": ["bicycle retail", "e-bike", "bike sharing", "micro-mobility", "DTC bicycle"],
    },
    "7419 JP": {
        "sector": "Electronics Retail",
        "products": "Consumer electronics retail (Nojima stores), mobile phone sales, IoT devices, carrier services",
        "competitor_keywords": ["electronics ecommerce", "online electronics", "refurbished electronics", "electronics marketplace"],
    },
    "3333 JP": {
        "sector": "Bicycle / Sports Retail",
        "products": "Bicycle retail (Asahi Bicycle), cycling accessories, bicycle repair, fitness equipment",
        "competitor_keywords": ["bicycle retail", "e-bike", "bike sharing", "micro-mobility", "DTC bicycle"],
    },
    "7839 JP": {
        "sector": "Motorcycle Helmets / Safety",
        "products": "Premium motorcycle helmets (Shoei brand), safety gear, global motorcycle accessories",
        "competitor_keywords": ["motorcycle helmet", "smart helmet", "connected helmet", "safety wearable", "HUD helmet"],
    },
    "5889 JP": {
        "sector": "Eyewear",
        "products": "Eyeglass frames (Sabae/Fukui manufacturing), eyewear brand management, optical retail",
        "competitor_keywords": ["eyewear DTC", "online eyewear", "smart glasses", "prescription eyewear online"],
    },
    "7952 JP": {
        "sector": "Musical Instruments",
        "products": "Pianos (grand/upright/digital), electronic keyboards, music education, sound technology",
        "competitor_keywords": ["digital piano", "music education tech", "online music learning", "electronic instruments", "music streaming"],
    },

    # ============================================================
    # JAPANESE IT / SOFTWARE
    # ============================================================
    "9799 JP": {
        "sector": "IT Services",
        "products": "System integration, software development, IT infrastructure, cloud services, data center operations",
        "competitor_keywords": ["IT services", "cloud migration", "digital transformation", "low-code platform", "SaaS"],
    },
    "9145 JP": {
        "sector": "Logistics IT / Transportation",
        "products": "Logistics/transportation services, funeral services, IT solutions for logistics, real estate",
        "competitor_keywords": ["logistics tech", "freight marketplace", "last-mile delivery", "supply chain platform"],
    },
    "3762 JP": {
        "sector": "IT Solutions / Cybersecurity",
        "products": "Network security solutions, cloud security, medical IT systems, application/platform solutions",
        "competitor_keywords": ["cybersecurity", "cloud security", "medical IT", "security as a service", "zero trust"],
    },
    "4783 JP": {
        "sector": "IT Services / Parking",
        "products": "Parking management systems, IT infrastructure services, system development, data center services",
        "competitor_keywords": ["smart parking", "parking tech", "IT services", "IoT parking", "automated parking"],
    },
    "9739 JP": {
        "sector": "IT Services / Software",
        "products": "Embedded software development, enterprise systems, manufacturing IT, telecom systems, IoT solutions",
        "competitor_keywords": ["embedded software", "IoT platform", "manufacturing IT", "edge computing", "digital twin"],
    },
    "4743 JP": {
        "sector": "IT Services",
        "products": "Financial IT systems, card payment systems, enterprise software, system integration, BPO",
        "competitor_keywords": ["payment technology", "fintech", "card processing", "financial IT", "SaaS"],
    },
    "9702 JP": {
        "sector": "IT Services / Software",
        "products": "System integration, embedded software, enterprise solutions, IT outsourcing, mobile app development",
        "competitor_keywords": ["IT services", "system integration", "low-code platform", "digital transformation", "SaaS"],
    },
    "9709 JP": {
        "sector": "IT Services",
        "products": "Business systems development, ERP consulting, cloud services, IT infrastructure management",
        "competitor_keywords": ["IT services", "ERP", "cloud services", "digital transformation", "SaaS platform"],
    },
    "3679 JP": {
        "sector": "Internet / Marketplace",
        "products": "Job search platform, real estate search, car search, lifestyle comparison services (ZIGExN)",
        "competitor_keywords": ["job marketplace", "real estate search", "online classifieds", "vertical search platform"],
    },
    "4318 JP": {
        "sector": "HR / Information Services",
        "products": "Human resource services, staffing/recruitment, information services, temporary staffing",
        "competitor_keywords": ["HR tech", "recruitment platform", "staffing marketplace", "AI recruiting", "talent platform"],
    },
    "9418 JP": {
        "sector": "Streaming / Telecom",
        "products": "U-NEXT video streaming, USEN business music/services, energy supply, store solutions",
        "competitor_keywords": ["video streaming", "OTT platform", "business music", "digital content platform"],
    },

    # ============================================================
    # JAPANESE STAFFING / HR
    # ============================================================
    "2415 JP": {
        "sector": "Education / Staffing",
        "products": "Human resource development, education business, vocational schools, staffing/temporary workers",
        "competitor_keywords": ["edtech", "online education", "HR tech", "staffing platform", "e-learning"],
    },
    "7781 JP": {
        "sector": "Manufacturing Staffing",
        "products": "Factory staffing/dispatch, manufacturing outsourcing, technical staffing, facility management",
        "competitor_keywords": ["staffing tech", "gig economy platform", "manufacturing staffing", "workforce management"],
    },
    "7191 JP": {
        "sector": "Insurance / Financial Agency",
        "products": "Insurance agency services, financial product distribution, insurance consulting, Entrust brand",
        "competitor_keywords": ["insurtech", "insurance marketplace", "digital insurance", "embedded insurance"],
    },

    # ============================================================
    # JAPANESE SHIPPING / TRANSPORT
    # ============================================================
    "9104 JP": {
        "sector": "Shipping",
        "products": "Container shipping (ONE alliance), dry bulk carriers, tankers, LNG carriers, car carriers, offshore",
        "competitor_keywords": ["digital freight", "shipping tech", "freight marketplace", "autonomous shipping", "green shipping"],
    },
    "9042 JP": {
        "sector": "Railway / Entertainment",
        "products": "Railway operations (Hankyu/Hanshin), real estate development, entertainment (Takarazuka), hotels, retail",
        "competitor_keywords": ["mobility as a service", "MaaS", "smart transit", "urban mobility", "ride sharing"],
    },
    "9022 JP": {
        "sector": "Railway",
        "products": "Tokaido Shinkansen (bullet train), conventional rail, bus transport, real estate, hotels, department stores",
        "competitor_keywords": ["high-speed rail", "MaaS", "mobility platform", "intercity transport", "autonomous transport"],
    },

    # ============================================================
    # JAPANESE MISCELLANEOUS INDUSTRIAL
    # ============================================================
    "6239 JP": {
        "sector": "Industrial Equipment",
        "products": "Water/oil well screens, internals for chemical plants/refineries, wedge wire screens, process equipment",
        "competitor_keywords": ["water treatment", "industrial filtration", "process equipment", "desalination tech"],
    },
    "5958 JP": {
        "sector": "Metal Products / Exterior Materials",
        "products": "Rain gutters, exterior wall materials, roofing materials, building envelope products",
        "competitor_keywords": ["building materials", "exterior cladding", "smart building materials", "prefab building components"],
    },
    "6061 JP": {
        "sector": "Engineering Services",
        "products": "Engineering consulting, transportation planning, environmental assessment, disaster prevention, urban planning",
        "competitor_keywords": ["engineering software", "BIM", "urban planning tech", "digital twin", "smart city"],
    },
    "5982 JP": {
        "sector": "Wire Products / Industrial",
        "products": "Steel wire products, springs, wire rope, metal fittings, precision parts",
        "competitor_keywords": ["wire products", "spring manufacturing", "precision parts", "advanced manufacturing"],
    },
    "6874 JP": {
        "sector": "Electronic Test Equipment",
        "products": "Electrical measuring instruments, power meters, power analyzers, insulation testers",
        "competitor_keywords": ["test and measurement", "power analyzer", "IoT monitoring", "smart grid testing"],
    },
    "8066 JP": {
        "sector": "Trading / Distribution",
        "products": "Chemical products trading, electronics materials, synthetic resins, building materials, green energy",
        "competitor_keywords": ["chemical distribution", "B2B marketplace", "chemical trading platform", "supply chain tech"],
    },
    "5071 JP": {
        "sector": "Staffing / Outsourcing",
        "products": "Construction staffing, manufacturing dispatch, technical staffing, facility management",
        "competitor_keywords": ["staffing platform", "construction staffing tech", "gig economy", "workforce management"],
    },
    "7521 JP": {
        "sector": "Auto Parts Retail",
        "products": "Automotive parts/accessories retail, car maintenance services, tire sales",
        "competitor_keywords": ["online auto parts", "auto parts marketplace", "car maintenance platform", "EV parts"],
    },
    "9672 JP": {
        "sector": "Horse Racing / Entertainment",
        "products": "Tokyo City Keiba (horse racing), race track operation, betting, leisure facilities",
        "competitor_keywords": ["online betting", "sports betting", "gambling tech", "digital wagering platform"],
    },
    "6675 JP": {
        "sector": "Telecom Equipment / Systems",
        "products": "Business phone systems, IP-PBX, networking equipment, security systems, IoT solutions",
        "competitor_keywords": ["cloud PBX", "UCaaS", "VoIP", "business communication platform", "IoT communication"],
    },
    "8074 JP": {
        "sector": "Industrial Trading",
        "products": "Industrial machinery distribution, bearings, tools, factory equipment, environmental systems",
        "competitor_keywords": ["industrial supply marketplace", "MRO ecommerce", "industrial IoT", "B2B procurement"],
    },
    "8052 JP": {
        "sector": "Industrial Distribution",
        "products": "Power transmission equipment (chains/belts), factory supplies, machinery parts, MRO distribution",
        "competitor_keywords": ["MRO ecommerce", "industrial supply marketplace", "B2B procurement", "smart maintenance"],
    },
    "8059 JP": {
        "sector": "Industrial Trading",
        "products": "Plant engineering, industrial machinery, electronic devices, automotive equipment, chemical products",
        "competitor_keywords": ["industrial marketplace", "B2B trading platform", "equipment as a service", "industrial IoT"],
    },
    "9960 JP": {
        "sector": "Industrial Trading / Electronics",
        "products": "Air conditioning equipment, electrical materials, information systems, industrial equipment distribution",
        "competitor_keywords": ["HVAC distribution", "building equipment marketplace", "smart HVAC", "energy management"],
    },
    "9273 JP": {
        "sector": "Electronics Distribution",
        "products": "Electronic components distribution, semiconductor distribution, device programming services",
        "competitor_keywords": ["electronic component marketplace", "semiconductor distribution", "IoT components", "supply chain tech"],
    },
    "9896 JP": {
        "sector": "Industrial Trading / Distribution",
        "products": "Automotive parts distribution, industrial supplies, housing equipment, logistics services",
        "competitor_keywords": ["auto parts marketplace", "industrial supply marketplace", "B2B distribution tech"],
    },
    "3321 JP": {
        "sector": "Electronics Distribution",
        "products": "Semiconductor devices, electronic components, FA equipment, optical communication devices",
        "competitor_keywords": ["semiconductor distribution", "electronic components marketplace", "IoT supply chain"],
    },
    "5715 JP": {
        "sector": "Mining / Metals / Machinery",
        "products": "Mining, metals smelting (copper/gold), industrial machinery, rockdrill, chemical products, real estate",
        "competitor_keywords": ["mining technology", "metals processing", "mining automation", "sustainable mining"],
    },
    "7821 JP": {
        "sector": "Industrial Materials / Geotextiles",
        "products": "Civil engineering materials, geotextiles, erosion control, slope protection, environmental products",
        "competitor_keywords": ["geotextile", "erosion control", "sustainable civil engineering", "green infrastructure"],
    },
    "255A JP": {
        "sector": "Technology / Recycling",
        "products": "Technology services, recycling business, environmental solutions",
        "competitor_keywords": ["recycling tech", "circular economy", "waste management tech", "environmental tech"],
    },
    "9632 JP": {
        "sector": "Building Maintenance / Services",
        "products": "Building maintenance, facility management, cleaning services, parking management, hotel operations",
        "competitor_keywords": ["facility management tech", "smart building maintenance", "property tech", "cleaning robotics"],
    },
    "9628 JP": {
        "sector": "Building Maintenance / Staffing",
        "products": "Building maintenance, security services, staffing, facility management, property management",
        "competitor_keywords": ["facility management tech", "smart building", "security tech", "cleaning robotics"],
    },
    "6040 JP": {
        "sector": "Tourism / Ski Resorts",
        "products": "Ski resort operations, tourism/leisure facilities, resort hotels, mountain tourism",
        "competitor_keywords": ["travel tech", "ski resort tech", "tourism platform", "outdoor recreation", "experience booking"],
    },
    "2685 JP": {
        "sector": "Restaurants / Retail",
        "products": "Point/restaurant chain, retail stores, food service, consumer brands",
        "competitor_keywords": ["restaurant tech", "food delivery", "ghost kitchen", "QSR technology", "food ordering platform"],
    },
}

# Apply profiles to the template
applied = 0
skipped = []
for ticker, profile_data in company_profiles.items():
    if ticker in profiles:
        profiles[ticker]["sector"] = profile_data["sector"]
        profiles[ticker]["products"] = profile_data["products"]
        profiles[ticker]["competitor_keywords"] = profile_data["competitor_keywords"]
        applied += 1
    else:
        skipped.append(ticker)

# Write the updated profiles
with open("holdings_competitive_profile.json", "w") as f:
    json.dump(profiles, f, indent=2)

# Count remaining unfilled
unfilled = [t for t, p in profiles.items() if not p.get("sector")]
print(f"Applied {applied} profiles")
if skipped:
    print(f"Skipped (not in holdings): {skipped}")
print(f"Remaining unfilled: {len(unfilled)}")
if unfilled:
    for t in unfilled:
        print(f"  {t}: {profiles[t]['name']}")
