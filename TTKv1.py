#!/usr/bin/env python3
# TikTok Kit v2.5 - Standalone CLI with Mandatory TikTok OAuth Login
# Kompatibel Termux. Install: pip install requests cryptography pyjwt
# Catatan: Login TikTok OAuth wajib untuk semua fitur. Bayar Rp 25.000 ke OVO 081391235364.

import requests
import getpass
import json
import os
import time
import sys
import base64
from datetime import datetime
from cryptography.fernet import Fernet
import jwt
import hmac
import hashlib

# Konfigurasi
DATA_FILE = os.path.expanduser('~/.tiktok_kit_data.json')
KEY_FILE = os.path.expanduser('~/.tiktok_kit_key.key')
TIKTOK_API_BASE = "https://business-api.tiktok.com/open_api/v1.3"
TIKTOK_OAUTH_BASE = "https://open.tiktokapis.com/v2/oauth"
YOUR_OVO_NUMBER = "081391235364"
PAYMENT_AMOUNT = 25000

# Generate Fernet key jika belum ada
if not os.path.exists(KEY_FILE):
    key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as f:
        f.write(key)

with open(KEY_FILE, 'rb') as f:
    fernet = Fernet(f.read())

# Warna ANSI
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# ASCII Art Header
ASCII_ART = f"""
{Colors.HEADER}{Colors.BOLD}
  ____          _ _       
 |  _ \\ __ _   | (_)_ __  
 | |_) / _` |  | | | '_ \\ 
 |  __/ (_| |  | | | | | |
 |_|   \\__,_|  |_|_|_| |_|
 
             v2.5 - TikTok Kit Tool
{Colors.ENDC}
"""

# Border untuk Menu
BORDER = f"{Colors.OKBLUE}╔{'═' * 50}╗{Colors.ENDC}"
BORDER_LINE = f"{Colors.OKBLUE}║{' ' * 50}║{Colors.ENDC}"
BORDER_END = f"{Colors.OKBLUE}╚{'═' * 50}╝{Colors.ENDC}"

def print_header():
    print(ASCII_ART)

def print_menu_border(title):
    print(BORDER)
    print(f"{Colors.OKBLUE}║{Colors.BOLD} {title.center(48)} {Colors.ENDC}{Colors.OKBLUE}║{Colors.ENDC}")
    print(BORDER_LINE)

def loading_spinner(msg, duration=2):
    print(f"{Colors.WARNING}{msg} ", end='', flush=True)
    spinner = "|/-\\"
    for _ in range(duration * 10):
        for char in spinner:
            sys.stdout.write(f"\r{Colors.WARNING}{msg} {char}{Colors.ENDC}")
            sys.stdout.flush()
            time.sleep(0.1)
    print(f"\r{Colors.OKGREEN}{msg} ✓{Colors.ENDC}")

def encrypt_data(data):
    json_str = json.dumps(data)
    encrypted = fernet.encrypt(json_str.encode())
    with open(DATA_FILE, 'wb') as f:
        f.write(encrypted)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'rb') as f:
            encrypted = f.read()
        try:
            decrypted = fernet.decrypt(encrypted).decode()
            return json.loads(decrypted)
        except Exception:
            return {}
    return {"users": {}, "analyses": [], "payments": {}}

def get_user_data(username):
    data = load_data()
    return data["users"].get(username, {})

def show_dashboard(username):
    print(f"{Colors.OKBLUE}=== DASHBOARD ==={Colors.ENDC}")
    data = load_data()
    analyses = data.get("analyses", [])
    loading_spinner("Memuat dashboard...")
    print(f"{Colors.BOLD}Total Analisis: {len(analyses)}{Colors.ENDC}")
    print(f"{Colors.BOLD}Recent Analyses:{Colors.ENDC}")
    for item in analyses[-5:]:
        print(f"  - {item['type']} on {item['date'][:10]}: {item['summary'][:50]}...")

