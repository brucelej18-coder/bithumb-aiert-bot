import time
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ================= 설정 영역 =================
TELEGRAM_BOT_TOKEN = "8698073846:AAGmv-TJQl-5l4u3D476XJ_0yiMcVd2GyTc"
TELEGRAM_CHAT_ID = "8767647660"

CHECK_INTERVAL = 60                 # 감지 주기 (60초)
MIN_TRADE_VALUE_KRW = 1_000_000_000 # 24시간 거래대금 10억원 이상 종목만 (잡코인 제외 기준 강화)
COOLDOWN_SECONDS = 1800             # 동일 종목 재알림 방지 쿨다운 (30분으로 확대)

# 알림 단계별 기준 (%)
LEVEL_1_PUMP = 2.5   # [주의] 1분간 +2.5% 이상 상승
LEVEL_2_SURGE = 4.5  # [급등] 1분간 +4.5% 이상 상승
LEVEL_3_ROCKET = 8.0 # [폭등] 1분간 +8.0% 이상 폭등
# ============================================

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
    prev_volumes = {}
    last_alert_time = {}

    print("🚀 [빗썸 세분화 감시 봇 가동] 필터링 시작...")
    send_telegram_alert("⚙️ *[빗썸 정밀 감시 봇 가동]*\n• 거래대금 10억 이상\n• 3단계 강도별 세분화 알림 적용 완료")

    while True:
        data = get_bithumb_all_tickers()
        current_time = time.time()

        if data:
            for coin_symbol, info in data.items():
                if coin_symbol == "date":
                    continue

                try:
                    current_price = float(info["closing_price"])
                    total_units_traded = float(info["units_traded_24H"])
                    trade_value_24h = float(info["acc_trade_value_24H"])
                    daily_change_rate = float(info["fluctate_rate_24H"])

                    # 1. 거래대금 10억원 미만 소형주는 원천 차단
                    if trade_value_24h < MIN_TRADE_VALUE_KRW:
                        continue

                    # 2. 직전 1분 대비 변동 분석
                    if coin_symbol in prev_prices and coin_symbol in prev_volumes:
                        prev_p = prev_prices[coin_symbol]
                        prev_v = prev_volumes[coin_symbol]

                        instant_surge_pct = ((current_price - prev_p) / prev_p) * 100
                        vol_diff = total_units_traded - prev_v  # 지난 1분간 체결된 코인 수량
                        recent_1m_value_krw = vol_diff * current_price  # 지난 1분간 거래금액 추산

                        is_cooldown = (current_time - last_alert_time.get(coin_symbol, 0)) < COOLDOWN_SECONDS

                        # 최소 1분간 거래대금이 3천만원 이상 터지면서 가격이 오른 경우만 필터링
                        if instant_surge_pct >= LEVEL_1_PUMP and not is_cooldown and recent_1m_value_krw >= 30_000_000:
                            
                            # 알림 단계 판정
                            if instant_surge_pct >= LEVEL_3_ROCKET:
                                level_tag = "🚨🚨 [3단계: 거래량 폭발 & 대량 급등]"
                            elif instant_surge_pct >= LEVEL_2_SURGE:
                                level_tag = "🔥 [2단계: 본격 수급 유입 급등]"
                            else:
                                level_tag = "👀 [1단계: 거래량 실린 시동 감지]"

                            msg = (
                                f"{level_tag}\n"
                                f"• 종목: *{coin_symbol}/KRW*\n"
                                f"• 현재가: {current_price:,.2f}원\n"
                                f"• 1분간 급등: *+{instant_surge_pct:.2f}%*\n"
                                f"• 1분간 거래대금: 약 *{recent_1m_value_krw / 100_000_000:,.2f}억원*\n"
                                f"• 당일 누적 변동률: {daily_change_rate:+.2f}%\n"
                                f"• 24시간 총 거래대금: {trade_value_24h / 100_000_000:,.1f}억원"
                            )
                            print(f"[{level_tag}] {coin_symbol}: +{instant_surge_pct:.2f}% (1분 거래대금: {recent_1m_value_krw / 100_000_000:.2f}억)")
                            send_telegram_alert(msg)
                            last_alert_time[coin_symbol] = current_time

                    # 현재 수치를 다음 비교값으로 갱신
                    prev_prices[coin_symbol] = current_price
                    prev_volumes[coin_symbol] = total_units_traded

                except Exception:
                    continue

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    threading.Thread(target=run_fake_server, daemon=True).start()
    run_crypto_scanner()
