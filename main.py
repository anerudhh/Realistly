import re
import json
from areas import BENGALURU_AREAS
from patterns import RENT_PATTERNS, SALE_PATTERNS, REQ_PATTERNS

GENERIC_PHRASES = set([
    'for rent', 'for sale', 'for lease', 'rent', 'sale', 'lease', 'to let', 'available', 'requirement', 'required', 'needed', 'looking for', 'need', 'wanted', 'want', 'flat for rent', 'apartment for rent', 'house for rent', 'villa for rent', 'shop for rent', 'warehouse for rent', 'office for rent', 'space for rent', 'open for rent', 'for rental', 'commercial space for rent', 'guest house', 'paying guest', 'pg', 'rental', 'rent:', 'sale:', 'lease:'
])

def parse_multiline_messages(file_path):
    pattern = r'^\[[^\]]+\]\s+(.*?):\s+(.*)'
    messages = []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    current_sender = None
    current_message = []
    for line in lines:
        line = line.rstrip()
        m = re.match(pattern, line)
        if m:
            if current_sender and current_message:
                messages.append({
                    "sender": current_sender,
                    "message": " ".join(current_message).strip()
                })
            raw_sender = m.group(1).strip()
            sender = re.sub(r'^[^\w]+', '', raw_sender)
            current_sender = sender
            current_message = [m.group(2).strip()]
        else:
            if current_message is not None:
                current_message.append(line)
    if current_sender and current_message:
        messages.append({
            "sender": current_sender,
            "message": " ".join(current_message).strip()
        })
    return messages

def is_irrelevant_message(msg):
    msg_low = msg.lower().strip()
    msg_clean = re.sub(r'[^\w\s]', '', msg_low).strip()
    sys_patterns = [
        'joined using this group', 'added you', 'left', 'created this group',
        'was added', 'was removed', 'changed the subject', 'pinned a message',
        'turned on disappearing messages', 'turned off disappearing messages',
        'changed this group', 'changed the group', 'changed the icon',
        'changed the group description', 'changed the group settings',
        'you deleted this message', 'this message was deleted', 'video omitted',
        'photo omitted', 'image omitted', 'sticker omitted', 'document omitted',
        'pdf omitted', 'file omitted', 'you deleted this message as admin',
        'this message was edited',
        "you're now an admin", 'you are now an admin', 'now an admin', 'is now an admin', 'made you an admin', 'made admin'
    ]
    for p in sys_patterns:
        if p in msg_low:
            return True
    # WhatsApp encryption/system messages
    if "messages and calls are end-to-end encrypted" in msg_low:
        return True
    if "follow this link to join my whatsapp group" in msg_low:
        return True
    if re.match(r'^https?://', msg_low):  # Only a link
        return True
    # Greetings: match at start or end, allow for emojis and "all" and common group greetings
    greetings = [
        r'^(hi|hello|hey|dear|greetings|good morning|good afternoon|good evening|namaste|thanks|thank you)[\s\W]*(everyone|all|guys|friends)?[\s\W]*$',
        r'^[\s\W]*(hi|hello|hey|dear|greetings|good morning|good afternoon|good evening|namaste|thanks|thank you)[\s\W]*(everyone|all|guys|friends)?[\s\W]*$',
        r'^(hi|hello|hey|dear|greetings)[\s\W]+(everyone|all|guys|friends)[\s\W]*$',
        r'^(everyone|all|guys|friends)[\s\W]+(hi|hello|hey|dear|greetings)[\s\W]*$'
    ]
    for g in greetings:
        if re.match(g, msg_clean):
            return True
    # Only emojis or too short and not a property message
    if len(msg_clean) < 5 and not re.search(r'\d', msg_clean):
        return True
    # Only attachment
    if re.match(r'^<attached:', msg_low):
        return True
    return False

def detect_listing_type(msg):
    msg_low = msg.lower()
    rent = any(re.search(p, msg_low) for p in RENT_PATTERNS)
    sale = any(re.search(p, msg_low) for p in SALE_PATTERNS)
    req = any(re.search(p, msg_low) for p in REQ_PATTERNS)
    if rent and sale:
        rent_idx = min([msg_low.find(k.replace(r'\b','').strip()) for k in RENT_PATTERNS if k.replace(r'\b','').strip() in msg_low] + [len(msg_low)])
        sale_idx = min([msg_low.find(k.replace(r'\b','').strip()) for k in SALE_PATTERNS if k.replace(r'\b','').strip() in msg_low] + [len(msg_low)])
        return "rent" if rent_idx < sale_idx else "sell"
    if rent:
        return "rent"
    if sale:
        return "sell"
    if req:
        if 'rent' in msg_low or 'lease' in msg_low:
            return "rent_requirement"
        if 'sale' in msg_low or 'buy' in msg_low or 'purchase' in msg_low or 'outrate' in msg_low:
            return "sell_requirement"
        return "requirement"
    return "other"

