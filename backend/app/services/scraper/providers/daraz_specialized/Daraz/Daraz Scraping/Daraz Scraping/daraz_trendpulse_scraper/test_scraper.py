import unittest
from db_manager import DatabaseManager

class TestTrendPulseScraper(unittest.TestCase):
    def setUp(self):
        self.db = DatabaseManager(":memory:")

    def test_database_deduplication(self):
        sample_prod = {
            "product_id": "TEST_101",
            "url": "https://daraz.pk/test",
            "title": "Test Gaming Mouse",
            "current_price": "Rs. 1,500",
            "brand": "TestBrand",
            "seller_name": "TestSeller",
            "seller_id": "seller_01"
        }
        self.db.save_product(sample_prod)
        self.assertTrue(self.db.is_already_crawled("TEST_101"))
        self.assertFalse(self.db.is_already_crawled("NON_EXISTENT_ID"))

    def tearDown(self):
        self.db.close()

if __name__ == "__main__":
    unittest.main()
