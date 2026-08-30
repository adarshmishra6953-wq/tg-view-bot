import os
import re
import time
import random
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# ----------------- Render Web Service Dummy Server ----------------- #
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Playwright Telegram View Bot Running 24/7!")

    def log_message(self, format, *args):
        return

def run_http_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyServer)
    print(f"[*] Dummy HTTP Server live on port {port}")
    server.serve_forever()

# ----------------- प्रॉक्सी स्क्रैपर ----------------- #
PROXIES_POOL = []
PROXIES_LOCK = threading.Lock()

PROXIES_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all"
]

def scrape_fresh_proxies():
    global PROXIES_POOL
    while True:
        new_proxies = set()
        for url in PROXIES_SOURCES:
            try:
                res = requests.get(url, timeout=10)
                if res.status_code == 200:
                    for line in res.text.splitlines():
                        p = line.strip()
                        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5}$", p):
                            new_proxies.add(p)
            except Exception:
                continue

        with PROXIES_LOCK:
            if new_proxies:
                sample_size = min(len(new_proxies), 100)
                PROXIES_POOL = random.sample(list(new_proxies), sample_size)
                print(f"[✓] [SCRAPER] {len(PROXIES_POOL)} ताज़ा प्रॉक्सी लोड हुईं।")

        time.sleep(300)

# ----------------- Playwright Headless Browser Worker ----------------- #
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
]

async def open_view_in_browser(playwright, channel, post_id, proxy=None):
    proxy_settings = None
    if proxy:
        proxy_settings = {"server": f"http://{proxy}"}

    browser = None
    try:
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-first-run",
                "--no-zygote",
                "--single-process"
            ]
        )
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1280, "height": 720},
            proxy=proxy_settings
        )
        page = await context.new_page()

        # टेलीग्राम एम्बेड पेज लोड करना
        url = f"https://t.me/{channel}/{post_id}?embed=1"
        await page.goto(url, timeout=20000, wait_until="networkidle")
        
        # JS एक्जीक्यूट और व्यू ट्रिगर होने के लिए 2-3 सेकंड का स्वाभाविक ठहराव
        await asyncio.sleep(random.uniform(2.0, 3.5))
        
        await context.close()
        await browser.close()
        return True
    except Exception:
        if browser:
            await browser.close()
        return False

async def boost_views_playwright(channel, post_id, max_concurrency=10):
    with PROXIES_LOCK:
        proxies = list(PROXIES_POOL)
    
    if not proxies:
        proxies = [None] * 5

    print(f"\n[+] नई पोस्ट डिटेक्ट हुई -> ID: {post_id} | Playwright से असली JS रेंडरिंग शुरू...")
    
    success_count = 0
    async with async_playwright() as playwright:
        sem = asyncio.Semaphore(max_concurrency)

        async def worker(proxy):
            nonlocal success_count
            async with sem:
                res = await open_view_in_browser(playwright, channel, post_id, proxy)
                if res:
                    success_count += 1

        tasks = [worker(p) for p in proxies[:40]] # 40 ब्राउज़र कॉल्स
        await asyncio.gather(*tasks)

    print(f"[✓] पोस्ट {post_id} पर {success_count}/{min(len(proxies), 40)} सफल ब्राउज़र व्यूज रेंडर हुए!\n")

def get_latest_post_id(channel):
    url = f"https://t.me/s/{channel}"
    try:
        res = requests.get(url, headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            posts = soup.find_all('div', class_='tgme_widget_message')
            if posts:
                last_post = posts[-1]
                data_post = last_post.get('data-post')
                if data_post:
                    return int(data_post.split('/')[-1])
    except Exception:
        pass
    return None

async def main():
    channel = os.getenv("CHANNEL_NAME", "").replace('@', '').replace('https://t.me/', '').replace('https://t.me/s/', '')
    check_interval = int(os.getenv("CHECK_INTERVAL", 15))

    if not channel:
        print("[ERROR] CHANNEL_NAME मौजूद नहीं है!")
        return

    threading.Thread(target=scrape_fresh_proxies, daemon=True).start()
    await asyncio.sleep(5)

    print(f"[*] Playwright इंजन चालू: @{channel}")
    print(f"[*] हर {check_interval} सेकंड में नई पोस्ट चेक की जाएगी...\n")

    last_known_post_id = get_latest_post_id(channel)
    if last_known_post_id:
        print(f"[*] वर्तमान पोस्ट ID: {last_known_post_id}")

    while True:
        try:
            current_latest_id = get_latest_post_id(channel)
            if current_latest_id:
                if last_known_post_id is None:
                    last_known_post_id = current_latest_id
                elif current_latest_id > last_known_post_id:
                    for new_id in range(last_known_post_id + 1, current_latest_id + 1):
                        await boost_views_playwright(channel, new_id, max_concurrency=5)
                    last_known_post_id = current_latest_id
            
            await asyncio.sleep(check_interval)
        except KeyboardInterrupt:
            break
        except Exception:
            await asyncio.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_http_server, daemon=True).start()
    asyncio.run(main())
