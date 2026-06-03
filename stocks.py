"""
stocks.py
---------
Master list of NSE-listed Indian stocks for the autocomplete dropdown.
Format: { "Company Name (Display)": "TICKER.NS" }
"""

STOCKS: dict[str, str] = {
    "Reliance Industries": "RELIANCE.NS",
    "Tata Consultancy Services (TCS)": "TCS.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "Infosys": "INFY.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "Hindustan Unilever (HUL)": "HINDUNILVR.NS",
    "State Bank of India (SBI)": "SBIN.NS",
    "Bharti Airtel": "BHARTIARTL.NS",
    "ITC": "ITC.NS",
    "Kotak Mahindra Bank": "KOTAKBANK.NS",
    "Larsen & Toubro (L&T)": "LT.NS",
    "Asian Paints": "ASIANPAINT.NS",
    "Axis Bank": "AXISBANK.NS",
    "Bajaj Finance": "BAJFINANCE.NS",
    "Maruti Suzuki": "MARUTI.NS",
    "HCL Technologies": "HCLTECH.NS",
    "Sun Pharmaceutical": "SUNPHARMA.NS",
    "Wipro": "WIPRO.NS",
    "UltraTech Cement": "ULTRACEMCO.NS",
    "Titan Company": "TITAN.NS",
    "Nestle India": "NESTLEIND.NS",
    "Power Grid Corporation": "POWERGRID.NS",
    "NTPC": "NTPC.NS",
    "Mahindra & Mahindra (M&M)": "M&M.NS",
    "Tech Mahindra": "TECHM.NS",
    "Bajaj Auto": "BAJAJ-AUTO.NS",
    "Tata Motors": "TATAMOTORS.NS",
    "Dr. Reddy's Laboratories": "DRREDDY.NS",
    "Cipla": "CIPLA.NS",
    "Adani Ports": "ADANIPORTS.NS",
    "Adani Enterprises": "ADANIENT.NS",
    "Adani Green Energy": "ADANIGREEN.NS",
    "Adani Power": "ADANIPOWER.NS",
    "Coal India": "COALINDIA.NS",
    "ONGC": "ONGC.NS",
    "Indian Oil Corporation (IOC)": "IOC.NS",
    "Bharat Petroleum (BPCL)": "BPCL.NS",
    "Hindustan Petroleum (HPCL)": "HPCL.NS",
    "Tata Steel": "TATASTEEL.NS",
    "JSW Steel": "JSWSTEEL.NS",
    "Hindalco Industries": "HINDALCO.NS",
    "Vedanta": "VEDL.NS",
    "Grasim Industries": "GRASIM.NS",
    "Shree Cement": "SHREECEM.NS",
    "ACC": "ACC.NS",
    "Ambuja Cements": "AMBUJACEM.NS",
    "Pidilite Industries": "PIDILITIND.NS",
    "Godrej Consumer Products": "GODREJCP.NS",
    "Dabur India": "DABUR.NS",
    "Marico": "MARICO.NS",
    "Colgate-Palmolive India": "COLPAL.NS",
    "Havells India": "HAVELLS.NS",
    "Voltas": "VOLTAS.NS",
    "Crompton Greaves Consumer": "CROMPTON.NS",
    "Dixon Technologies": "DIXON.NS",
    "Tata Power": "TATAPOWER.NS",
    "Torrent Power": "TORNTPOWER.NS",
    "NHPC": "NHPC.NS",
    "Indraprastha Gas (IGL)": "IGL.NS",
    "Petronet LNG": "PETRONET.NS",
    "Gail India": "GAIL.NS",
    "Hero MotoCorp": "HEROMOTOCO.NS",
    "Eicher Motors (Royal Enfield)": "EICHERMOT.NS",
    "Bajaj Finserv": "BAJAJFINSV.NS",
    "HDFC Life Insurance": "HDFCLIFE.NS",
    "SBI Life Insurance": "SBILIFE.NS",
    "ICICI Prudential Life": "ICICIPRULI.NS",
    "LIC of India": "LICI.NS",
    "Muthoot Finance": "MUTHOOTFIN.NS",
    "Cholamandalam Finance": "CHOLAFIN.NS",
    "Shriram Finance": "SHRIRAMFIN.NS",
    "SBI Cards": "SBICARD.NS",
    "HDFC AMC": "HDFCAMC.NS",
    "Nippon India AMC (NAM India)": "NAM-INDIA.NS",
    "Divi's Laboratories": "DIVISLAB.NS",
    "Biocon": "BIOCON.NS",
    "Apollo Hospitals": "APOLLOHOSP.NS",
    "Max Healthcare": "MAXHEALTH.NS",
    "Fortis Healthcare": "FORTIS.NS",
    "Lupin": "LUPIN.NS",
    "Aurobindo Pharma": "AUROPHARMA.NS",
    "Zydus Lifesciences": "ZYDUSLIFE.NS",
    "Abbott India": "ABBOTINDIA.NS",
    "Tata Consumer Products": "TATACONSUM.NS",
    "United Spirits (Diageo India)": "UNITDSPR.NS",
    "Varun Beverages (VBL)": "VBL.NS",
    "Zomato": "ZOMATO.NS",
    "Swiggy": "SWIGGY.NS",
    "Nykaa (FSN E-Commerce)": "NYKAA.NS",
    "PB Fintech (Policybazaar)": "POLICYBZR.NS",
    "One97 Communications (Paytm)": "PAYTM.NS",
    "Delhivery": "DELHIVERY.NS",
    "InterGlobe Aviation (IndiGo)": "INDIGO.NS",
    "Indian Railway Finance (IRFC)": "IRFC.NS",
    "Rail Vikas Nigam (RVNL)": "RVNL.NS",
    "IRCTC": "IRCTC.NS",
    "Bharat Electronics (BEL)": "BEL.NS",
    "HAL (Hindustan Aeronautics)": "HAL.NS",
    "Bharat Dynamics (BDL)": "BDL.NS",
    "Mazagon Dock": "MAZDOCK.NS",
    "Tata Elxsi": "TATAELXSI.NS",
    "Persistent Systems": "PERSISTENT.NS",
    "Mphasis": "MPHASIS.NS",
    "LTIMindtree": "LTIM.NS",
    "Coforge": "COFORGE.NS",
    "Oracle Financial Services (OFSS)": "OFSS.NS",
    "Hindustan Zinc": "HINDZINC.NS",
    "National Aluminium (NALCO)": "NATIONALUM.NS",
    "NMDC": "NMDC.NS",
    "Motherson Sumi (SAMIL)": "MOTHERSON.NS",
    "Bosch India": "BOSCHLTD.NS",
    "MRF Tyres": "MRF.NS",
    "Apollo Tyres": "APOLLOTYRE.NS",
    "Page Industries (Jockey)": "PAGEIND.NS",
    "Trent (Westside / Zudio)": "TRENT.NS",
    "Avenue Supermarts (DMart)": "DMART.NS",
    "Jubilant Foodworks (Domino's)": "JUBLFOOD.NS",
    "Info Edge (Naukri / 99acres)": "NAUKRI.NS",
    "Just Dial": "JUSTDIAL.NS",
    "Indiamart Intermesh": "INDIAMART.NS",
}

