import os
import re
import time
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# रैंडम User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
]

# ----------------- डमी वेब सर्वर (Render Web Service के लिए) ----------------- #
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Telegram View Bot is Running 24/7 on Render Web Service!")

    def log_message(self, format, *args):
        # डमी सर्वर के फालतू लॉग्स को कंसोल में आने से रोकना
        return

def run_http_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyServer)
    print(f"[*] Render Dummy HTTP Server listening on port {port}")
    server.serve_forever()

# ----------------- टेलीग्राम व्यू बॉट लॉजिक ----------------- #
def format_proxy(proxy_raw):
    p = proxy_raw.strip()
    if not p:
        return None
    if not (p.startswith("http://") or p.startswith("https://") or p.startswith("socks4://") or p.startswith("socks5://")):
        p = f"http://{p}"
    return {'http': p, 'https': p}

def process_view(channel, post, proxy_raw):
    proxy_dict = format_proxy(proxy_raw)
    if not proxy_dict:
        return False

    ua = random.choice(USER_AGENTS)
    headers = {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    }

    session = requests.Session()
    session.proxies.update(proxy_dict)
    
    retries = Retry(total=1, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    try:
        embed_url = f"https://t.me/{channel}/{post}?embed=1"
        res = session.get(embed_url, headers=headers, timeout=10)
        if res.status_code != 200:
            return False

        match = re.search(r'data-view="([^"]+)"', res.text)
        if not match:
            return False
        
        view_token = match.group(1)

        ajax_headers = {
            'User-Agent': ua,
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': embed_url,
            'Accept': '*/*'
        }
        
        view_url = f"https://t.me/{channel}/{post}?embed=1&view={view_token}"
        view_res = session.get(view_url, headers=ajax_headers, timeout=10)
        
        if view_res.status_code == 200:
            return True
        return False
    except Exception:
        return False
    finally:
        session.close()

def send_views_to_post(channel, post_id, proxies, max_workers=10):
    print(f"\n[+] नई पोस्ट डिटेक्ट हुई -> ID: {post_id} | व्यूज भेजना शुरू...")
    success_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_view, channel, post_id, proxy) for proxy in proxies]
        for f in futures:
            if f.result():
                success_count += 1
    print(f"[✓] पोस्ट {post_id} पर {success_count}/{len(proxies)} सफल व्यूज भेजे गए।")

def get_latest_post_id(channel):
    url = f"https://t.me/s/{channel}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            posts = soup.find_all('div', class_='tgme_widget_message')
            if posts:
                last_post = posts[-1]
                data_post = last_post.get('data-post')
                if data_post:
                    post_id = int(data_post.split('/')[-1])
                    return post_id
    except Exception as e:
        print(f"[!] पोस्ट चेक करने में एरर: {e}")
    return None

def load_proxies():
    if not os.path.exists('proxies.txt'):
        return []
    with open('proxies.txt', 'r', encoding='utf-8', errors='ignore') as f:
        return [line.strip() for line in f if line.strip()]

def main():
    channel = os.getenv("CHANNEL_NAME", "").replace('@', '').replace('https://t.me/', '').replace('https://t.me/s/', '')
    max_workers = int(os.getenv("THREADS", 10))
    check_interval = int(os.getenv("CHECK_INTERVAL", 15))

    if not channel:
        print("[ERROR] CHANNEL_NAME सेट नहीं किया गया है!")
        return

    proxies = load_proxies()
    if not proxies:
        print("[ERROR] proxies.txt में कोई प्रॉक्सी नहीं मिली!")
        return

    print(f"[*] चैनल मॉनिटरिंग चालू: @{channel}")
    print(f"[*] लोड की गई प्रॉक्सी: {len(proxies)} | थ्रेड्स: {max_workers}")
    print(f"[*] हर {check_interval} सेकंड में नई पोस्ट चेक की जाएगी...\n")

    last_known_post_id = get_latest_post_id(channel)
    if last_known_post_id:
        print(f"[*] वर्तमान नवीनतम पोस्ट ID: {last_known_post_id}")
    else:
        print("[!] चैनल का प्रारंभिक डेटा प्राप्त नहीं हो सका, पुनः प्रयास जारी रहेगा...")

    while True:
        try:
            current_latest_id = get_latest_post_id(channel)
            if current_latest_id:
                if last_known_post_id is None:
                    last_known_post_id = current_latest_id
                elif current_latest_id > last_known_post_id:
                    for new_id in range(last_known_post_id + 1, current_latest_id + 1):
                        send_views_to_post(channel, new_id, proxies, max_workers)
                    last_known_post_id = current_latest_id
            
            time.sleep(check_interval)
        except KeyboardInterrupt:
            print("\n[!] मॉनिटरिंग बंद की गई।")
            break
        except Exception as e:
            print(f"[!] लूप एरर: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # Render Web Service के पोर्ट बाइंडिंग के लिए डमी सर्वर थ्रेड
    server_thread = threading.Thread(target=run_http_server, daemon=True)
    server_thread.start()
    
    # मुख्य बॉट लूप
    main()
