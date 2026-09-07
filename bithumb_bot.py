import time
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ================= 설정 영역 =================
TELEGRAM_BOT_TOKEN = "8698073846:AAGmv-TJQl-5l4u3D476XJ_0yiMcVd2GyTc"
TELEGRAM_CHAT_ID = "8767647660"

CHECK_INTERVAL = 60                
MIN_PRICE_JUMP = 1.8               
MIN_TRADE_VALUE_KRW = 300_000_000 
COOLDOWN_SECONDS = 900             
# ============================================

# Render 무료 웹 서비스 유지를 위한 가짜 웹 서버
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_fake_server():
    server = HTTPServer(("0.0.0.0", 10000), HealthCheckHandler)
    server.serve_forever()

def send_telegram_alert(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[알림 전송 실패]: {e}")

def get_bithumb_all_tickers():
    url = "https://api.bithumb.com/public/ticker/ALL_KRW"
    try:
        res = requests.get(url, timeout=5)
        res_json = res.json()
        if res_json.get("status") == "0000":
            return res_json.get("data", {})
    except Exception as e:
        print(f"[API 조회 오류]: {e}")
    return {}

def run_crypto_scanner():
    prev_prices = {}
    last_alert_time = {}

    print("🚀 [빗썸 급등 포착 봇 가동] 감시 시작...")
    send_telegram_alert("🚀 *[빗썸 알림 봇 활성화]*\n무료 클라우드 감시를 시작합니다.")

    while True:
        data = get_bithumb_all_tickers()
        current_time = time.time()

        if data:
            for coin_symbol, info in data.items():
                if coin_symbol == "date":
                    continue
                try:
                    current_price = float(info["closing_price"])
                    trade_value_24h = float(info["acc_trade_value_24H"])
                    daily_change_rate = float(info["fluctate_rate_24H"])

                    if trade_value_24h < MIN_TRADE_VALUE_KRW:
                        continue

                    if coin_symbol in prev_prices:
                        prev_p = prev_prices[coin_symbol]
                        instant_surge_pct = ((current_price - prev_p) / prev_p) * 100
                        is_cooldown = (current_time - last_alert_time.get(coin_symbol, 0)) < COOLDOWN_SECONDS

                        if instant_surge_pct >= MIN_PRICE_JUMP and not is_cooldown:
                            msg = (
                                f"🚨 *[빗썸 급등 포착]*\n"
                                f"• 종목: *{coin_symbol}/KRW*\n"
                                f"• 현재가: {current_price:,.2f}원\n"
                                f"• 단기 변동률: *+{instant_surge_pct:.2f}%*\n"
                                f"• 당일 누적 변동률: {daily_change_rate:+.2f}%\n"
                                f"• 24시간 거래대금: {trade_value_24h / 100_000_000:,.1f}억원"
                            )
                            send_telegram_alert(msg)
                            last_alert_time[coin_symbol] = current_time

                    prev_prices[coin_symbol] = current_price
                except Exception:
                    continue

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # 백그라운드에서 가짜 웹 서버 실행 (Render 무료 조건 통과용)
    threading.Thread(target=run_fake_server, daemon=True).start()
    run_crypto_scanner()