SORTED_LABELS: list[str] = sorted(STOCKS.keys())

# Reverse lookup: ticker → display name
TICKER_TO_NAME: dict[str, str] = {v: k for k, v in STOCKS.items()}

# ── Industry-level peer groups (yfinance industry strings) ────────────────
INDUSTRY_PEERS: dict[str, list[str]] = {
    # IT / Technology
    "Information Technology Services": [
        "TCS.NS","INFY.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS",
        "LTIM.NS","MPHASIS.NS","COFORGE.NS","PERSISTENT.NS","TATAELXSI.NS","OFSS.NS",
    ],
    "Software - Application": [
        "TCS.NS","INFY.NS","WIPRO.NS","HCLTECH.NS","LTIM.NS","OFSS.NS",
    ],
    # Banking
    "Banks - Regional": [
        "HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","KOTAKBANK.NS","AXISBANK.NS",
    ],
    "Banks - Diversified": [
        "HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","KOTAKBANK.NS","AXISBANK.NS",
    ],
    # NBFCs / Lending
    "Credit Services": [
        "BAJFINANCE.NS","BAJAJFINSV.NS","MUTHOOTFIN.NS","CHOLAFIN.NS",
        "SHRIRAMFIN.NS","SBICARD.NS","IRFC.NS",
    ],
    # Insurance
    "Insurance - Life": [
        "HDFCLIFE.NS","SBILIFE.NS","ICICIPRULI.NS","LICI.NS",
    ],
    "Insurance - Diversified": [
        "HDFCLIFE.NS","SBILIFE.NS","ICICIPRULI.NS","LICI.NS","POLICYBZR.NS",
    ],
    # Asset Management
    "Asset Management": [
        "HDFCAMC.NS","NAM-INDIA.NS",
    ],
    # Pharma
    "Drug Manufacturers - Specialty & Generic": [
        "SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","LUPIN.NS",
        "AUROPHARMA.NS","ZYDUSLIFE.NS","ABBOTINDIA.NS","DIVISLAB.NS","BIOCON.NS",
    ],
    "Drug Manufacturers - General": [
        "SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","LUPIN.NS",
        "AUROPHARMA.NS","ZYDUSLIFE.NS","DIVISLAB.NS","BIOCON.NS",
    ],
    # Hospitals
    "Medical Care Facilities": [
        "APOLLOHOSP.NS","MAXHEALTH.NS","FORTIS.NS",
    ],
    # Auto OEMs
    "Auto Manufacturers": [
        "MARUTI.NS","TATAMOTORS.NS","M&M.NS","HEROMOTOCO.NS","BAJAJ-AUTO.NS","EICHERMOT.NS",
    ],
    # Auto Components
    "Auto Parts": [
        "BOSCHLTD.NS","APOLLOTYRE.NS","MOTHERSON.NS","MRF.NS",
    ],
    # FMCG / Personal Care
    "Household & Personal Products": [
        "HINDUNILVR.NS","GODREJCP.NS","MARICO.NS","DABUR.NS","COLPAL.NS",
    ],
    # Packaged Food / Beverages
    "Packaged Foods": [
        "NESTLEIND.NS","TATACONSUM.NS","VBL.NS","ITC.NS",
    ],
    "Beverages - Non-Alcoholic": [
        "VBL.NS","NESTLEIND.NS","TATACONSUM.NS",
    ],
    # Tobacco — group with broader FMCG for useful comparison
    "Tobacco": [
        "ITC.NS","HINDUNILVR.NS","DABUR.NS","MARICO.NS","TATACONSUM.NS",
    ],
    # Retail
    "Discount Stores": [
        "DMART.NS","TRENT.NS",
    ],
    "Luxury Goods": [
        "TITAN.NS","PAGEIND.NS","TRENT.NS",
    ],
    "Apparel Retail": [
        "TRENT.NS","PAGEIND.NS","TITAN.NS",
    ],
    "Apparel Manufacturing": [
        "PAGEIND.NS","TRENT.NS",
    ],
    # Food Service
    "Restaurants": [
        "JUBLFOOD.NS","ZOMATO.NS","SWIGGY.NS",
    ],
    # Travel / Transport
    "Travel Services": [
        "IRCTC.NS","INDIGO.NS",
    ],
    "Airlines": [
        "INDIGO.NS","IRCTC.NS",
    ],
    # Metals
    "Steel": [
        "TATASTEEL.NS","JSWSTEEL.NS",
    ],
    "Aluminum": [
        "HINDALCO.NS","VEDL.NS","NATIONALUM.NS",
    ],
    "Other Industrial Metals & Mining": [
        "VEDL.NS","HINDZINC.NS","NMDC.NS","NATIONALUM.NS","HINDALCO.NS",
    ],
    # Cement / Building Materials
    "Building Materials": [
        "ULTRACEMCO.NS","SHREECEM.NS","ACC.NS","AMBUJACEM.NS","GRASIM.NS",
    ],
    # Chemicals / Paints
    "Specialty Chemicals": [
        "ASIANPAINT.NS","PIDILITIND.NS",
    ],
    # Oil & Gas
    "Oil & Gas Refining & Marketing": [
        "RELIANCE.NS","IOC.NS","BPCL.NS","HPCL.NS",
    ],
    "Oil & Gas Integrated": [
        "ONGC.NS","RELIANCE.NS","GAIL.NS",
    ],
    "Oil & Gas E&P": [
        "ONGC.NS","RELIANCE.NS",
    ],
    "Oil & Gas Midstream": [
        "GAIL.NS","PETRONET.NS","IGL.NS",
    ],
    # Coal / Mining
    "Thermal Coal": [
        "COALINDIA.NS","ADANIENT.NS",
    ],
    # Power / Utilities
    "Utilities - Regulated Electric": [
        "NTPC.NS","POWERGRID.NS","TATAPOWER.NS","TORNTPOWER.NS","NHPC.NS","ADANIPOWER.NS",
    ],
    "Utilities - Renewable": [
        "ADANIGREEN.NS","TATAPOWER.NS","NTPC.NS","NHPC.NS",
    ],
    "Utilities - Regulated Gas": [
        "GAIL.NS","IGL.NS","PETRONET.NS",
    ],
    "Utilities - Independent Power Producers": [
        "TATAPOWER.NS","TORNTPOWER.NS","ADANIPOWER.NS","NTPC.NS",
    ],
    # Defence
    "Aerospace & Defense": [
        "BEL.NS","HAL.NS","BDL.NS","MAZDOCK.NS",
    ],
    # Engineering & Infrastructure
    "Engineering & Construction": [
        "LT.NS","RVNL.NS","ADANIPORTS.NS",
    ],
    "Infrastructure Operations": [
        "ADANIPORTS.NS","LT.NS","RVNL.NS",
    ],
    # Telecom
    "Telecom Services": [
        "BHARTIARTL.NS",
    ],
    # Internet / Digital Media
    "Internet Content & Information": [
        "NAUKRI.NS","JUSTDIAL.NS","INDIAMART.NS","NYKAA.NS","POLICYBZR.NS","PAYTM.NS",
    ],
    "Internet Retail": [
        "NYKAA.NS","DMART.NS","TRENT.NS",
    ],
    # Logistics
    "Integrated Freight & Logistics": [
        "DELHIVERY.NS","ADANIPORTS.NS",
    ],
    "Marine Shipping": [
        "ADANIPORTS.NS","MAZDOCK.NS",
    ],
}

