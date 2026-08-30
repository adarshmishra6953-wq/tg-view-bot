import os
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# à¤°à¥ˆà¤‚à¤¡à¤® User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
]

def format_proxy(proxy_raw):
    """à¤ªà¥à¤°à¥‰à¤•à¥à¤¸à¥€ à¤¸à¥à¤Ÿà¥à¤°à¤¿à¤‚à¤— à¤•à¥‹ à¤¸à¤¹à¥€ URL à¤«à¥‰à¤°à¥à¤®à¥‡à¤Ÿ à¤®à¥‡à¤‚ à¤¤à¥ˆà¤¯à¤¾à¤° à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ"""
    p = proxy_raw.strip()
    if not p:
        return None
    if not (p.startswith("http://") or p.startswith("https://") or p.startswith("socks4://") or p.startswith("socks5://")):
        p = f"http://{p}"
    return {'http': p, 'https': p}

def process_view(channel, post, proxy_raw):
    """à¤ªà¥à¤°à¤¤à¥à¤¯à¥‡à¤• à¤ªà¥à¤°à¥‰à¤•à¥à¤¸à¥€ à¤•à¥‡ à¤²à¤¿à¤ à¤¸à¥‡à¤¶à¤¨ à¤¬à¤¨à¤¾à¤•à¤° à¤µà¥à¤¯à¥‚ à¤°à¤¿à¤•à¥à¤µà¥‡à¤¸à¥à¤Ÿ à¤­à¥‡à¤œà¤¤à¤¾ à¤¹à¥ˆ"""
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

def send_views_to_post(channel, post_id, proxies, max_workers=50):
    """à¤¦à¤¿à¤ à¤—à¤ à¤ªà¥‹à¤¸à¥à¤Ÿ ID à¤ªà¤° à¤¸à¤­à¥€ à¤ªà¥à¤°à¥‰à¤•à¥à¤¸à¥€à¤œ à¤¸à¥‡ à¤µà¥à¤¯à¥‚à¤œ à¤­à¥‡à¤œà¤¤à¤¾ à¤¹à¥ˆ"""
    print(f"\n[+] à¤¨à¤ˆ à¤ªà¥‹à¤¸à¥à¤Ÿ à¤®à¤¿à¤²à¥€ -> ID: {post_id} | à¤µà¥à¤¯à¥‚à¤œ à¤­à¥‡à¤œà¤¨à¤¾ à¤¶à¥à¤°à¥‚ à¤¹à¥‹ à¤°à¤¹à¤¾ à¤¹à¥ˆ...")
    success_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_view, channel, post_id, proxy) for proxy in proxies]
        for f in futures:
            if f.result():
                success_count += 1
    print(f"[âœ“] à¤ªà¥‹à¤¸à¥à¤Ÿ {post_id} à¤ªà¤° {success_count}/{len(proxies)} à¤¸à¤«à¤² à¤µà¥à¤¯à¥‚à¤œ à¤­à¥‡à¤œà¥‡ à¤—à¤à¥¤")

def get_latest_post_id(channel):
    """à¤šà¥ˆà¤¨à¤² à¤•à¥‡ à¤µà¥‡à¤¬ à¤ªà¥à¤°à¥€à¤µà¥à¤¯à¥‚ à¤ªà¥‡à¤œ à¤¸à¥‡ à¤¨à¤µà¥€à¤¨à¤¤à¤® à¤ªà¥‹à¤¸à¥à¤Ÿ ID à¤¨à¤¿à¤•à¤¾à¤²à¤¤à¤¾ à¤¹à¥ˆ"""
    url = f"https://t.me/s/{channel}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # à¤Ÿà¥‡à¤²à¥€à¤—à¥à¤°à¤¾à¤® à¤µà¥‡à¤¬ à¤ªà¥‡à¤œ à¤ªà¤° à¤¹à¤° à¤ªà¥‹à¤¸à¥à¤Ÿ à¤•à¤¾ à¤Ÿà¥ˆà¤— tgme_widget_message à¤¹à¥‹à¤¤à¤¾ à¤¹à¥ˆ
            posts = soup.find_all('div', class_='tgme_widget_message')
            if posts:
                # à¤¸à¤¬à¤¸à¥‡ à¤†à¤–à¤¿à¤°à¥€ à¤ªà¥‹à¤¸à¥à¤Ÿ à¤¸à¥‡ ID à¤¨à¤¿à¤•à¤¾à¤²à¤¨à¤¾ (format: channel/1234)
                last_post = posts[-1]
                data_post = last_post.get('data-post')
                if data_post:
                    post_id = int(data_post.split('/')[-1])
                    return post_id
    except Exception as e:
        print(f"[!] à¤ªà¥‹à¤¸à¥à¤Ÿ à¤šà¥‡à¤• à¤•à¤°à¤¨à¥‡ à¤®à¥‡à¤‚ à¤à¤°à¤°: {e}")
    return None

