from finance_tracker.services.categorisation.rules.base_rules import Rule

# Rules are evaluated top to bottom — more specific patterns first.
# category names must exactly match the categories master table.
# Add new rules here as you encounter unmatched transactions.

ICICI_RULES: list[Rule] = [

    # Income
    Rule(r"salary|payroll", "Salary", dr_cr="CR"),
    Rule(r"interest credit|int\.pd|interest paid", "Interest", dr_cr="CR"),
    Rule(r"dividend|div (payout|credit)", "Dividends", dr_cr="CR"),
    Rule(r"ACH / Ong.*gas|ACH / Oil.*gas|ACH / Ong", "Dividends", dr_cr="CR"),
    Rule(r"ACH / Nmdc|ACH / Coal India|ACH / Bel Int|ACH / Mazagon|ACH / Tpl Int|ACH / Sbi.*card int|ACH / Sun Tv", "Dividends", dr_cr="CR"),
    Rule(r"ACH / Indian Railway", "Dividends", dr_cr="CR"),
    Rule(r"IMPS /|NEFT /|Fund Transfer", "Other Income", dr_cr="CR"),
    Rule(r"FD Sweep", "Interest", dr_cr="CR"),

    # Food
    Rule(r"Swiggy|swiggy", "Food Delivery"),
    Rule(r"Zomato|zomato", "Food Delivery"),
    Rule(r"UPI / .*/ (vegetables|fruits|grocery|groceries|sabji|sabzi)", "Groceries"),
    Rule(r"Reliance S.*/ grocery|Reliance.*grocery", "Groceries"),
    Rule(r"UPI / .*/ (milk|dairy)", "Groceries"),
    Rule(r"UPI / .*/ (food|lunch|dinner|breakfast|snack|tiffin|thali)", "Dining Out"),
    Rule(r"UPI / .*/ (cafe|coffee|chai|tea)", "Cafe / Coffee"),
    Rule(r"UPI / .*/ (icecream|ice cream|sweets|mithai)", "Dining Out"),
    Rule(r"UPI / .*/ (drink|juice|cold drink)", "Dining Out"),

    # Transport
    Rule(r"UPI / .*/ (fuel|petrol|diesel)", "Fuel"),
    Rule(r"UPI / Shoffr|ola|uber|rapido", "Cab / Ola / Uber"),
    Rule(r"UPI / .*/ (auto|rickshaw|rikshaw)", "Auto / Rickshaw"),
    Rule(r"UPI / Vi /|ACH / Vodafoneid|UPI / Vodafoneid", "Internet / Broadband"),

    # Housing
    Rule(r"ACH / Racpc|home loan|housing loan", "Loan EMI"),
    Rule(r"UPI / .*/ (rent|house rent|room rent)", "Rent"),
    Rule(r"UPI / .*/ (electricity|bijli|mseb|bescom|torrent power)", "Electricity"),
    Rule(r"UPI / .*/ (water|jal board)", "Water"),
    Rule(r"UPI / .*/ (maintenance|society|society maintenance)", "Maintenance / Society"),
    Rule(r"internet|broadband|wifi|jio fiber|airtel fiber", "Internet / Broadband"),

    # Health & Insurance
    Rule(r"ACH / Sbi Life|ACH / Kotak Life|ACH / Tp Kotak|ACH / Lic|life insurance", "Insurance Premium"),
    Rule(r"ACH / Sbicard Int", "Insurance Premium"),
    Rule(r"UPI / .*/ (doctor|hospital|clinic|pharmacy|medicine|medical)", "Medicines"),
    Rule(r"UPI / Gym|gym|fitness|yoga", "Gym / Fitness"),

    # Shopping
    Rule(r"Amazon|Flipkart|Myntra|Meesho", "Amazon / Flipkart"),
    Rule(r"UPI / Reliance R|Reliance Retail|DMart|Big Bazaar", "Groceries"),
    Rule(r"UPI / .*/ (clothes|clothing|shirt|dress|shoes|footwear)", "Clothing"),
    Rule(r"UPI / .*/ (mobile|laptop|electronics|phone)", "Electronics"),
    Rule(r"UPI / .*/ (salon|haircut|parlour|beauty|spa)", "Personal Care"),
    Rule(r"UPI / .*/ (plant|plants|nursery|garden)", "Home Supplies"),
    Rule(r"UPI / .*/ (book|books)", "Books / Courses"),
    Rule(r"UPI / .*/ (xerox|print|photocopy)", "Books / Courses"),

    # Entertainment
    Rule(r"Netflix|Amazon Prime|Hotstar|Disney|Zee5|Sony Liv|JioCinema", "OTT Subscriptions"),
    Rule(r"Spotify|Gaana|JioSaavn|Apple Music|Youtube Premium", "OTT Subscriptions"),
    Rule(r"UPI / Google Pla|Google Play", "Games"),

    # Finance & Investments
    Rule(r"UPI / Cred Club|CRED", "Credit Card Payment"),
    Rule(r"ACH / Indian Clearing Corp", "Mutual Fund SIP"),
    Rule(r"NEFT /.*Mutual Fund|NEFT /.*Mf |bseindia.*clearing", "Mutual Fund SIP"),
    Rule(r"UPI Collect /|UPL /|remar", "Mutual Fund SIP"),
    Rule(r"ACH / Ong|ACH / Nmdc|ACH / Coal|ACH / Bel|ACH / Mazagon|ACH / Tpl|ACH / Sbi Life|ACH / Sun Tv|ACH / Indian Railway", "Dividends", dr_cr="CR"),
    Rule(r"UPI / Kabrawala|brokerage|Kotak.*brokerage", "Stock Purchase"),
    Rule(r"Direct Debit / Direct Tax|tax payment|income tax", "Tax Payment"),
    Rule(r"ACH / Tp Kotak Life|ACH / Kotak Life", "Insurance Premium"),

    # Transfers
    Rule(r"Cash Withdrawal", "Account Transfer", dr_cr="DR"),
    Rule(r"IMPS /|MMT/IMPS", "Account Transfer"),
    Rule(r"UPI / .*/ (upi|transfer|send|paid)", "UPI Transfer"),
    Rule(r"UPI / .*/ (ear piercing|piercing)", "Personal Care"),
    Rule(r"UPI / .*/ (lot|matlu|home thing|scrub)", "Home Supplies"),
]