def generate_content(username):
    print(f"{Colors.OKBLUE}=== GENERATE CONTENT ==={Colors.ENDC}")
    product_desc = input("Silahkan masukkan deskripsi produk: ").strip()
    niche = input("Silahkan masukkan niche: ").strip()
    target_audience = input("Silahkan masukkan target audience: ").strip()
    if not all([product_desc, niche, target_audience]):
        print(f"{Colors.FAIL}Semua field harus diisi!{Colors.ENDC}")
        return
    loading_spinner("Menghasilkan konten...")
    content = {
        "ideas": [f"Idea untuk {niche}", f"Promosi {product_desc}"],
        "script": f"Script untuk {product_desc} target {target_audience}",
        "captions": [f"Check {product_desc}!", f"Promo {niche}!"],
        "hashtags": ["#promo", f"#{niche}"]
    }
    data = load_data()
    data["analyses"].append({
        "type": "content_generation",
        "date": datetime.now().isoformat(),
        "summary": f"Generated for {product_desc}",
        "data": content
    })
    encrypt_data(data)
    print(f"{Colors.OKGREEN}Konten berhasil digenerate!{Colors.ENDC}")
    print(f"{Colors.BOLD}Ideas: {', '.join(content['ideas'])}{Colors.ENDC}")
    print(f"{Colors.BOLD}Script: {content['script'][:100]}...{Colors.ENDC}")

def analyze_video(username):
    print(f"{Colors.OKBLUE}=== ANALYZE VIDEO ==={Colors.ENDC}")
    video_url = input("Silahkan masukkan URL video TikTok: ").strip()
    niche = input("Silahkan masukkan niche (opsional): ").strip() or None
    loading_spinner("Menganalisis video...")
    analysis = {"video_data": {"views": 0, "likes": 0}, "analysis": f"Analisis untuk {video_url} di niche {niche}"}
    data = load_data()
    data["analyses"].append({
        "type": "video_analysis",
        "date": datetime.now().isoformat(),
        "summary": f"Analyzed {video_url}",
        "data": analysis
    })
    encrypt_data(data)
    print(f"{Colors.OKGREEN}Analisis OK! Periksa data manual.{Colors.ENDC}")

def performance_tracking(username):
    print(f"{Colors.OKBLUE}=== PERFORMANCE ==={Colors.ENDC}")
    loading_spinner("Memuat performa...")
    data = load_data()
    analyses = data.get("analyses", [])
    for item in analyses[-5:]:
        print(f"  - {item['type']}: {item['summary'][:50]}...")

def account_management(username):
    print(f"{Colors.OKBLUE}=== ACCOUNT ==={Colors.ENDC}")
    data = load_data()
    user_data = data["users"].get(username, {})
    tier = user_data.get("tier", "basic")
    loading_spinner("Memuat akun...")
    print(f"{Colors.BOLD}Tier: {tier}{Colors.ENDC}")
    print(f"{Colors.BOLD}Status Pembayaran: {'Lunas' if user_data.get('paid', False) else 'Belum Lunas'}{Colors.ENDC}")
    choice = input("1. Upgrade Tier | 2. Logout: ").strip()
    if choice == '1':
        new_tier = input("Pilih tier (pro/enterprise): ").strip()
        if new_tier in ["pro", "enterprise"]:
            user_data["tier"] = new_tier
            encrypt_data(data)
            print(f"{Colors.OKGREEN}Tier diupgrade ke {new_tier}!{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}Tier tidak valid!{Colors.ENDC}")
    elif choice == '2':
        logout(username)

def set_credentials():
    print(f"{Colors.OKBLUE}=== SET KREDENSIAL ==={Colors.ENDC}")
    loading_spinner("Memuat kredensial lama...")
    data = load_data()
    creds = data.get("creds", {})
    
    print(f"{Colors.WARNING}Cara dapatkan kredensial:{Colors.ENDC}")
    print(f"- TikTok: Daftar di https://business.tiktok.com/, dapatkan APP_ID, APP_SECRET, ADVERTISER_ID setelah approval.")
    print(f"- OVO: Tidak diperlukan untuk API, bayar manual ke {YOUR_OVO_NUMBER} sebesar Rp {PAYMENT_AMOUNT:,}.")
    
    creds['tiktok_app_id'] = input("Silahkan masukkan TikTok APP ID: ").strip()
    creds['tiktok_app_secret'] = getpass.getpass("Silahkan masukkan TikTok APP Secret: ")
    creds['tiktok_advertiser_id'] = input("Silahkan masukkan TikTok Advertiser ID: ").strip()
    
    if not all([creds.get(k) for k in ['tiktok_app_id', 'tiktok_app_secret', 'tiktok_advertiser_id']]):
        print(f"{Colors.FAIL}Semua kredensial TikTok wajib diisi!{Colors.ENDC}")
        return
    data["creds"] = creds
    encrypt_data(data)
    print(f"{Colors.OKGREEN}Kredensial TikTok disimpan aman!{Colors.ENDC}")

