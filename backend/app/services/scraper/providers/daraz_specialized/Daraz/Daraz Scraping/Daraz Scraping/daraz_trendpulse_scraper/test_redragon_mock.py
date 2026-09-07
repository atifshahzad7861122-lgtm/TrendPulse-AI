import json
from db_manager import DatabaseManager
from excel_exporter import export_to_excel
from logger import logger

mock_product = {
  "product_id": "439281729",
  "sku": "SKU-439281729",
  "title": "Redragon K552 Mechanical Gaming Keyboard RGB Backlit",
  "description": "Compact 87-key space-saving design with custom mechanical switches.",
  "current_price": "Rs. 7,499",
  "original_price": "Rs. 9,999",
  "discount": "-25%",
  "currency": "PKR",
  "brand": "Redragon",
  "category": "Computers & Laptops > Computer Accessories > Keyboards",
  "rating": "4.8",
  "total_reviews": "142",
  "sold_count": "500+ Sold",
  "seller_name": "TechZone Official",
  "seller_id": "techzone-pk",
  "seller_metrics": {
    "Positive Seller Ratings": "96%",
    "Ship on Time": "99%",
    "Chat Response Rate": "95%"
  },
  "image_gallery": [
    "https://img.daraz.pk/p/keyboard_front.jpg",
    "https://img.daraz.pk/p/keyboard_side.jpg"
  ],
  "variations": ["Red Switch / Black", "Blue Switch / Black"],
  "specifications": {
    "Key Switches": "Outemu Blue / Red",
    "Backlight": "RGB Rainbow",
    "Connection": "USB Wired"
  },
  "reviews": [
    {
      "page": 1,
      "reviewer": "Zubair A.",
      "date": "14 Aug 2026",
      "rating": 5,
      "variation": "Red Switch / Black",
      "content": "Authentic product, clicky switches are responsive.",
      "images": "https://img.daraz.pk/review1.jpg"
    }
  ]
}

def test_mock_injection():
    # 1. Save mock to database
    db = DatabaseManager()
    logger.info("Injecting Redragon mock product record into database...")
    db.save_product(mock_product)
    db.close()
    
    # 2. Export mock details to styled Excel report
    logger.info("Exporting Redragon product details to Excel...")
    saved_file = export_to_excel(
        product_data=mock_product,
        specs=mock_product["specifications"],
        reviews=mock_product["reviews"],
        output_filepath="redragon_scraped_output.xlsx"
    )
    logger.info(f"✅ Mock test complete! Output saved to: '{saved_file}'")

if __name__ == "__main__":
    test_mock_injection()
