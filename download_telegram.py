#!/usr/bin/env python3
import os
import re
import json
import argparse
import requests
from urllib.parse import urlparse
from pathlib import Path

class TelegramDownloader:
    def __init__(self, output_dir="downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})

    def extract_post_info(self, url):
        """استخراج اطلاعات پست - پشتیبانی از فرمت‌های مختلف"""
        patterns = [
            r't\.me/([^/]+)/(\d+)',
            r'telegram\.me/([^/]+)/(\d+)',
            r'telegram\.dog/([^/]+)/(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2)
        raise ValueError(f"لینک نامعتبر: {url}")

    def try_alternative_sources(self, channel, post_id):
        """تلاش برای دریافت محتوا از سورس‌های جایگزین (بدون نیاز به ویجت)"""
        # سرویس tgstat (محتوا را ایندکس می‌کند)
        tgstat_url = f"https://tgstat.com/post/{channel}/{post_id}"
        
        try:
            resp = self.session.get(tgstat_url, timeout=20)
            if resp.status_code == 200 and 'tgme_widget_message_text' in resp.text:
                return resp.text
        except:
            pass
        
        # سرویس telegra.ph (برای پست‌های متنی)
        telegraph_url = f"https://telegra.ph/{channel}-{post_id}"
        try:
            resp = self.session.get(telegraph_url, timeout=20)
            if resp.status_code == 200:
                return resp.text
        except:
            pass
            
        return None

    def download_post(self, url):
        print(f"\n🔍 در حال پردازش: {url}")
        channel, post_id = self.extract_post_info(url)
        
        # ایجاد پوشه
        post_folder = self.output_dir / f"{channel}_{post_id}"
        post_folder.mkdir(parents=True, exist_ok=True)
        
        # تلاش برای دریافت محتوا از منابع جایگزین
        alt_content = self.try_alternative_sources(channel, post_id)
        
        if alt_content:
            # ذخیره متن در صورت وجود
            text_match = re.search(r'<div class="tgme_widget_message_text"[^>]*>(.*?)</div>', 
                                  alt_content, re.DOTALL)
            if text_match:
                text = re.sub(r'<[^>]+>', '', text_match.group(1))
                text_file = post_folder / "message.txt"
                text_file.write_text(text, encoding='utf-8')
                print(f"✅ متن پست ذخیره شد")
            
            # جستجوی فایل‌ها در محتوای دریافتی
            file_patterns = [
                r'href="([^"]+\.(jpg|png|mp4|pdf|zip))"',
                r'src="([^"]+\.(jpg|png|webp))"',
            ]
            files_found = []
            for pattern in file_patterns:
                files_found.extend(re.findall(pattern, alt_content))
            
            if files_found:
                print(f"📁 {len(files_found)} فایل پیدا شد")
                # دانلود فایل‌ها (کد دانلود مشابه قبل)
        
        # ذخیره متادیتا
        metadata = {
            'channel': channel,
            'post_id': post_id,
            'url': url,
            'download_date': datetime.now().isoformat(),
            'content_found': bool(alt_content),
            'alternative_source_used': alt_content is not None
        }
        
        (post_folder / "metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), 
            encoding='utf-8'
        )
        
        if not alt_content:
            print("\n⚠️ توجه: این پست ممکن است:")
            print("   1) فایل قابل دانلودی نداشته باشد")
            print("   2) فقط از طریق ویجت تعبیه شده در سایت قابل مشاهده باشد")
            print("   3) غیرعمومی یا حذف شده باشد")
        
        return True