def verify_payment(username):
    data = load_data()
    user_data = data["users"].get(username, {})
    if user_data.get("paid", False):
        return True
    
    print(f"{Colors.OKBLUE}=== VERIFIKASI PEMBAYARAN ==={Colors.ENDC}")
    print(f"{Colors.WARNING}Langkah-langkah pembayaran:{Colors.ENDC}")
    print(f"1. Buka aplikasi OVO Anda.")
    print(f"2. Transfer Rp {PAYMENT_AMOUNT:,} ke nomor OVO {YOUR_OVO_NUMBER}.")
    print(f"3. Catat waktu transfer, jumlah, dan kode transaksi (jika ada).")
    print(f"4. Pemilik (Anda) akan memverifikasi pembayaran secara manual.")
    
    transaction_time = input("Silahkan masukkan waktu transfer (YYYY-MM-DD HH:MM): ").strip()
    amount = int(input(f"Silahkan masukkan jumlah (harus Rp {PAYMENT_AMOUNT:,}): ").strip())
    transaction_code = input("Silahkan masukkan kode transaksi (jika ada): ").strip()
    proof_path = input("Silahkan masukkan path file bukti transfer (contoh: /sdcard/proof.jpg): ").strip()
    
    if amount != PAYMENT_AMOUNT:
        print(f"{Colors.FAIL}Jumlah salah! Harus Rp {PAYMENT_AMOUNT:,}.{Colors.ENDC}")
        return False
    
    data["payments"][username] = {
        "transaction_time": transaction_time,
        "amount": amount,
        "transaction_code": transaction_code,
        "proof_path": proof_path,
        "verified": False
    }
    encrypt_data(data)
    print(f"{Colors.WARNING}Bukti pembayaran disimpan. Tunggu verifikasi dari pemilik (nomor {YOUR_OVO_NUMBER}).{Colors.ENDC}")
    print(f"{Colors.BOLD}Catatan: Pemilik akan memeriksa pembayaran di OVO dan mengonfirmasi. Hubungi jika perlu.{Colors.ENDC}")
    return False

def tiktok_oauth_login():
    data = load_data()
    creds = data.get("creds", {})
    if not creds.get('tiktok_app_id') or not creds.get('tiktok_app_secret'):
        print(f"{Colors.FAIL}Set kredensial TikTok dulu di menu 9!{Colors.ENDC}")
        return
    
    # Minta username jika belum ada
    if not data.get("current_user"):
        username = input("Silahkan masukkan username unik untuk sesi ini: ").strip()
        data["current_user"] = username
        encrypt_data(data)
    else:
        username = data["current_user"]
    
    print(f"{Colors.OKBLUE}=== LOGIN TIKTOK OAUTH ==={Colors.ENDC}")
    print(f"{Colors.WARNING}Langkah-langkah:{Colors.ENDC}")
    print("1. Buka URL berikut di browser Anda (gunakan termux-open-url jika di Termux).")
    print("2. Login ke akun TikTok Anda.")
    print("3. Salin code authorization dari URL redirect setelah login.")
    print("4. Masukkan code di sini.")
    
    auth_url = f"{TIKTOK_OAUTH_BASE}/authorize/?client_key={creds['tiktok_app_id']}&scope=user.info.basic,video.list,ads.manage&response_type=code&redirect_uri=http://localhost:8000/callback&state={username}"
    print(f"{Colors.BOLD}Buka URL ini: {auth_url}{Colors.ENDC}")
    input("Tekan Enter setelah membuka URL dan login...")
    
    auth_code = input("Silahkan masukkan authorization code: ").strip()
    if not auth_code:
        print(f"{Colors.FAIL}Code tidak valid!{Colors.ENDC}")
        return
    
    loading_spinner("Menukar code dengan access token...")
    exchange_data = {
        "client_key": creds['tiktok_app_id'],
        "client_secret": creds['tiktok_app_secret'],
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": "http://localhost:8000/callback"
    }
    try:
        resp = requests.post(f"{TIKTOK_OAUTH_BASE}/token/", json=exchange_data)
        resp.raise_for_status()
        token_data = resp.json()
        access_token = token_data.get("access_token")
        if access_token:
            # Validasi token dengan panggilan API
            loading_spinner("Memvalidasi token...")
            val_resp = requests.get(f"{TIKTOK_OAUTH_BASE}/user/info/?access_token={access_token}")
            if val_resp.status_code == 200:
                data["users"][username] = {
                    "tiktok_access_token": access_token,
                    "tier": "basic",
                    "login_time": datetime.now().isoformat(),
                    "paid": False
                }
                data["current_user"] = username
                encrypt_data(data)
                print(f"{Colors.OKGREEN}Login TikTok OAuth berhasil! Token valid. Selamat datang, {username}.{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}Token tidak valid. Periksa kredensial.{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}Gagal mendapatkan token.{Colors.ENDC}")
    except requests.exceptions.RequestException as e:
        print(f"{Colors.FAIL}Error OAuth: {e}{Colors.ENDC}")

