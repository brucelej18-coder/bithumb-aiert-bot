import time
import requests

# ================= 설정 완료 영역 =================
TELEGRAM_BOT_TOKEN = "8698073846:AAGmv-TJQl-5l4u3D476XJ_0yiMcVd2GyTc"
TELEGRAM_CHAT_ID = "8767647660"

CHECK_INTERVAL = 60                # 감지 주기 (60초)
MIN_PRICE_JUMP = 1.8               # 1분 전 대비 최소 상승폭 (%)
MIN_TRADE_VALUE_KRW = 300_000_000 # 최소 24시간 거래대금 (3억원 이상 종목만)
COOLDOWN_SECONDS = 900             # 동일 종목 15분간 중복 알림 방지
# =================================================

def send_telegram_alert(message: str):
    """텔레그램 메시지 전송"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=5)
        return res.json()
    except Exception as e:
        print(f"[알림 전송 실패]: {e}")
        return None

def get_bithumb_all_tickers():
    """빗썸 전체 원화 종목 시세 조회"""
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

    print("🚀 [빗썸 급등 포착 봇 가동] 원화 마켓 실시간 감시를 시작합니다...")
    
    # 봇 정상 연결 확인용 초기 메시지 전송
    send_telegram_alert("🚀 *[빗썸 알림 봇 활성화]*\n가상자산 급등 전조 감시를 시작합니다.")

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

                    # 1. 거래대금 적은 비인기 종목 제외 (호가 왜곡 방지)
                    if trade_value_24h < MIN_TRADE_VALUE_KRW:
                        continue

                    # 2. 직전 주기(1분 전) 대비 급등 여부 확인
                    if coin_symbol in prev_prices:
                        prev_p = prev_prices[coin_symbol]
                        instant_surge_pct = ((current_price - prev_p) / prev_p) * 100

                        is_cooldown = (current_time - last_alert_time.get(coin_symbol, 0)) < COOLDOWN_SECONDS

                        # 급등 기준 충족 시 텔레그램 발송
                        if instant_surge_pct >= MIN_PRICE_JUMP and not is_cooldown:
                            msg = (
                                f"🚨 *[빗썸 급등 포착]*\n"
                                f"• 종목: *{coin_symbol}/KRW*\n"
                                f"• 현재가: {current_price:,.2f}원\n"
                                f"• 단기 상승률: *+{instant_surge_pct:.2f}%*\n"
                                f"• 당일 변동률: {daily_change_rate:+.2f}%\n"
                                f"• 24시간 거래대금: {trade_value_24h / 100_000_000:,.1f}억원"
                            )
                            print(f"[신호 감지] {coin_symbol}: +{instant_surge_pct:.2f}%")
                            send_telegram_alert(msg)
                            last_alert_time[coin_symbol] = current_time

                    # 현재 가격을 다음 턴 비교값으로 갱신
                    prev_prices[coin_symbol] = current_price

                except (KeyError, ValueError, TypeError):
                    continue

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run_crypto_scanner()
