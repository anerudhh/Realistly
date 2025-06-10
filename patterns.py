RENT_PATTERNS = [
    r'\bfor rent\b', r'\bfor lease\b', r'\brent\b', r'\blease\b', r'\brental\b',
    r'\bavailable for rent\b', r'\bto let\b', r'\bpg\b', r'\bpaying guest\b',
    r'\bcommercial space for rent\b', r'\bguest house\b', r'\bapartment for rent\b',
    r'\bflat for rent\b', r'\bhouse for rent\b', r'\bvilla for rent\b', r'\bshop for rent\b',
    r'\bwarehouse for rent\b', r'\boffice for rent\b', r'\bspace for rent\b',
    r'\bopen for rent\b', r'\bfor rental\b'
]
SALE_PATTERNS = [
    r'\bfor sale\b', r'\bsale\b', r'\bsite for sale\b', r'\bplots?\b', r'\bplot for sale\b',
    r'\bbuy\b', r'\bpurchase\b', r'\bout rate\b', r'\bout-rate\b', r'\bresale\b',
    r'\bavailable for sale\b', r'\bsite sale\b', r'\bapartment for sale\b', r'\bflat for sale\b',
    r'\bhouse for sale\b', r'\bvilla for sale\b', r'\bshop for sale\b', r'\bwarehouse for sale\b',
    r'\boffice for sale\b', r'\bspace for sale\b'
]
REQ_PATTERNS = [
    r'\brequired\b', r'\brequirement\b', r'\bneeded\b', r'\blooking for\b', r'\bneed\b', r'\bwanted\b', r'\bwant\b'
]