def analyze_fyp_keyword(username):
    data = load_data()
    user_data = data["users"].get(username, {})
    if not user_data.get('tiktok_access_token'):
        print(f"{Colors.FAIL}Login TikTok OAuth dulu di menu 1!{Colors.ENDC}")
        return
    
    print(f"{Colors.OKBLUE}=== ANALISIS FYP/KEYWORD INDONESIA ==={Colors.ENDC}")
    keyword = input("Silahkan masukkan keyword untuk analisis (misal: fashion indonesia): ").strip()
    loading_spinner("Menganalisis tren FYP dan keyword...")
    
    headers = {
        "Access-Token": user_data['tiktok_access_token'],
        "Content-Type": "application/json"
    }
    params = {
        "region": "ID",
        "keyword": keyword,
        "limit": 20
    }
    try:
        resp = requests.get(f"{TIKTOK_API_BASE}/trending/hashtags/", headers=headers, params=params)
        resp.raise_for_status()
        trends = resp.json().get("data", [])
        print(f"{Colors.OKGREEN}Tren FYP/Keyword Populer di Indonesia:{Colors.ENDC}")
        for trend in trends[:10]:
            print(f"  - #{trend['name']}: Views ~{trend.get('views', 0):,}, Posts ~{trend.get('posts', 0):,}")
    except requests.exceptions.RequestException as e:
        print(f"{Colors.FAIL}Error analisis: {e}{Colors.ENDC}")

def promosi_menu(username):
    data = load_data()
    creds = data.get("creds", {})
    user_data = data["users"].get(username, {})
    if not user_data.get('tiktok_access_token'):
        print(f"{Colors.FAIL}Login TikTok OAuth dulu di menu 1!{Colors.ENDC}")
        return
    if not all([creds.get(k) for k in ['tiktok_app_id', 'tiktok_app_secret', 'tiktok_advertiser_id']]):
        print(f"{Colors.FAIL}Set kredensial TikTok dulu di menu 9!{Colors.ENDC}")
        return
    if not user_data.get("paid", False):
        if not verify_payment(username):
            return
    
    target, video_url, pkg = None, None, None
    while True:
        print_menu_border("PROMOSI TIKTOK")
        print(f"{Colors.OKBLUE}1. Pilih Target{Colors.ENDC}")
        print(f"{Colors.OKBLUE}2. Pilih Materi Iklan{Colors.ENDC}")
        print(f"{Colors.OKBLUE}3. Pilih Paket{Colors.ENDC}")
        print(f"{Colors.OKBLUE}4. Buat Kampanye{Colors.ENDC}")
        print(f"{Colors.OKBLUE}0. Back{Colors.ENDC}")
        choice = input(f"{Colors.WARNING}Pilih (0-4): {Colors.ENDC}").strip()
        
        if choice == '1':
            targets = {'1': 'TRAFFIC', '2': 'ENGAGEMENT', '3': 'FOLLOWERS'}
            for k, v in targets.items():
                print(f"{k}. {v.lower().replace('_', ' ')}")
            target = targets.get(input("Silahkan masukkan nomor: ").strip(), 'TRAFFIC')
            print(f"{Colors.OKGREEN}Target: {target.lower()}{Colors.ENDC}")
        elif choice == '2':
            video_url = input("Silahkan masukkan URL video TikTok: ").strip()
            print(f"{Colors.OKGREEN}Video: {video_url}{Colors.ENDC}")
        elif choice == '3':
            packages = {'1': 'basic', '2': 'pro'}
            for k, v in packages.items():
                print(f"{k}. {v} (Rp {1790 if v == 'basic' else 15000})")
            pkg = packages.get(input("Silahkan masukkan nomor: ").strip(), 'basic')
            print(f"{Colors.OKGREEN}Paket: {pkg} (Rp {15000 if pkg == 'pro' else 1790}){Colors.ENDC}")
        elif choice == '4':
            if not all([target, video_url, pkg]):
                print(f"{Colors.FAIL}Isi target, materi iklan, dan paket dulu!{Colors.ENDC}")
                continue
            loading_spinner("Membuat kampanye TikTok...")
            campaign_data = {
                "advertiser_id": creds['tiktok_advertiser_id'],
                "campaign_name": f"Promo_{username}_{datetime.now().strftime('%Y%m%d')}",
                "budget": 15000 if pkg == 'pro' else 1790,
                "objective": target,
                "video_url": video_url
            }
            headers = {
                "Access-Token": user_data['tiktok_access_token'],
                "Content-Type": "application/json"
            }
            try:
                resp = requests.post(f"{TIKTOK_API_BASE}/advertiser/campaign/create/", json=campaign_data, headers=headers)
                resp.raise_for_status()
                campaign_id = resp.json().get("data", {}).get("campaign_id")
                if campaign_id:
                    data["analyses"].append({
                        "type": "promotion",
                        "date": datetime.now().isoformat(),
                        "summary": f"Promosi {target} untuk {video_url}",
                        "data": {"campaign_id": campaign_id, "cost": campaign_data['budget']}
                    })
                    encrypt_data(data)
                    print(f"{Colors.OKGREEN}Promosi sukses! Campaign ID: {campaign_id}, Cost: Rp {campaign_data['budget']:,}{Colors.ENDC}")
                else:
                    print(f"{Colors.FAIL}Gagal membuat kampanye TikTok.{Colors.ENDC}")
            except requests.exceptions.RequestException as e:
                print(f"{Colors.FAIL}Error TikTok API: {e}{Colors.ENDC}")
        elif choice == '0':
            break
        input(f"{Colors.OKBLUE}Enter untuk lanjut...{Colors.ENDC}")

