#!/usr/bin/env python3
"""
Telegram Message Downloader
دانلود محتوای پست‌های عمومی تلگرام
"""

import os
import re
import json
import argparse
import requests
from urllib.parse import urlparse, unquote
from datetime import datetime
from pathlib import Path
import time
import random

class TelegramDownloader:
    """دانلودر محتوای تلگرام"""
    
    def __init__(self, output_dir="downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # User-Agent برای شبیه‌سازی مرورگر
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def extract_post_info(self, url):
        """استخراج اطلاعات پست از لینک تلگرام"""
        patterns = [
            r'telegram\.org/dl\?url=(.+)$',  # لینک‌های مستقیم telegram.org
            r't\.me/([^/]+)/(\d+)',          # t.me/username/postid
            r'telegram\.me/([^/]+)/(\d+)',   # telegram.me/username/postid
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                if 'dl?url=' in url:
                    # لینک رمزگذاری شده
                    encoded_url = match.group(1)
                    decoded_url = unquote(encoded_url)
                    return self.extract_post_info(decoded_url)
                else:
                    channel = match.group(1)
                    post_id = match.group(2)
                    return channel, post_id
        
        raise ValueError(f"لینک معتبر تلگرام نیست: {url}")
    
    def get_telegram_page(self, channel, post_id):
        """دریافت صفحه پست تلگرام"""
        urls_to_try = [
            f"https://t.me/{channel}/{post_id}",
            f"https://telegram.me/{channel}/{post_id}",
            f"https://telegram.dog/{channel}/{post_id}"
        ]
        
        for url in urls_to_try:
            try:
                print(f"🔄 تلاش برای اتصال به: {url}")
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    print(f"✅ اتصال موفق به: {url}")
                    return response.text
                else:
                    print(f"⚠️ خطای {response.status_code} از {url}")
                    
            except Exception as e:
                print(f"❌ خطا در اتصال به {url}: {e}")
                continue
        
        raise Exception("امکان اتصال به تلگرام وجود ندارد")
    
    def extract_media_urls(self, html_content):
        """استخراج لینک‌های رسانه‌ای از صفحه"""
        media_urls = []
        
        # الگوهای مختلف برای پیدا کردن لینک‌های رسانه
        patterns = {
            'image': [
                r'<img[^>]+src="([^"]+)"[^>]*>',
                r'<a[^>]+href="([^"]+\.(jpg|jpeg|png|gif|webp))"[^>]*>',
            ],
            'video': [
                r'<video[^>]+src="([^"]+)"[^>]*>',
                r'<source[^>]+src="([^"]+\.(mp4|webm|mov))"[^>]*>',
                r'href="([^"]+\.(mp4|mkv|avi))"',
            ],
            'audio': [
                r'href="([^"]+\.(mp3|ogg|m4a|wav))"',
                r'<audio[^>]+src="([^"]+)"',
            ],
            'file': [
                r'href="([^"]+\.(pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar|7z))"',
            ]
        }
        
        for media_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    url = match if isinstance(match, str) else match[0]
                    if url.startswith('/'):
                        url = 'https://t.me' + url
                    if url.startswith('//'):
                        url = 'https:' + url
                    if url.startswith('http') and 'telegram' in url:
                        media_urls.append({
                            'url': url,
                            'type': media_type
                        })
        
        # حذف تکراری‌ها
        unique_urls = []
        seen = set()
        for item in media_urls:
            if item['url'] not in seen:
                seen.add(item['url'])
                unique_urls.append(item)
        
        return unique_urls
    
    def extract_text_content(self, html_content):
        """استخراج متن پست"""
        # پیدا کردن متن در تگ‌های مختلف
        text_patterns = [
            r'<div class="tgme_widget_message_text"[^>]*>(.*?)</div>',
            r'<div class="message"[^>]*>(.*?)</div>',
            r'<div class="text"[^>]*>(.*?)</div>',
        ]
        
        for pattern in text_patterns:
            match = re.search(pattern, html_content, re.DOTALL)
            if match:
                text = match.group(1)
                # حذف تگ‌های HTML
                text = re.sub(r'<[^>]+>', '', text)
                text = re.sub(r'&nbsp;', ' ', text)
                text = re.sub(r'<br\s*/?>', '\n', text)
                text = re.sub(r'&[a-z]+;', '', text)
                return text.strip()
        
        return ""
    
    def download_file(self, url, filepath):
        """دانلود فایل با نمایش پیشرفت"""
        try:
            print(f"⬇️  شروع دانلود: {os.path.basename(filepath)}")
            
            response = self.session.get(url, stream=True, timeout=60)
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
            
            print(f"\n✅ دانلود کامل: {os.path.basename(filepath)}")
            return True
            
        except Exception as e:
            print(f"❌ خطا در دانلود {url}: {e}")
            return False
    
    def sanitize_filename(self, filename):
        """پاکسازی نام فایل"""
        # حذف کاراکترهای غیرمجاز
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # محدود کردن طول نام
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:190] + ext
        return filename
    
    def download_post(self, url):
        """دانلود کامل یک پست تلگرام"""
        print("\n" + "="*50)
        print("🚀 شروع دانلود از تلگرام")
        print("="*50)
        
        # استخراج اطلاعات پست
        try:
            channel, post_id = self.extract_post_info(url)
            print(f"📺 کانال: @{channel}")
            print(f"🆔 شناسه پست: {post_id}")
        except ValueError as e:
            print(f"❌ {e}")
            return False
        
        # دریافت صفحه پست
        try:
            html_content = self.get_telegram_page(channel, post_id)
        except Exception as e:
            print(f"❌ {e}")
            return False
        
        # ایجاد پوشه برای این پست
        post_folder = self.output_dir / f"{channel}_{post_id}"
        post_folder.mkdir(parents=True, exist_ok=True)
        
        # استخراج و ذخیره متن
        text_content = self.extract_text_content(html_content)
        if text_content:
            text_file = post_folder / "message.txt"
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(f"کانال: @{channel}\n")
                f.write(f"شناسه پست: {post_id}\n")
                f.write(f"لینک: {url}\n")
                f.write(f"تاریخ دانلود: {datetime.now()}\n")
                f.write("\n" + "="*50 + "\n\n")
                f.write(text_content)
            print(f"📝 متن پست ذخیره شد: {text_file}")
        
        # استخراج و دانلود رسانه‌ها
        media_urls = self.extract_media_urls(html_content)
        
        if not media_urls:
            print("ℹ️ هیچ فایل رسانه‌ای در این پست یافت نشد")
        else:
            print(f"\n📊 تعداد فایل‌های یافت شده: {len(media_urls)}")
            
            downloaded_files = []
            failed_files = []
            
            for idx, media in enumerate(media_urls, 1):
                print(f"\n🔍 فایل {idx}/{len(media_urls)}:")
                
                # استخراج نام فایل از URL
                url_path = urlparse(media['url']).path
                filename = os.path.basename(url_path)
                
                if not filename or '.' not in filename:
                    # اگر نام فایل مشخص نبود، از نوع فایل استفاده کن
                    ext_map = {
                        'image': 'jpg',
                        'video': 'mp4',
                        'audio': 'mp3',
                        'file': 'file'
                    }
                    ext = ext_map.get(media['type'], 'bin')
                    filename = f"{media['type']}_{idx}.{ext}"
                
                filename = self.sanitize_filename(filename)
                filepath = post_folder / filename
                
                # دانلود فایل
                if self.download_file(media['url'], filepath):
                    downloaded_files.append(filename)
                else:
                    failed_files.append(filename)
                
                # مکث کوتاه برای جلوگیری از مسدود شدن
                time.sleep(random.uniform(0.5, 1.5))
            
            # گزارش نهایی
            print("\n" + "="*50)
            print("📊 گزارش دانلود:")
            print(f"✅ موفق: {len(downloaded_files)} فایل")
            print(f"❌ ناموفق: {len(failed_files)} فایل")
            
            if downloaded_files:
                print("\n📁 فایل‌های دانلود شده:")
                for f in downloaded_files:
                    print(f"   - {f}")
        
        # ذخیره متادیتا
        metadata = {
            'channel': channel,
            'post_id': post_id,
            'url': url,
            'download_date': datetime.now().isoformat(),
            'has_text': bool(text_content),
            'media_count': len(media_urls)
        }
        
        metadata_file = post_folder / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 متادیتا ذخیره شد: {metadata_file}")
        print("\n✨ عملیات دانلود با موفقیت به پایان رسید!")
        print("="*50)
        
        return True

def main():
    parser = argparse.ArgumentParser(description='دانلود محتوای پست‌های عمومی تلگرام')
    parser.add_argument('--url', '-u', required=True, help='لینک پست تلگرام')
    parser.add_argument('--output', '-o', default='downloads', help='پوشه خروجی (پیش‌فرض: downloads)')
    
    args = parser.parse_args()
    
    # ایجاد دانلودر و شروع دانلود
    downloader = TelegramDownloader(args.output)
    success = downloader.download_post(args.url)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
