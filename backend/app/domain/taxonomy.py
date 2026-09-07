import re
from typing import Dict, Any, List, Optional, Tuple

INITIAL_TOP_LEVEL_CATEGORIES = [
    "Electronics",
    "Fashion",
    "Beauty & Personal Care",
    "Home & Living",
    "Health & Wellness",
    "Sports & Fitness",
    "Toys & Collectibles",
    "Automotive",
    "Groceries & Food",
    "Baby & Kids",
    "Books & Media",
    "Pet Supplies",
    "Jewelry & Accessories",
    "Tools & Hardware",
    "Office & Stationery",
    "Industrial & Business",
    "Other",
    "Unknown"
]

CENTRAL_TAXONOMY_TREE = [
    {
        "name": "Electronics",
        "slug": "electronics",
        "description": "Consumer electronics, computing, audio, mobile, and digital hardware",
        "subcategories": [
            {
                "name": "Audio",
                "slug": "electronics-audio",
                "product_types": [
                    {
                        "name": "Wireless Earbuds",
                        "slug": "wireless-earbuds",
                        "keywords": ["earbuds", "tws", "airpods", "wireless earbuds", "bluetooth earphones", "in-ear true wireless"],
                        "path": ["Electronics", "Audio", "Headphones & Earbuds", "Wireless Earbuds"]
                    },
                    {
                        "name": "Over-Ear Headphones",
                        "slug": "over-ear-headphones",
                        "keywords": ["headphone", "headphones", "over-ear", "headset", "studio monitor", "noise cancelling headphone"],
                        "path": ["Electronics", "Audio", "Headphones & Earbuds", "Over-Ear Headphones"]
                    },
                    {
                        "name": "Bluetooth Speakers",
                        "slug": "bluetooth-speakers",
                        "keywords": ["speaker", "bluetooth speaker", "soundbar", "subwoofer", "portable speaker"],
                        "path": ["Electronics", "Audio", "Speakers", "Bluetooth Speakers"]
                    }
                ]
            },
            {
                "name": "Mobile Accessories",
                "slug": "electronics-mobile-accessories",
                "product_types": [
                    {
                        "name": "Wireless Chargers",
                        "slug": "wireless-chargers",
                        "keywords": ["wireless charger", "magsafe", "charging pad", "fast charger", "qi charger", "charging stand", "magnetic charger"],
                        "path": ["Electronics", "Mobile Accessories", "Charging & Power", "Wireless Chargers"]
                    },
                    {
                        "name": "Power Banks",
                        "slug": "power-banks",
                        "keywords": ["power bank", "powerbank", "portable charger", "battery pack", "10000mah", "20000mah"],
                        "path": ["Electronics", "Mobile Accessories", "Charging & Power", "Power Banks"]
                    },
                    {
                        "name": "Phone Cases & Protection",
                        "slug": "phone-cases",
                        "keywords": ["phone case", "silicone case", "tempered glass", "screen protector", "cover case", "shockproof cover"],
                        "path": ["Electronics", "Mobile Accessories", "Cases & Protectors", "Phone Cases & Protection"]
                    }
                ]
            },
            {
                "name": "Computer Accessories",
                "slug": "electronics-computer-accessories",
                "product_types": [
                    {
                        "name": "Gaming Keyboard",
                        "slug": "gaming-keyboard",
                        "keywords": ["mechanical keyboard", "gaming keyboard", "rgb keyboard", "wireless keyboard", "keycaps", "keychron"],
                        "path": ["Electronics", "Computer Accessories", "Keyboards & Mice", "Gaming Keyboard"]
                    },
                    {
                        "name": "Gaming Mouse",
                        "slug": "gaming-mouse",
                        "keywords": ["gaming mouse", "wireless mouse", "optical mouse", "ergonomic mouse", "logitech mouse"],
                        "path": ["Electronics", "Computer Accessories", "Keyboards & Mice", "Gaming Mouse"]
                    },
                    {
                        "name": "Monitors & Displays",
                        "slug": "monitors-displays",
                        "keywords": ["monitor", "gaming monitor", "ips display", "4k monitor", "curved screen", "144hz", "240hz"],
                        "path": ["Electronics", "Computer Accessories", "Displays", "Monitors & Displays"]
                    }
                ]
            },
            {
                "name": "Smart Home & IoT",
                "slug": "electronics-smart-home",
                "product_types": [
                    {
                        "name": "Smart Security Cameras",
                        "slug": "smart-security-cameras",
                        "keywords": ["security camera", "cctv", "ip camera", "wifi camera", "smart doorbell", "surveillance"],
                        "path": ["Electronics", "Smart Home & IoT", "Security & Surveillance", "Smart Security Cameras"]
                    },
                    {
                        "name": "Smart Bulbs & Lighting",
                        "slug": "smart-bulbs-lighting",
                        "keywords": ["smart bulb", "rgb bulb", "smart led", "ambient light", "led light strip", "smart plug"],
                        "path": ["Electronics", "Smart Home & IoT", "Smart Lighting", "Smart Bulbs & Lighting"]
                    }
                ]
            },
            {
                "name": "Wearables",
                "slug": "electronics-wearables",
                "product_types": [
                    {
                        "name": "Smartwatches",
                        "slug": "smartwatches",
                        "keywords": ["smartwatch", "smart watch", "fitness tracker", "apple watch", "galaxy watch", "fitness band"],
                        "path": ["Electronics", "Wearables", "Smart Watches & Trackers", "Smartwatches"]
                    }
                ]
            }
        ]
    },
    {
        "name": "Fashion",
        "slug": "fashion",
        "description": "Apparel, clothing, footwear, activewear, and outerwear",
        "subcategories": [
            {
                "name": "Men's Clothing",
                "slug": "fashion-mens-clothing",
                "product_types": [
                    {
                        "name": "T-Shirts",
                        "slug": "mens-t-shirts",
                        "keywords": ["t-shirt", "tshirt", "tee", "cotton t-shirt", "graphic tee", "men tee", "oversized t-shirt"],
                        "path": ["Fashion", "Men's Clothing", "Tops", "T-Shirts"]
                    },
                    {
                        "name": "Hoodies & Sweatshirts",
                        "slug": "mens-hoodies",
                        "keywords": ["hoodie", "sweatshirt", "fleece hoodie", "pullover", "zip hoodie", "streetwear hoodie"],
                        "path": ["Fashion", "Men's Clothing", "Outerwear", "Hoodies & Sweatshirts"]
                    },
                    {
                        "name": "Jeans & Trousers",
                        "slug": "mens-jeans-trousers",
                        "keywords": ["jeans", "denim", "trousers", "chinos", "cargo pants", "joggers", "sweatpants"],
                        "path": ["Fashion", "Men's Clothing", "Bottoms", "Jeans & Trousers"]
                    }
                ]
            },
            {
                "name": "Women's Clothing",
                "slug": "fashion-womens-clothing",
                "product_types": [
                    {
                        "name": "Dresses",
                        "slug": "womens-dresses",
                        "keywords": ["dress", "maxi dress", "midi dress", "cocktail dress", "floral dress", "kurti", "lawn suit"],
                        "path": ["Fashion", "Women's Clothing", "Dresses & Suits", "Dresses"]
                    },
                    {
                        "name": "Women Tops & Blouses",
                        "slug": "womens-tops",
                        "keywords": ["blouse", "women top", "crop top", "tunic", "camisole", "shirt women"],
                        "path": ["Fashion", "Women's Clothing", "Tops", "Women Tops & Blouses"]
                    }
                ]
            },
            {
                "name": "Footwear",
                "slug": "fashion-footwear",
                "product_types": [
                    {
                        "name": "Sneakers & Athletic Shoes",
                        "slug": "sneakers-athletic-shoes",
                        "keywords": ["sneakers", "running shoes", "trainer shoes", "athletic footwear", "air jordan", "tenis shoes"],
                        "path": ["Fashion", "Footwear", "Athletic", "Sneakers & Athletic Shoes"]
                    },
                    {
                        "name": "Casual Shoes & Loafers",
                        "slug": "casual-shoes-loafers",
                        "keywords": ["loafers", "casual shoes", "sandals", "slippers", "slides", "leather shoes", "boots"],
                        "path": ["Fashion", "Footwear", "Casual", "Casual Shoes & Loafers"]
                    }
                ]
            }
        ]
    },
    {
        "name": "Beauty & Personal Care",
        "slug": "beauty-personal-care",
        "description": "Skincare, haircare, makeup, fragrances, and personal grooming",
        "subcategories": [
            {
                "name": "Skincare",
                "slug": "beauty-skincare",
                "product_types": [
                    {
                        "name": "Face Serum",
                        "slug": "face-serum",
                        "keywords": ["serum", "face serum", "vitamin c serum", "hyaluronic acid", "niacinamide", "retinol serum", "collagen serum"],
                        "path": ["Beauty & Personal Care", "Skincare", "Face Treatments", "Face Serum"]
                    },
                    {
                        "name": "Moisturizers & Creams",
                        "slug": "moisturizers-creams",
                        "keywords": ["moisturizer", "day cream", "night cream", "lotion", "hydrating gel", "face cream", "ceramide"],
                        "path": ["Beauty & Personal Care", "Skincare", "Moisturizers", "Moisturizers & Creams"]
                    },
                    {
                        "name": "Sunscreens",
                        "slug": "sunscreens",
                        "keywords": ["sunscreen", "sunblock", "spf 50", "spf 60", "uv protection", "sun shield"],
                        "path": ["Beauty & Personal Care", "Skincare", "Sun Protection", "Sunscreens"]
                    },
                    {
                        "name": "Lip Care & Treatments",
                        "slug": "lip-care",
                        "keywords": ["lip balm", "lip serum", "lip butter", "lip gloss", "lip mask", "lip treatment"],
                        "path": ["Beauty & Personal Care", "Skincare", "Lip Care", "Lip Care & Treatments"]
                    }
                ]
            },
            {
                "name": "Haircare",
                "slug": "beauty-haircare",
                "product_types": [
                    {
                        "name": "Shampoo & Conditioner",
                        "slug": "shampoo-conditioner",
                        "keywords": ["shampoo", "conditioner", "hair cleanser", "anti-dandruff shampoo", "keratin shampoo"],
                        "path": ["Beauty & Personal Care", "Haircare", "Washing", "Shampoo & Conditioner"]
                    },
                    {
                        "name": "Hair Oils & Serums",
                        "slug": "hair-oils-serums",
                        "keywords": ["hair oil", "rosemary oil", "argan oil", "hair growth serum", "hair tonic"],
                        "path": ["Beauty & Personal Care", "Haircare", "Treatments", "Hair Oils & Serums"]
                    }
                ]
            },
            {
                "name": "Fragrances & Perfumes",
                "slug": "beauty-fragrances",
                "product_types": [
                    {
                        "name": "Eau de Parfum",
                        "slug": "eau-de-parfum",
                        "keywords": ["perfume", "fragrance", "eau de parfum", "edp", "cologne", "body mist", "attar", "oud"],
                        "path": ["Beauty & Personal Care", "Fragrances & Perfumes", "Fine Fragrances", "Eau de Parfum"]
                    }
                ]
            }
        ]
    },
    {
        "name": "Home & Living",
        "slug": "home-living",
        "description": "Kitchen, furniture, home decor, bedding, and domestic appliances",
        "subcategories": [
            {
                "name": "Kitchen & Dining",
                "slug": "home-kitchen-dining",
                "product_types": [
                    {
                        "name": "Tea & Coffee Accessories",
                        "slug": "tea-coffee-accessories",
                        "keywords": ["matcha", "whisk", "ceremonial", "tea maker", "coffee grinder", "french press", "pour over", "kettle"],
                        "path": ["Home & Living", "Kitchen & Dining", "Beverage Prep", "Tea & Coffee Accessories"]
                    },
                    {
                        "name": "Cookware & Bakeware",
                        "slug": "cookware-bakeware",
                        "keywords": ["pan", "frying pan", "pot", "non-stick cookware", "knife set", "baking sheet", "cutting board"],
                        "path": ["Home & Living", "Kitchen & Dining", "Cookware", "Cookware & Bakeware"]
                    },
                    {
                        "name": "Food Storage & Organization",
                        "slug": "food-storage",
                        "keywords": ["airtight container", "food container", "lunch box", "bento", "spice rack", "mason jar"],
                        "path": ["Home & Living", "Kitchen & Dining", "Storage", "Food Storage & Organization"]
                    }
                ]
            },
            {
                "name": "Home Decor & Lighting",
                "slug": "home-decor-lighting",
                "product_types": [
                    {
                        "name": "Lamps & Ambient Lighting",
                        "slug": "lamps-lighting",
                        "keywords": ["desk lamp", "table lamp", "sunset lamp", "night light", "chandelier", "wall light", "fairy lights"],
                        "path": ["Home & Living", "Home Decor & Lighting", "Lighting", "Lamps & Ambient Lighting"]
                    }
                ]
            }
        ]
    },
    {
        "name": "Sports & Fitness",
        "slug": "sports-fitness",
        "description": "Athletic gear, gym equipment, endurance, outdoor recreation, and sports apparel",
        "subcategories": [
            {
                "name": "Gym & Strength Training",
                "slug": "sports-gym-strength",
                "product_types": [
                    {
                        "name": "Resistance Bands & Weights",
                        "slug": "resistance-bands-weights",
                        "keywords": ["resistance bands", "dumbbells", "kettlebell", "gym gloves", "workout mat", "yoga mat"],
                        "path": ["Sports & Fitness", "Gym & Strength Training", "Fitness Gear", "Resistance Bands & Weights"]
                    }
                ]
            },
            {
                "name": "Running & Outdoor",
                "slug": "sports-running-outdoor",
                "product_types": [
                    {
                        "name": "Hydration Vests & Packs",
                        "slug": "hydration-vests-packs",
                        "keywords": ["running vest", "hydration pack", "water bladder", "running belt", "titanflex", "trail vest"],
                        "path": ["Sports & Fitness", "Running & Outdoor", "Packs & Hydration", "Hydration Vests & Packs"]
                    }
                ]
            }
        ]
    },
    {
        "name": "Health & Wellness",
        "slug": "health-wellness",
        "description": "Vitamins, supplements, medical supplies, and personal well-being",
        "subcategories": [
            {
                "name": "Dietary Supplements",
                "slug": "health-dietary-supplements",
                "product_types": [
                    {
                        "name": "Vitamins & Minerals",
                        "slug": "vitamins-minerals",
                        "keywords": ["vitamin c", "multivitamin", "zinc", "omega 3", "fish oil", "biotin", "whey protein", "creatine"],
                        "path": ["Health & Wellness", "Dietary Supplements", "Vitamins", "Vitamins & Minerals"]
                    }
                ]
            }
        ]
    },
    {
        "name": "Automotive",
        "slug": "automotive",
        "description": "Car electronics, replacement parts, car care, and automotive accessories",
        "subcategories": [
            {
                "name": "Car Electronics",
                "slug": "automotive-car-electronics",
                "product_types": [
                    {
                        "name": "Dash Cams",
                        "slug": "dash-cams",
                        "keywords": ["dash cam", "car dvr", "rearview camera", "car tracker", "fm transmitter", "car charger"],
                        "path": ["Automotive", "Car Electronics", "Cameras & Audio", "Dash Cams"]
                    }
                ]
            }
        ]
    },
    {
        "name": "Toys & Collectibles",
        "slug": "toys-collectibles",
        "description": "Toys, games, action figures, board games, and collectible novelties",
        "subcategories": [
            {
                "name": "Action Figures & Collectibles",
                "slug": "toys-action-figures",
                "product_types": [
                    {
                        "name": "Collectible Figures",
                        "slug": "collectible-figures",
                        "keywords": ["action figure", "funko pop", "anime figure", "building blocks", "lego", "diecast car"],
                        "path": ["Toys & Collectibles", "Action Figures & Collectibles", "Figures", "Collectible Figures"]
                    }
                ]
            }
        ]
    },
    {
        "name": "Groceries & Food",
        "slug": "groceries-food",
        "description": "Beverages, pantry staples, snacks, and gourmet specialty goods",
        "subcategories": [
            {
                "name": "Beverages",
                "slug": "groceries-beverages",
                "product_types": [
                    {
                        "name": "Tea & Coffee Goods",
                        "slug": "tea-coffee-goods",
                        "keywords": ["green tea", "black tea", "organic matcha", "coffee beans", "instant coffee"],
                        "path": ["Groceries & Food", "Beverages", "Hot Drinks", "Tea & Coffee Goods"]
                    }
                ]
            }
        ]
    },
    {
        "name": "Baby & Kids",
        "slug": "baby-kids",
        "description": "Baby care, nursery items, gear, and children apparel",
        "subcategories": [
            {
                "name": "Baby Gear",
                "slug": "baby-gear",
                "product_types": [
                    {
                        "name": "Baby Carriers & Strollers",
                        "slug": "baby-carriers-strollers",
                        "keywords": ["stroller", "baby carrier", "car seat", "diaper bag", "baby wrap"],
                        "path": ["Baby & Kids", "Baby Gear", "Mobility", "Baby Carriers & Strollers"]
                    }
                ]
            }
        ]
    },
    {
        "name": "Pet Supplies",
        "slug": "pet-supplies",
        "description": "Pet food, toys, grooming, and care supplies for domestic animals",
        "subcategories": [
            {
                "name": "Dog Supplies",
                "slug": "pet-dog-supplies",
                "product_types": [
                    {
                        "name": "Dog Leashes & Harnesses",
                        "slug": "dog-leashes-harnesses",
                        "keywords": ["dog leash", "dog harness", "dog collar", "dog bed", "chew toy"],
                        "path": ["Pet Supplies", "Dog Supplies", "Collars & Leashes", "Dog Leashes & Harnesses"]
                    }
                ]
            }
        ]
    },
    {
        "name": "Tools & Hardware",
        "slug": "tools-hardware",
        "description": "Power tools, hand tools, electrical supplies, and building hardware",
        "subcategories": [
            {
                "name": "Hand & Power Tools",
                "slug": "tools-hand-power",
                "product_types": [
                    {
                        "name": "Drills & Screwdrivers",
                        "slug": "drills-screwdrivers",
                        "keywords": ["cordless drill", "screwdriver set", "impact driver", "wrench", "measuring tape"],
                        "path": ["Tools & Hardware", "Hand & Power Tools", "Power Tools", "Drills & Screwdrivers"]
                    }
                ]
            }
        ]
    },
    {
        "name": "Office & Stationery",
        "slug": "office-stationery",
        "description": "Office supplies, writing instruments, desk organization, and paper products",
        "subcategories": [
            {
                "name": "Writing & Desk Organization",
                "slug": "office-writing-desk",
                "product_types": [
                    {
                        "name": "Notebooks & Planners",
                        "slug": "notebooks-planners",
                        "keywords": ["notebook", "planner", "journal", "pen set", "fountain pen", "desk pad", "desk organizer"],
                        "path": ["Office & Stationery", "Writing & Desk Organization", "Paper Goods", "Notebooks & Planners"]
                    }
                ]
            }
        ]
    },
    {
        "name": "Jewelry & Accessories",
        "slug": "jewelry-accessories",
        "description": "Fine & fashion jewelry, watches, sunglasses, bags, and luxury accessories",
        "subcategories": [
            {
                "name": "Fashion Jewelry & Watches",
                "slug": "jewelry-fashion-watches",
                "product_types": [
                    {
                        "name": "Sunglasses",
                        "slug": "sunglasses",
                        "keywords": ["sunglasses", "polarized glasses", "eyewear", "aviator", "uv400 shades"],
                        "path": ["Jewelry & Accessories", "Fashion Jewelry & Watches", "Eyewear", "Sunglasses"]
                    }
                ]
            }
        ]
    },
    {
        "name": "Books & Media",
        "slug": "books-media",
        "description": "Books, digital media, music, movies, and video games",
        "subcategories": [
            {
                "name": "Books",
                "slug": "books-general",
                "product_types": [
                    {
                        "name": "Paperback Books",
                        "slug": "paperback-books",
                        "keywords": ["novel", "hardcover", "paperback", "biography", "fiction book"],
                        "path": ["Books & Media", "Books", "Printed Books", "Paperback Books"]
                    }
                ]
            }
        ]
    },
    {
        "name": "Industrial & Business",
        "slug": "industrial-business",
        "description": "MRO, commercial equipment, test instruments, and industrial supplies",
        "subcategories": [
            {
                "name": "Testing & Measurement",
                "slug": "industrial-testing-measurement",
                "product_types": [
                    {
                        "name": "Digital Multimeters",
                        "slug": "digital-multimeters",
                        "keywords": ["multimeter", "laser distance meter", "voltage tester", "caliper"],
                        "path": ["Industrial & Business", "Testing & Measurement", "Electronic Testing", "Digital Multimeters"]
                    }
                ]
            }
        ]
    },
    {
        "name": "Other",
        "slug": "other",
        "description": "Miscellaneous and specialized marketplace products",
        "subcategories": [
            {
                "name": "General Miscellaneous",
                "slug": "other-general",
                "product_types": [
                    {
                        "name": "Miscellaneous Item",
                        "slug": "miscellaneous-item",
                        "keywords": [],
                        "path": ["Other", "General Miscellaneous", "Standard", "Miscellaneous Item"]
                    }
                ]
            }
        ]
    },
    {
        "name": "Unknown",
        "slug": "unknown",
        "description": "Unclassified marketplace records requiring human or AI review",
        "subcategories": [
            {
                "name": "Unknown",
                "slug": "unknown-subcategory",
                "product_types": [
                    {
                        "name": "Unknown",
                        "slug": "unknown-product-type",
                        "keywords": [],
                        "path": ["Unknown", "Unknown", "Unknown"]
                    }
                ]
            }
        ]
    }
]

def generate_slug(text: str) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9\s-]', '', text).strip().lower()
    return re.sub(r'[\s-]+', '-', cleaned)

def get_top_level_categories() -> List[str]:
    return list(INITIAL_TOP_LEVEL_CATEGORIES)