def logout(username):
    data = load_data()
    if username in data["users"]:
        del data["users"][username]
    data["current_user"] = None
    encrypt_data(data)
    print(f"{Colors.OKGREEN}Logout berhasil.{Colors.ENDC}")

def main_menu():
    while True:
        print_header()
        print_menu_border("MENU UTAMA V2.5")
        print(f"{Colors.OKBLUE}1. Login TikTok OAuth (Wajib untuk Semua Fitur){Colors.ENDC}")
        print(f"{Colors.OKBLUE}2. Dashboard{Colors.ENDC}")
        print(f"{Colors.OKBLUE}3. Generate Content{Colors.ENDC}")
        print(f"{Colors.OKBLUE}4. Analyze Video{Colors.ENDC}")
        print(f"{Colors.OKBLUE}5. Performance Tracking{Colors.ENDC}")
        print(f"{Colors.OKBLUE}6. Account Management{Colors.ENDC}")
        print(f"{Colors.OKBLUE}7. Logout{Colors.ENDC}")
        print(f"{Colors.OKBLUE}8. Promosi TikTok{Colors.ENDC}")
        print(f"{Colors.OKBLUE}9. Set Kredensial{Colors.ENDC}")
        print(f"{Colors.OKBLUE}10. Analisis FYP/Keyword Indonesia{Colors.ENDC}")
        print(f"{Colors.OKBLUE}0. Exit{Colors.ENDC}")
        print(BORDER_END)
        choice = input(f"{Colors.WARNING}Pilih (0-10): {Colors.ENDC}").strip()
        data = load_data()
        current_user = data.get("current_user")
        user_data = get_user_data(current_user) if current_user else {}
        token = user_data.get("tiktok_access_token")

        if choice == '1':
            tiktok_oauth_login()
        elif choice in ['2', '3', '4', '5', '6', '8', '10']:
            if not current_user or not token:
                print(f"{Colors.FAIL}Login TikTok OAuth dulu di menu 1!{Colors.ENDC}")
                continue
            if choice == '2':
                show_dashboard(current_user)
            elif choice == '3':
                generate_content(current_user)
            elif choice == '4':
                analyze_video(current_user)
            elif choice == '5':
                performance_tracking(current_user)
            elif choice == '6':
                account_management(current_user)
            elif choice == '8':
                promosi_menu(current_user)
            elif choice == '10':
                analyze_fyp_keyword(current_user)
        elif choice == '7' and current_user:
            logout(current_user)
        elif choice == '9':
            set_credentials()
        elif choice == '0':
            print(f"{Colors.OKGREEN}Terima kasih! Sampai jumpa.{Colors.ENDC}")
            break
        else:
            print(f"{Colors.FAIL}Pilihan tidak valid atau belum login!{Colors.ENDC}")
        input(f"\n{Colors.OKBLUE}Enter untuk menu...{Colors.ENDC}")

if __name__ == "__main__":
    main_menu()