def extract_location(msg):
    msg_low = msg.lower()
    # 1. Try to match all known areas (case-insensitive, allow partial and multi-word matches)
    found_areas = []
    for area in BENGALURU_AREAS:
        area_low = area.lower()
        # Use word boundaries for single-word areas, substring for multi-word
        if ' ' in area_low:
            if area_low in msg_low:
                found_areas.append((msg_low.find(area_low), area))
        else:
            for m in re.finditer(r'\b' + re.escape(area_low) + r'\b', msg_low):
                found_areas.append((m.start(), area))
    if found_areas:
        found_areas.sort()
        # Capitalize each word in area name
        loc = ' '.join([w.capitalize() for w in found_areas[0][1].split()])
        if loc.strip().lower() not in GENERIC_PHRASES:
            return loc
    # 2. Fallback: try to find the best substring match (fuzzy, but simple)
    best_area = None
    best_idx = len(msg_low)
    for area in BENGALURU_AREAS:
        area_low = area.lower()
        idx = msg_low.find(area_low)
        if idx != -1 and idx < best_idx:
            best_idx = idx
            best_area = area
    if best_area:
        loc = ' '.join([w.capitalize() for w in best_area.split()])
        if loc.strip().lower() not in GENERIC_PHRASES:
            return loc
    # 3. Fallback: regex after location:, in, at, near (first 2-3 words only)
    m = re.search(r'(?:location:|in|at|near)\s*([A-Za-z0-9\s\-]+)', msg, re.IGNORECASE)
    if m:
        loc = m.group(1).strip()
        loc = ' '.join(loc.split()[:3])
        loc = re.split(r'[\.,;:\n]', loc)[0]
        loc = re.sub(r'\s+\d+.*$', '', loc)
        if loc and loc.strip().lower() not in GENERIC_PHRASES:
            return loc.title()
    return None

def extract_price(msg):
    # Only extract numbers after price/rent keywords, handle lakh/cr/k/L
    price = None
    price_patterns = [
        r'(rent|price|rs|₹|rental|asking|lakhs?|cr|crore)[^\d]{0,10}([\d,\.]+)',  # e.g. Rent: 25000, Price: 1.2 cr
        r'([\d,\.]+)\s*(lakhs?|cr|crore|l|k)',  # e.g. 1.2 cr, 80 lakhs, 80L, 80K
        r'₹\s?([\d,\.]+)'
    ]
    for pat in price_patterns:
        for m in re.finditer(pat, msg, re.IGNORECASE):
            num_str = m.group(2) if len(m.groups()) > 1 else m.group(1)
            num = re.sub(r'[^\d.]', '', num_str)
            if not num:
                continue
            val = None
            if 'cr' in m.group(0).lower() or 'crore' in m.group(0).lower():
                try:
                    val = float(num) * 1e7
                except:
                    continue
            elif 'lakh' in m.group(0).lower() or 'l' in m.group(0).lower():
                try:
                    val = float(num) * 1e5
                except:
                    continue
            elif 'k' in m.group(0).lower():
                try:
                    val = float(num) * 1e3
                except:
                    continue
            else:
                try:
                    val = float(num)
                except:
                    continue
            if val and val >= 10000:
                price = int(val)
                break
        if price:
            break
    return price

def extract_property_type(msg):
    # e.g. "3 BHK", "3.5 BHK", "4bhk", "studio", "villa"
    m = re.search(r'\b([1-9](?:\.[05])?\s?BHK|studio|villa|bungalow)\b', msg, re.IGNORECASE)
    if m:
        return m.group(1).upper().replace(" ", "")
    return None