# ── Sector-level peer groups (broader fallback) ───────────────────────────
SECTOR_PEERS: dict[str, list[str]] = {
    "Technology": [
        "TCS.NS","INFY.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS",
        "LTIM.NS","MPHASIS.NS","COFORGE.NS","PERSISTENT.NS","TATAELXSI.NS","OFSS.NS",
    ],
    "Financial Services": [
        "HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","KOTAKBANK.NS","AXISBANK.NS",
        "BAJFINANCE.NS","BAJAJFINSV.NS","MUTHOOTFIN.NS","CHOLAFIN.NS","SHRIRAMFIN.NS",
        "SBICARD.NS","HDFCLIFE.NS","SBILIFE.NS","ICICIPRULI.NS","HDFCAMC.NS",
    ],
    "Healthcare": [
        "SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","LUPIN.NS","AUROPHARMA.NS",
        "ZYDUSLIFE.NS","DIVISLAB.NS","BIOCON.NS","APOLLOHOSP.NS","MAXHEALTH.NS","FORTIS.NS",
    ],
    "Consumer Cyclical": [
        "MARUTI.NS","TATAMOTORS.NS","M&M.NS","HEROMOTOCO.NS","BAJAJ-AUTO.NS","EICHERMOT.NS",
        "TITAN.NS","TRENT.NS","PAGEIND.NS","DMART.NS","JUBLFOOD.NS",
        "BOSCHLTD.NS","APOLLOTYRE.NS","MRF.NS",
    ],
    "Consumer Defensive": [
        "HINDUNILVR.NS","ITC.NS","NESTLEIND.NS","TATACONSUM.NS","DABUR.NS",
        "MARICO.NS","COLPAL.NS","GODREJCP.NS","VBL.NS","UNITDSPR.NS",
    ],
    "Energy": [
        "RELIANCE.NS","ONGC.NS","IOC.NS","BPCL.NS","HPCL.NS","COALINDIA.NS","ADANIENT.NS",
    ],
    "Utilities": [
        "NTPC.NS","POWERGRID.NS","TATAPOWER.NS","TORNTPOWER.NS","NHPC.NS",
        "ADANIGREEN.NS","ADANIPOWER.NS","GAIL.NS","IGL.NS","PETRONET.NS",
    ],
    "Basic Materials": [
        "TATASTEEL.NS","JSWSTEEL.NS","HINDALCO.NS","VEDL.NS","HINDZINC.NS","NMDC.NS",
        "NATIONALUM.NS","ULTRACEMCO.NS","SHREECEM.NS","ACC.NS","AMBUJACEM.NS",
        "ASIANPAINT.NS","PIDILITIND.NS","GRASIM.NS",
    ],
    "Industrials": [
        "LT.NS","BEL.NS","HAL.NS","BDL.NS","MAZDOCK.NS","RVNL.NS",
        "INDIGO.NS","ADANIPORTS.NS","DELHIVERY.NS",
    ],
    "Communication Services": [
        "BHARTIARTL.NS","NAUKRI.NS","JUSTDIAL.NS","INDIAMART.NS",
        "NYKAA.NS","POLICYBZR.NS","PAYTM.NS",
    ],
}
