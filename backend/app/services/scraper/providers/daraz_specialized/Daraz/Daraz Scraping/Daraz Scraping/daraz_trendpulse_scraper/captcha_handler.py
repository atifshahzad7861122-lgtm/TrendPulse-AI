import asyncio
from logger import logger

async def handle_captcha_if_present(page):
    """Pauses the browser session and waits for manual user verification upon challenge."""
    captcha_selectors = [
        "#nc_1_n1z", "#nocaptcha", ".nc-container", 
        "iframe[src*='captcha']", "#baxia-dialog-content", ".punish-dialog"
    ]
    for selector in captcha_selectors:
        element = await page.query_selector(selector)
        if element and await element.is_visible():
            logger.warning("🚨 [ANTI-BOT / SECURITY VERIFICATION DETECTED]")
            print("\n" + "="*75)
            print("👉 HUMAN-IN-THE-LOOP ACTIVE: Please solve the slider/CAPTCHA in Chrome.")
            print("="*75)
            await asyncio.to_thread(input, "Press [ENTER] in this terminal after solving the CAPTCHA...")
            logger.info("Resuming scraping session...")
            await asyncio.sleep(2)
            break