def load_proxies():
    """proxies.txt à¤¸à¥‡ à¤ªà¥à¤°à¥‰à¤•à¥à¤¸à¥€ à¤²à¥‹à¤¡ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ"""
    if not os.path.exists('proxies.txt'):
        return []
    with open('proxies.txt', 'r', encoding='utf-8', errors='ignore') as f:
        return [line.strip() for line in f if line.strip()]

def main():
    channel = os.getenv("CHANNEL_NAME", "").replace('@', '').replace('https://t.me/', '').replace('https://t.me/s/', '')
    max_workers = int(os.getenv("THREADS", 50))
    check_interval = int(os.getenv("CHECK_INTERVAL", 15)) # à¤¹à¤° à¤•à¤¿à¤¤à¤¨à¥‡ à¤¸à¥‡à¤•à¤‚à¤¡ à¤®à¥‡à¤‚ à¤šà¥‡à¤• à¤•à¤°à¥‡

    if not channel:
        print("[ERROR] CHANNEL_NAME à¤¸à¥‡à¤Ÿ à¤¨à¤¹à¥€à¤‚ à¤•à¤¿à¤¯à¤¾ à¤—à¤¯à¤¾ à¤¹à¥ˆ!")
        return

    proxies = load_proxies()
    if not proxies:
        print("[ERROR] proxies.txt à¤®à¥‡à¤‚ à¤•à¥‹à¤ˆ à¤ªà¥à¤°à¥‰à¤•à¥à¤¸à¥€ à¤¨à¤¹à¥€à¤‚ à¤®à¤¿à¤²à¥€!")
        return

    print(f"[*] à¤šà¥ˆà¤¨à¤² à¤®à¥‰à¤¨à¤¿à¤Ÿà¤°à¤¿à¤‚à¤— à¤šà¤¾à¤²à¥‚: @{channel}")
    print(f"[*] à¤²à¥‹à¤¡ à¤•à¥€ à¤—à¤ˆ à¤ªà¥à¤°à¥‰à¤•à¥à¤¸à¥€: {len(proxies)} | à¤¥à¥à¤°à¥‡à¤¡à¥à¤¸: {max_workers}")
    print(f"[*] à¤¹à¤° {check_interval} à¤¸à¥‡à¤•à¤‚à¤¡ à¤®à¥‡à¤‚ à¤¨à¤ˆ à¤ªà¥‹à¤¸à¥à¤Ÿ à¤šà¥‡à¤• à¤•à¥€ à¤œà¤¾à¤à¤—à¥€...\n")

    # à¤¶à¥à¤°à¥à¤†à¤¤à¥€ à¤²à¥‡à¤Ÿà¥‡à¤¸à¥à¤Ÿ à¤ªà¥‹à¤¸à¥à¤Ÿ ID à¤ªà¥à¤°à¤¾à¤ªà¥à¤¤ à¤•à¤°à¤¨à¤¾
    last_known_post_id = get_latest_post_id(channel)
    if last_known_post_id:
        print(f"[*] à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤¨à¤µà¥€à¤¨à¤¤à¤® à¤ªà¥‹à¤¸à¥à¤Ÿ ID: {last_known_post_id}")
    else:
        print("[!] à¤šà¥ˆà¤¨à¤² à¤•à¤¾ à¤ªà¥à¤°à¤¾à¤°à¤‚à¤­à¤¿à¤• à¤¡à¥‡à¤Ÿà¤¾ à¤ªà¥à¤°à¤¾à¤ªà¥à¤¤ à¤¨à¤¹à¥€à¤‚ à¤¹à¥‹ à¤¸à¤•à¤¾, à¤ªà¥à¤¨à¤ƒ à¤ªà¥à¤°à¤¯à¤¾à¤¸ à¤œà¤¾à¤°à¥€ à¤°à¤¹à¥‡à¤—à¤¾...")

    while True:
        try:
            current_latest_id = get_latest_post_id(channel)
            if current_latest_id:
                if last_known_post_id is None:
                    last_known_post_id = current_latest_id
                elif current_latest_id > last_known_post_id:
                    # à¤¯à¤¦à¤¿ à¤à¤• à¤¸à¥‡ à¤…à¤§à¤¿à¤• à¤ªà¥‹à¤¸à¥à¤Ÿ à¤† à¤—à¤ˆ à¤¹à¥‹à¤‚ à¤¤à¥‹ à¤•à¥à¤°à¤®à¤µà¤¾à¤° à¤¸à¤­à¥€ à¤ªà¤° à¤µà¥à¤¯à¥‚à¤œ à¤­à¥‡à¤œà¤¨à¤¾
                    for new_id in range(last_known_post_id + 1, current_latest_id + 1):
                        send_views_to_post(channel, new_id, proxies, max_workers)
                    last_known_post_id = current_latest_id
            
            time.sleep(check_interval)
        except KeyboardInterrupt:
            print("\n[!] à¤®à¥‰à¤¨à¤¿à¤Ÿà¤°à¤¿à¤‚à¤— à¤¬à¤‚à¤¦ à¤•à¥€ à¤—à¤ˆà¥¤")
            break
        except Exception as e:
            print(f"[!] à¤²à¥‚à¤ª à¤à¤°à¤°: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
