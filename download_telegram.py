#!/usr/bin/env python3
"""
Telegram File Downloader - نسخه کامل برای کامپیوتر
"""

import os
import re
import json
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

class TelegramDownloader:
    def __init__(self, output_dir="downloads", headless=True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.driver = None
        self.session = requests.Session()
        
    def setup_driver(self):
        """راه‌اندازی مرورگر کروم"""
        print("🌐 در حال راه‌اندازی مرورگر...")
        
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # دانلود خودکار chromedriver
        self.driver = webdriver.Chrome(
            ChromeDriverManager().install(),
            options=chrome_options
        )
        self.driver.implicitly_wait(10)
        print("✅ مرورگر راه‌اندازی شد")
    
    def extract_post_info(self, url):
        patterns = [r't\.me/([^/]+)/(\d+)', r'telegram\.me/([^/]+)/(\d+)']
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2)
        raise ValueError(f"لینک نامعتبر: {url}")
    
    def download_post(self, url):
        print("\n" + "="*60)
        print("🚀 شروع دانلود از تلگرام")
        print("="*60)
        
        channel, post_id = self.extract_post_info(url)
        print(f"📺 کانال: @{channel}")
        print(f"🆔 شناسه: {post_id}")
        
        self.setup_driver()
        
        # لینک Web Telegram
        web_url = f"https://web.telegram.org/k/#@{channel}/{post_id}"
        print(f"\n🔄 اتصال به: {web_url}")
        self.driver.get(web_url)
        
        # انتظار برای بارگذاری
        time.sleep(5)
        
        # ایجاد پوشه
        post_folder = self.output_dir / f"{channel}_{post_id}"
        post_folder.mkdir(parents=True, exist_ok=True)
        
        # استخراج متن
        try:
            text_elem = self.driver.find_element(By.CSS_SELECTOR, ".message-text")
            text_content = text_elem.text
            if text_content:
                (post_folder / "message.txt").write_text(text_content, encoding='utf-8')
                print(f"📝 متن پست ذخیره شد")
        except:
            print("ℹ️ متنی یافت نشد")
        
        # استخراج لینک فایل‌ها با جاوااسکریپت
        media_urls = self.driver.execute_script("""
            const urls = [];
            document.querySelectorAll('a[href]').forEach(link => {
                let href = link.href;
                if (href && (href.includes('/file/') || href.match(/\\.(mp4|mp3|jpg|png|pdf|zip)$/i))) {
                    urls.push(href);
                }
            });
            document.querySelectorAll('video, audio').forEach(media => {
                if (media.src) urls.push(media.src);
            });
            return urls;
        """)
        
        if media_urls:
            print(f"\n📊 {len(media_urls)} فایل پیدا شد")
            for idx, media_url in enumerate(media_urls, 1):
                filename = media_url.split('/')[-1].split('?')[0]
                if not filename or '.' not in filename:
                    filename = f"file_{idx}.mp4"
                
                filepath = post_folder / filename
                print(f"⬇️  دانلود: {filename}")
                
                try:
                    resp = self.session.get(media_url, stream=True, timeout=60)
                    with open(filepath, 'wb') as f:
                        for chunk in resp.iter_content(8192):
                            f.write(chunk)
                    print(f"✅ ذخیره شد: {filename}")
                except Exception as e:
                    print(f"❌ خطا: {e}")
        else:
            print("⚠️ هیچ فایل رسانه‌ای یافت نشد")
        
        # ذخیره متادیتا
        metadata = {
            'channel': channel,
            'post_id': post_id,
            'url': url,
            'download_date': datetime.now().isoformat()
        }
        (post_folder / "metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        self.driver.quit()
        print("\n✨ دانلود کامل شد!")
        return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', '-u', required=True, help='لینک تلگرام')
    parser.add_argument('--output', '-o', default='downloads')
    parser.add_argument('--visible', action='store_true', help='نمایش مرورگر')
    
    args = parser.parse_args()
    
    downloader = TelegramDownloader(args.output, headless=not args.visible)
    downloader.download_post(args.url)

if __name__ == "__main__":
    main()
