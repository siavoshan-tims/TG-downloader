#!/usr/bin/env python3
"""
Telegram File Downloader Using Web Telegram
دانلود فایل‌های تلگرام از طریق Web Telegram - بدون نیاز به API
"""

import os
import re
import json
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, unquote
import base64

# تلاش برای import سرویس‌های مختلف
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.action_chains import ActionChains
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️ Selenium نصب نیست. در حال نصب خودکار...")
    os.system("pip install selenium webdriver-manager")
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True

class TelegramWebDownloader:
    """دانلودر تلگرام با استفاده از Web Telegram"""
    
    def __init__(self, output_dir="downloads", headless=True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.driver = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def setup_driver(self):
        """راه‌اندازی مرورگر کروم برای Web Telegram"""
        print("🌐 در حال راه‌اندازی مرورگر...")
        
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        # پشتیبانی از دانلود خودکار
        prefs = {
            "download.default_directory": str(self.output_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            if SELENIUM_AVAILABLE:
                try:
                    from webdriver_manager.chrome import ChromeDriverManager
                    self.driver = webdriver.Chrome(
                        ChromeDriverManager().install(), 
                        options=chrome_options
                    )
                except:
                    self.driver = webdriver.Chrome(options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
                
            self.driver.implicitly_wait(10)
            print("✅ مرورگر با موفقیت راه‌اندازی شد")
        except Exception as e:
            print(f"❌ خطا در راه‌اندازی مرورگر: {e}")
            raise
    
    def extract_post_info(self, url):
        """استخراج اطلاعات پست از لینک تلگرام"""
        patterns = [
            r'https?://t\.me/([^/]+)/(\d+)',
            r'https?://telegram\.me/([^/]+)/(\d+)',
            r'https?://telegram\.dog/([^/]+)/(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                channel = match.group(1)
                post_id = match.group(2)
                return channel, post_id
        
        raise ValueError(f"❌ لینک معتبر تلگرام نیست: {url}")
    
    def get_web_telegram_url(self, channel, post_id):
        """ساخت لینک Web Telegram برای پست مورد نظر"""
        # روش اول: لینک مستقیم WebZ (نسخه جدید)
        web_urls = [
            f"https://web.telegram.org/k/#@{channel}/{post_id}",
            f"https://web.telegram.org/z/#@{channel}/{post_id}",
            f"https://web.telegram.org/a/#@{channel}/{post_id}"
        ]
        return web_urls
    
    def wait_for_content(self, timeout=30):
        """انتظار برای بارگذاری محتوای صفحه"""
        try:
            # انتظار برای بارگذاری پیام
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CLASS_NAME, "message"))
            )
            time.sleep(3)  # زمان اضافی برای بارگذاری کامل
            return True
        except:
            try:
                # تلاش با کلاس‌های مختلف
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='message']"))
                )
                time.sleep(2)
                return True
            except:
                return False
    
    def find_download_buttons(self):
        """پیدا کردن دکمه‌های دانلود در صفحه"""
        download_buttons = []
        
        # الگوهای مختلف برای پیدا کردن دکمه دانلود
        selectors = [
            "a[download]",
            "[class*='download']",
            "[class*='Download']",
            "button[class*='download']",
            "a[href*='download']",
            "video",
            "audio",
            "img"
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    # بررسی لینک دانلود
                    if elem.tag_name == 'a':
                        href = elem.get_attribute('href')
                        if href and any(ext in href.lower() for ext in ['.mp4', '.jpg', '.png', '.pdf', '.zip', '.mp3']):
                            download_buttons.append({
                                'element': elem,
                                'url': href,
                                'type': 'direct_link'
                            })
                    # بررسی رسانه‌ها
                    elif elem.tag_name in ['video', 'audio', 'img']:
                        src = elem.get_attribute('src')
                        if src:
                            download_buttons.append({
                                'element': elem,
                                'url': src,
                                'type': elem.tag_name
                            })
            except:
                continue
        
        return download_buttons
    
    def extract_media_from_page(self):
        """استخراج تمام رسانه‌ها از صفحه با جاوااسکریپت"""
        media_data = self.driver.execute_script("""
            const media = [];
            
            // پیدا کردن تمام لینک‌های دانلود
            document.querySelectorAll('a[href]').forEach(link => {
                const href = link.href;
                if (href && (
                    href.includes('/file/') ||
                    href.match(/\\.(mp4|mp3|jpg|png|gif|pdf|zip|rar)$/i)
                )) {
                    media.push({
                        type: 'link',
                        url: href,
                        text: link.innerText
                    });
                }
            });
            
            // پیدا کردن ویدیوها و صداها
            document.querySelectorAll('video, audio').forEach(mediaElem => {
                const src = mediaElem.src || mediaElem.currentSrc;
                if (src) {
                    media.push({
                        type: mediaElem.tagName.toLowerCase(),
                        url: src
                    });
                }
            });
            
            // پیدا کردن تصاویر
            document.querySelectorAll('img').forEach(img => {
                if (img.src && img.src.startsWith('http')) {
                    media.push({
                        type: 'image',
                        url: img.src
                    });
                }
            });
            
            return media;
        """)
        
        return media_data
    
    def download_file_with_requests(self, url, filepath):
        """دانلود فایل با استفاده از requests"""
        try:
            print(f"⬇️  در حال دانلود: {filepath.name}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': self.driver.current_url
            }
            
            response = self.session.get(url, headers=headers, stream=True, timeout=60)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r📊 پیشرفت: {percent:.1f}%", end='')
            
            print(f"\n✅ دانلود شد: {filepath.name}")
            return True
            
        except Exception as e:
            print(f"❌ خطا در دانلود: {e}")
            return False
    
    def download_post(self, url):
        """دانلود کامل پست تلگرام"""
        print("\n" + "="*60)
        print("🚀 شروع دانلود از تلگرام (Web Telegram Method)")
        print("="*60)
        
        # استخراج اطلاعات پست
        try:
            channel, post_id = self.extract_post_info(url)
            print(f"📺 کانال: @{channel}")
            print(f"🆔 شناسه: {post_id}")
        except ValueError as e:
            print(f"❌ {e}")
            return False
        
        # راه‌اندازی مرورگر
        try:
            self.setup_driver()
        except Exception as e:
            print(f"❌ خطا در راه‌اندازی مرورگر: {e}")
            return False
        
        # تلاش برای لینک‌های مختلف Web Telegram
        web_urls = self.get_web_telegram_url(channel, post_id)
        page_loaded = False
        
        for web_url in web_urls:
            try:
                print(f"\n🔄 تلاش برای اتصال به: {web_url}")
                self.driver.get(web_url)
                
                if self.wait_for_content(timeout=20):
                    print("✅ صفحه با موفقیت بارگذاری شد")
                    page_loaded = True
                    break
            except Exception as e:
                print(f"⚠️ خطا در اتصال: {e}")
                continue
        
        if not page_loaded:
            print("❌ امکان بارگذاری صفحه وجود ندارد")
            self.driver.quit()
            return False
        
        # ایجاد پوشه برای این پست
        post_folder = self.output_dir / f"{channel}_{post_id}"
        post_folder.mkdir(parents=True, exist_ok=True)
        
        # استخراج متن پست
        try:
            text_elements = self.driver.find_elements(By.CSS_SELECTOR, ".message-text, [class*='message_text']")
            if text_elements:
                text_content = text_elements[0].text
                if text_content:
                    text_file = post_folder / "message.txt"
                    text_file.write_text(text_content, encoding='utf-8')
                    print(f"📝 متن پست ذخیره شد ({len(text_content)} کاراکتر)")
        except Exception as e:
            print(f"⚠️ استخراج متن با مشکل مواجه شد: {e}")
        
        # استخراج رسانه‌ها
        print("\n🔍 در حال جستجوی فایل‌ها...")
        media_items = self.extract_media_from_page()
        
        if not media_items:
            print("⚠️ هیچ فایل رسانه‌ای یافت نشد")
            # ذخیره اسکرین‌شات برای دیباگ
            screenshot_path = post_folder / "page_screenshot.png"
            self.driver.save_screenshot(str(screenshot_path))
            print(f"📸 اسکرین‌شات صفحه ذخیره شد: {screenshot_path}")
        else:
            print(f"📊 {len(media_items)} فایل پیدا شد")
            
            downloaded = 0
            failed = 0
            
            for idx, media in enumerate(media_items, 1):
                print(f"\n🔍 فایل {idx}/{len(media_items)}:")
                
                # استخراج نام فایل
                url_path = urlparse(media['url']).path
                filename = os.path.basename(url_path)
                
                if not filename or '.' not in filename:
                    ext_map = {
                        'video': 'mp4',
                        'audio': 'mp3',
                        'image': 'jpg'
                    }
                    ext = ext_map.get(media['type'], 'bin')
                    filename = f"file_{idx}.{ext}"
                
                # پاکسازی نام فایل
                filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                filepath = post_folder / filename
                
                # دانلود فایل
                if self.download_file_with_requests(media['url'], filepath):
                    downloaded += 1
                else:
                    failed += 1
                
                time.sleep(1)  # تاخیر بین دانلودها
            
            print(f"\n📊 گزارش دانلود: ✅ موفق: {downloaded} | ❌ ناموفق: {failed}")
        
        # ذخیره متادیتا
        metadata = {
            'channel': channel,
            'post_id': post_id,
            'url': url,
            'download_date': datetime.now().isoformat(),
            'media_count': len(media_items) if media_items else 0,
            'method': 'web_telegram'
        }
        
        (post_folder / "metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        # بستن مرورگر
        self.driver.quit()
        
        print("\n✨ عملیات دانلود با موفقیت به پایان رسید!")
        print(f"📁 مسیر ذخیره: {post_folder}")
        print("="*60)
        
        return True

def main():
    parser = argparse.ArgumentParser(description='دانلود فایل‌های تلگرام با Web Telegram')
    parser.add_argument('--url', '-u', required=True, help='لینک پست تلگرام')
    parser.add_argument('--output', '-o', default='downloads', help='پوشه خروجی')
    parser.add_argument('--visible', action='store_true', help='نمایش مرورگر (حالت معمولی)')
    
    args = parser.parse_args()
    
    downloader = TelegramWebDownloader(
        output_dir=args.output,
        headless=not args.visible
    )
    
    success = downloader.download_post(args.url)
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
