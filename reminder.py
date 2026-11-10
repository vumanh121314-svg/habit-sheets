import os,requests
from datetime import datetime
from zoneinfo import ZoneInfo
now=datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
msg=("🌙 HABIT SHEETS 3.0 – NHẮC NHỞ TIẾN BỘ 1%\\n"+now.strftime("%d/%m/%Y")+
"\\n1. Việc quan trọng nhất hôm nay đã xong chưa?\\n2. Bạn đã giữ thói quen nào?\\n3. Điều gì cần điều chỉnh?\\n4. Ngày mai chọn hành động nhỏ nào?\\n\\nKhông cần hoàn hảo. Chỉ cần tiến bộ 1%. 🌱")
r=requests.post(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",json={"chat_id":os.environ["TELEGRAM_CHAT_ID"],"text":msg},timeout=20); r.raise_for_status()
