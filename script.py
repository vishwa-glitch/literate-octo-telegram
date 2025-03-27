import os
import asyncio
import random
import aiohttp
import aiofiles
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from telegram import Bot, InputMediaPhoto

# Configuration
WEBSITES = [
    "https://www.elitebabes.com/tag/blonde+babe/"
]
TELEGRAM_BOT_TOKEN = "7630710110:AAE1jWMiWhDnUjqKIo2lgWY2Yc_McbM2wpY"
TELEGRAM_CHANNEL_ID = "-1002501159798"
DOWNLOAD_FOLDER = "temp_images"
NUM_IMAGES = 6  # Telegram allows up to 10 media in a group

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def setup_selenium_driver():
    """Setup Chrome WebDriver with improved initialization"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"user-agent={HEADERS['User-Agent']}")
    chrome_options.add_argument("--enable-unsafe-swiftshader")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    try:
        driver_path = ChromeDriverManager().install()
        service = ChromeService(executable_path=driver_path)
        return webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"WebDriver initialization error: {e}")
        raise

def extract_images(driver, target_url):
    """Extract image URLs from the page"""
    driver.get(target_url)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
    try:
        images = driver.find_elements(By.CSS_SELECTOR, "img[src^='http']")
        valid_images = []
        for img in images:
            try:
                src = img.get_attribute('src')
                if src and src.startswith(('http://', 'https://')) and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    valid_images.append(src)
            except Exception:
                continue
        return valid_images
    except Exception as e:
        print(f"Image extraction error: {e}")
        return []

async def download_image(session, img_url, file_path):
    """Async image download"""
    try:
        async with session.get(img_url, headers=HEADERS) as response:
            if response.status == 200:
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(await response.read())
                return True
    except Exception as e:
        print(f"Download error for {img_url}: {e}")
    return False

async def send_telegram_album(bot, chat_id, file_paths):
    """Send multiple photos as an album/group"""
    try:
        # Prepare media group
        media_group = []
        for file_path in file_paths:
            async with aiofiles.open(file_path, "rb") as f:
                photo_data = await f.read()
                media_group.append(InputMediaPhoto(media=photo_data))
        
        # Send as media group (appears as a single message with multiple photos)
        await bot.send_media_group(chat_id=chat_id, media=media_group)
        return True
    except Exception as e:
        print(f"Telegram send error: {e}")
    return False

async def main():
    target_url = random.choice(WEBSITES)
    print(f"Selected website: {target_url}")

    driver = setup_selenium_driver()
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    try:
        all_images = extract_images(driver, target_url)
        if not all_images:
            print("No images found on the page.")
            return

        selected_images = random.sample(all_images, min(NUM_IMAGES, len(all_images)))
        print(f"Found {len(selected_images)} images")

        async with aiohttp.ClientSession() as session:
            # Download all images first
            file_paths = []
            for idx, img_url in enumerate(selected_images):
                file_path = os.path.join(DOWNLOAD_FOLDER, f"img_{idx}.jpg")
                try:
                    if await download_image(session, img_url, file_path):
                        file_paths.append(file_path)
                        print(f"Downloaded image: {file_path}")
                except Exception as e:
                    print(f"Failed to download image {img_url}: {e}")
            
            # Send all images as a single album
            if file_paths:
                await send_telegram_album(bot, TELEGRAM_CHANNEL_ID, file_paths)
                print("Sent images as album to Telegram")
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Clean up downloaded files
        for file_path in file_paths:
            if os.path.exists(file_path):
                os.remove(file_path)
        driver.quit()

if __name__ == "__main__":
    asyncio.run(main())