def extract_dimensions(msg):
    # e.g. "1500 sqft", "2 acres", "30x40", "1200 sft", "2400 Sq.ft", "80,000 sq ft"
    matches = []
    # 1. Match numbers with optional commas and spaces (e.g., 80,000 sq ft, 20000 sq ft)
    for m in re.finditer(r'\b([\d,]+)\s?(sq\.? ?ft|sft|sqft|sq ft|acres?|guntas?)\b', msg, re.IGNORECASE):
        num = m.group(1).replace(',', '').strip()
        try:
            val = int(num)
        except ValueError:
            continue
        # Format with commas for readability
        formatted = f"{val:,} {m.group(2).replace('.', '').replace(' ', '')}"
        matches.append((val, formatted))
    # 2. Match 30x40, 40x60, etc.
    for m in re.finditer(r'\b\d{1,3}\s?x\s?\d{1,3}\b', msg):
        matches.append((0, m.group()))
    # Return the largest dimension (by value) if any
    if matches:
        matches.sort(reverse=True)
        return matches[0][1]
    return None

def extract_phone(msg):
    # 10-digit or +91-xxxxxxxxxx
    m = re.search(r'\b\d{10}\b', msg)
    if m:
        return m.group()
    m = re.search(r'\+91[-\s]?(\d{10})\b', msg)
    if m:
        return m.group(1)
    return None

def extract_furnishing(msg):
    m = re.search(r'\b(fully|semi|un)?\s*furnished\b', msg, re.IGNORECASE)
    if m:
        return m.group().strip().lower()
    return None

def extract_floor(msg):
    m = re.search(r'\b(?:ground|lower|middle|upper|higher|\d{1,2})(?:st|nd|rd|th)?\s+floor\b', msg, re.IGNORECASE)
    if m:
        return m.group().strip().lower()
    return None

def extract_facing(msg):
    m = re.search(r'\b(north|south|east|west)\s*facing\b', msg, re.IGNORECASE)
    if m:
        return m.group().strip().lower()
    return None

def extract_property_name(msg):
    msg_low = msg.lower()
    # 1. Project/complex name after 'in' or 'at' (e.g., 'in Mahaveer Maple')
    m = re.search(r'(?:in|at)\s+([A-Za-z0-9&\-_ ]{3,40})', msg, re.IGNORECASE)
    if m:
        name = ' '.join(m.group(1).strip().split()[:3])
        if name.strip().lower() not in GENERIC_PHRASES:
            return name.strip()
    # 2. After 'for rent/sale in/at', extract next 1-3 words
    m = re.search(r'for (?:rent|sale)[^\w]*(?:in|at)\s+([A-Za-z0-9&\-_ ]{3,40})', msg, re.IGNORECASE)
    if m:
        name = ' '.join(m.group(1).strip().split()[:3])
        if name.strip().lower() not in GENERIC_PHRASES:
            return name.strip()
    # 3. Before BHK, up to 3 words
    m = re.search(r'([A-Za-z0-9&\-_ ]{1,40})\s+([1-9](?:\.[05])?\s?BHK)', msg, re.IGNORECASE)
    if m:
        before = m.group(1).strip()
        name = ' '.join(before.split()[-3:])
        if name.strip().lower() not in GENERIC_PHRASES:
            return name.strip()
    return None

def extract_info(msg):
    info = dict.fromkeys([
        'property_name','property_type','location','dimensions',
        'rent_or_price','phone','furnishing','floor','facing'
    ], None)
    info['property_type'] = extract_property_type(msg)
    info['dimensions'] = extract_dimensions(msg)
    info['rent_or_price'] = extract_price(msg)
    info['phone'] = extract_phone(msg)
    info['furnishing'] = extract_furnishing(msg)
    info['floor'] = extract_floor(msg)
    info['facing'] = extract_facing(msg)
    info['property_name'] = extract_property_name(msg)
    info['location'] = extract_location(msg)
    return info

def build_json(sender, message):
    info = extract_info(message)
    status = "complete" if info['property_type'] and info['location'] else "needs_review"
    listing_type = detect_listing_type(message)
    return {
        "sender": sender,
        "message": message,
        "listing_type": listing_type,
        **info,
        "status": status
    }

def save_to_json(records, path='rentals_cleaned.json'):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

def main():
    parsed = parse_multiline_messages('chat.txt')
    print(f"\n📨 Parsed messages: {len(parsed)}")
    filtered = []
    for msg in parsed:
        if not is_irrelevant_message(msg['message']):
            filtered.append(build_json(msg['sender'], msg['message']))
    print(f"✅ Saved {len(filtered)} relevant property listings to rentals_cleaned.json")
    if filtered:
        print("\n Sample:\n", json.dumps(filtered[:2], indent=2, ensure_ascii=False))
    save_to_json(filtered)

if __name__ == "__main__":
    main()