
import os, sqlite3, hashlib, hmac, secrets, io, json
from pathlib import Path
from datetime import date, datetime, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT=Path(__file__).parent
DB=ROOT/"habit_sheets_3.db"
st.set_page_config(page_title="Habit Sheets 3.0",page_icon="🌱",layout="wide")

# ---------- database + password hashing ----------
def connect():
    c=sqlite3.connect(DB,check_same_thread=False); c.row_factory=sqlite3.Row; return c
def hash_pw(password, salt=None):
    salt=salt or secrets.token_hex(16)
    digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt.encode(),240000).hex()
    return f"{salt}${digest}"
def verify_pw(password,stored):
    try:
        salt,digest=stored.split("$",1)
        return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256",password.encode(),salt.encode(),240000).hex(),digest)
    except Exception: return False
def init():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,password_hash TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS habits(id INTEGER PRIMARY KEY,user_id INTEGER,name TEXT,category TEXT,target INTEGER,points INTEGER,active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS checks(id INTEGER PRIMARY KEY,user_id INTEGER,habit_id INTEGER,day TEXT,UNIQUE(user_id,habit_id,day));
        CREATE TABLE IF NOT EXISTS goals(id INTEGER PRIMARY KEY,user_id INTEGER,title TEXT,category TEXT,target REAL,current REAL,unit TEXT,deadline TEXT,priority INTEGER,active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS notes(user_id INTEGER,day TEXT,wins TEXT,missed TEXT,tomorrow TEXT,mood TEXT,PRIMARY KEY(user_id,day));
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY,user_id INTEGER,day TEXT,title TEXT,category TEXT,done INTEGER DEFAULT 0,priority INTEGER DEFAULT 2);
        CREATE TABLE IF NOT EXISTS focus(id INTEGER PRIMARY KEY,user_id INTEGER,day TEXT,minutes INTEGER,note TEXT);
        """)
init()
def get(sql,p=(),one=False):
    with connect() as c:
        cur=c.execute(sql,p); return cur.fetchone() if one else cur.fetchall()
def put(sql,p=()):
    with connect() as c: c.execute(sql,p); c.commit()

# ---------- style ----------
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');
.stApp{background:linear-gradient(135deg,#faf9f6,#f0f5f4 65%,#fff);color:#242a3b}
.block-container{max-width:1450px;padding-top:1.2rem}
.hero{background:#ffffffed;border:1px solid #eee6dc;border-radius:23px;padding:24px 29px;margin-bottom:18px;box-shadow:0 8px 28px #2830400a}
.kicker{font-size:11px;letter-spacing:3px;color:#ad8b53;font-weight:700}
.hero h1{font-family:'Playfair Display',serif;font-size:clamp(30px,4vw,48px);line-height:1.12;color:#22283a;margin:9px 0}
.hero h1 span{color:#c85e78}.hero p{color:#667085}
div[data-testid="stMetric"]{background:white;border:1px solid #e9edf0;border-radius:15px;padding:12px}
.stProgress>div>div{background:linear-gradient(90deg,#d87991,#78b9bc)}
</style>""",unsafe_allow_html=True)

# ---------- auth ----------
if "uid" not in st.session_state: st.session_state.uid=None
if st.session_state.uid is None:
    st.markdown("<div class='hero'><div class='kicker'>HABIT SHEETS · VERSION 3.0</div><h1>THIẾT KẾ CUỘC ĐỜI<br><span>TIẾN BỘ 1% MỖI NGÀY</span></h1><p>Thói quen · Mục tiêu · Công việc · Tài chính · Phản tư</p></div>",unsafe_allow_html=True)
    a,b=st.tabs(["Đăng nhập","Tạo tài khoản"])
    with a:
        with st.form("login"):
            u=st.text_input("Tên đăng nhập"); p=st.text_input("Mật khẩu",type="password")
            if st.form_submit_button("Đăng nhập",use_container_width=True):
                row=get("SELECT * FROM users WHERE username=?",(u.strip(),),True)
                if row and verify_pw(p,row["password_hash"]):
                    st.session_state.uid=row["id"]; st.session_state.username=row["username"]; st.rerun()
                else: st.error("Tên đăng nhập hoặc mật khẩu chưa đúng.")
    with b:
        with st.form("signup"):
            u=st.text_input("Tên tài khoản mới"); p=st.text_input("Mật khẩu (từ 8 ký tự)",type="password"); p2=st.text_input("Nhập lại mật khẩu",type="password")
            if st.form_submit_button("Tạo tài khoản"):
                if len(u.strip())<3 or len(p)<8: st.error("Tên tài khoản tối thiểu 3 ký tự, mật khẩu tối thiểu 8 ký tự.")
                elif p!=p2: st.error("Mật khẩu nhập lại không khớp.")
                elif get("SELECT id FROM users WHERE username=?",(u.strip(),),True): st.error("Tên tài khoản đã tồn tại.")
                else:
                    put("INSERT INTO users(username,password_hash,created_at) VALUES(?,?,?)",(u.strip(),hash_pw(p),datetime.now().isoformat()))
                    st.success("Tạo tài khoản thành công. Hãy đăng nhập.")
    st.caption("Phiên bản 3.0 không tạo sẵn tài khoản demo. Dữ liệu được lưu riêng theo tài khoản trong cơ sở dữ liệu cục bộ.")
    st.stop()

uid=st.session_state.uid; today=date.today(); ds=today.isoformat()
# ---------- user data ----------
habits=get("SELECT * FROM habits WHERE user_id=? AND active=1 ORDER BY id",(uid,))
goals=get("SELECT * FROM goals WHERE user_id=? AND active=1 ORDER BY priority,id",(uid,))
done={r["habit_id"] for r in get("SELECT habit_id FROM checks WHERE user_id=? AND day=?",(uid,ds))}
week_start=(today-timedelta(days=today.weekday())).isoformat()
week_count=get("SELECT COUNT(*) n FROM checks WHERE user_id=? AND day>=?",(uid,week_start),True)["n"]
xp=get("SELECT COALESCE(SUM(h.points),0) n FROM checks c JOIN habits h ON h.id=c.habit_id WHERE c.user_id=?",(uid,),True)["n"]
streak=0
for i in range(366):
    d=(today-timedelta(days=i)).isoformat()
    if get("SELECT 1 FROM checks WHERE user_id=? AND day=? LIMIT 1",(uid,d),True): streak+=1
    else: break
habit_pct=min(round(week_count/max(1,len(habits)*7)*100),100)
goal_pct=round(sum(min(g["current"]/max(g["target"],1)*100,100) for g in goals)/max(1,len(goals)))
st.markdown(f"<div class='hero'><div class='kicker'>✦ PERSONAL GROWTH OPERATING SYSTEM</div><h1>HÔM NAY TỐT HƠN HÔM QUA<br><span>THÊM 1% MỖI NGÀY</span></h1><p>Xin chào {st.session_state.username} · {today.strftime('%d/%m/%Y')} · Kỷ luật nhỏ tạo nên thay đổi lớn.</p></div>",unsafe_allow_html=True)
with st.sidebar:
    st.title("🌱 HABIT SHEETS 3.0")
    st.metric("Điểm XP",xp); st.metric("Chuỗi ngày",f"{streak} 🔥")
    if st.button("Đăng xuất",use_container_width=True):
        st.session_state.uid=None; st.rerun()
    st.caption("Nhắc nhở mục tiêu lúc 20:30")
    st.info("Nhắc ChatGPT đã được đặt riêng. Telegram có thể bật bằng GitHub Actions.")

tabs=st.tabs(["🏠 Tổng quan","🗓️ Kế hoạch ngày","✅ Thói quen","🎯 Mục tiêu","💰 Tài chính","🧠 Trợ lý 1%","📊 Báo cáo","⚙️ Cài đặt"])
with tabs[0]:
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("Thói quen tuần",f"{habit_pct}%"); c2.metric("Hoàn thành hôm nay",f"{len(done)}/{len(habits)}")
    c3.metric("Mục tiêu",len(goals)); c4.metric("Chuỗi ngày",f"{streak} ngày"); c5.metric("XP tích lũy",xp)
    l,r=st.columns([1.2,1])
    with l:
        st.subheader("Nhịp độ tuần")
        st.progress(habit_pct/100,text=f"Thói quen · {habit_pct}%"); st.progress(goal_pct/100,text=f"Mục tiêu · {goal_pct}%")
        data=[]
        for i in range(6,-1,-1):
            d=today-timedelta(days=i); n=get("SELECT COUNT(*) n FROM checks WHERE user_id=? AND day=?",(uid,d.isoformat()),True)["n"]
            data.append({"Ngày":d.strftime("%d/%m"),"Lượt hoàn thành":n})
        st.plotly_chart(px.bar(pd.DataFrame(data),x="Ngày",y="Lượt hoàn thành"),use_container_width=True)
    with r:
        st.subheader("Mục tiêu ưu tiên")
        for g in goals[:4]:
            pct=min(int(g["current"]/max(g["target"],1)*100),100)
            st.write("**"+g["title"]+"**"); st.progress(pct/100,text=f"{pct}%")
            if g["deadline"] and pct<100:
                days=(date.fromisoformat(g["deadline"])-today).days
                if days<0: st.error(f"Quá hạn {abs(days)} ngày")
                elif days<=7: st.warning(f"Còn {days} ngày")
        st.success("Chọn ít việc hơn, làm đến nơi hơn. Tiến bộ 1% bắt đầu từ hành động tiếp theo.")
with tabs[1]:
    st.subheader("Kế hoạch hành động hôm nay")
    st.caption("Chọn 1–3 việc quan trọng nhất. Hoàn thành từng việc và ghi nhận tiến độ.")
    tasks=get("SELECT * FROM tasks WHERE user_id=? AND day=? ORDER BY priority,id",(uid,ds))
    for t in tasks:
        a,b=st.columns([.08,.92]); val=a.checkbox("",value=bool(t["done"]),key=f"task{t['id']}",label_visibility="collapsed")
        b.write(("~~"+t["title"]+"~~") if val else "**"+t["title"]+"**")
        b.caption(f"{t['category']} · Ưu tiên {['','Cao','Vừa','Thấp'][t['priority']]}")
        if int(val)!=t["done"]: put("UPDATE tasks SET done=? WHERE id=? AND user_id=?",(int(val),t["id"],uid)); st.rerun()
    with st.form("newtask",clear_on_submit=True):
        title=st.text_input("Thêm việc cần làm"); cat=st.selectbox("Nhóm",["Công việc","Gia đình","Sức khỏe","Học tập","Tài chính","Khác"])
        pri=st.select_slider("Ưu tiên",options=[1,2,3],value=1,format_func=lambda x:{1:"Cao",2:"Vừa",3:"Thấp"}[x])
        if st.form_submit_button("Thêm vào kế hoạch") and title.strip():
            put("INSERT INTO tasks(user_id,day,title,category,priority) VALUES(?,?,?,?,?)",(uid,ds,title.strip(),cat,pri)); st.rerun()
    st.markdown("#### Phiên tập trung")
    with st.form("focus"):
        mins=st.number_input("Số phút tập trung",min_value=5,max_value=300,value=25,step=5); note=st.text_input("Bạn đã tập trung làm gì?")
        if st.form_submit_button("Ghi nhận phiên tập trung"):
            put("INSERT INTO focus(user_id,day,minutes,note) VALUES(?,?,?,?)",(uid,ds,int(mins),note)); st.success(f"Đã ghi nhận {mins} phút tập trung.")
    total=get("SELECT COALESCE(SUM(minutes),0) n FROM focus WHERE user_id=? AND day=?",(uid,ds),True)["n"]
    st.metric("Tổng thời gian tập trung hôm nay",f"{total} phút")
with tabs[2]:
    st.subheader("Thói quen và điểm thưởng")
    for h in habits:
        a,b,c=st.columns([.08,.67,.25]); was=h["id"] in done
        val=a.checkbox("",value=was,key=f"habit{h['id']}",label_visibility="collapsed")
        b.write("**"+h["name"]+"**"); b.caption(f"{h['category']} · {h['points']} XP · {h['target']} ngày/tuần")
        c.write("Đã hoàn thành ✅" if val else "Chưa hoàn thành")
        if val!=was:
            if val: put("INSERT OR IGNORE INTO checks(user_id,habit_id,day) VALUES(?,?,?)",(uid,h["id"],ds))
            else: put("DELETE FROM checks WHERE user_id=? AND habit_id=? AND day=?",(uid,h["id"],ds))
            st.rerun()
    with st.expander("＋ Thêm thói quen"):
        with st.form("habitadd"):
            n=st.text_input("Tên"); cat=st.selectbox("Lĩnh vực",["Sức khỏe","Tài chính","Sự nghiệp","Phát triển bản thân","Tinh thần","Gia đình","Khác"])
            target=st.slider("Mục tiêu ngày/tuần",1,7,5); pts=st.slider("XP",5,30,10)
            if st.form_submit_button("Lưu") and n.strip():
                put("INSERT INTO habits(user_id,name,category,target,points) VALUES(?,?,?,?,?)",(uid,n,cat,target,pts)); st.rerun()
with tabs[3]:
    st.subheader("Mục tiêu dài hạn")
    for g in goals:
        pct=min(int(g["current"]/max(g["target"],1)*100),100)
        with st.container(border=True):
            st.write("**"+g["title"]+"**"); st.progress(pct/100,text=f"{g['current']:g}/{g['target']:g} {g['unit']} · {pct}%")
            if g["deadline"]:
                left=(date.fromisoformat(g["deadline"])-today).days
                if left<0 and pct<100: st.error(f"Quá hạn {abs(left)} ngày – nên điều chỉnh kế hoạch.")
                elif left<=7 and pct<100: st.warning(f"Còn {left} ngày.")
            a,b=st.columns([.75,.25]); value=a.number_input("Giá trị hiện tại",0.0,float(g["target"]),float(g["current"]),key=f"goal{g['id']}")
            if b.button("Cập nhật",key=f"goalbtn{g['id']}"): put("UPDATE goals SET current=? WHERE id=? AND user_id=?",(value,g["id"],uid)); st.rerun()
    with st.expander("＋ Tạo mục tiêu"):
        with st.form("goaladd"):
            n=st.text_input("Tên mục tiêu"); cat=st.selectbox("Lĩnh vực",["Sức khỏe","Tài chính","Sự nghiệp","Phát triển bản thân","Gia đình","Khác"])
            target=st.number_input("Giá trị cần đạt",min_value=1.0,value=100.0); unit=st.text_input("Đơn vị","%")
            deadline=st.date_input("Hạn hoàn thành",today+timedelta(days=30)); pri=st.select_slider("Ưu tiên",[1,2,3],value=2)
            if st.form_submit_button("Lưu mục tiêu") and n.strip():
                put("INSERT INTO goals(user_id,title,category,target,current,unit,deadline,priority) VALUES(?,?,?,?,?,?,?,?)",(uid,n,cat,target,0,unit,deadline.isoformat(),pri)); st.rerun()
with tabs[4]:
    st.subheader("Theo dõi tài chính cá nhân")
    st.caption("Bản 3.0 ghi nhận mục tiêu và thói quen tài chính, chưa kết nối ngân hàng.")
    # Financial figures are stored as goals to avoid collecting bank credentials.
    fin=[g for g in goals if g["category"]=="Tài chính"]
    if fin:
        for g in fin:
            pct=min(int(g["current"]/max(g["target"],1)*100),100)
            st.write(f"**{g['title']}** · {g['current']:g}/{g['target']:g} {g['unit']}"); st.progress(pct/100)
    else: st.info("Thêm mục tiêu thuộc lĩnh vực Tài chính ở tab Mục tiêu.")
    st.warning("Không nhập số tài khoản, mật khẩu ngân hàng, mã OTP hoặc thông tin thẻ vào ứng dụng.")
with tabs[5]:
    st.subheader("Trợ lý phát triển bản thân 1%")
    st.write("Trợ lý hiện tạo gợi ý dựa trên dữ liệu đã ghi nhận; chưa gọi mô hình AI bên ngoài.")
    today_tasks=get("SELECT COUNT(*) n FROM tasks WHERE user_id=? AND day=?",(uid,ds),True)["n"]
    task_done=get("SELECT COUNT(*) n FROM tasks WHERE user_id=? AND day=? AND done=1",(uid,ds),True)["n"]
    focus=get("SELECT COALESCE(SUM(minutes),0) n FROM focus WHERE user_id=? AND day=?",(uid,ds),True)["n"]
    st.metric("Việc trong kế hoạch",f"{task_done}/{today_tasks}")
    st.metric("Thời gian tập trung",f"{focus} phút")
    suggestions=[]
    if not habits: suggestions.append("Tạo một thói quen nhỏ, dễ thực hiện.")
    elif len(done)==0: suggestions.append("Đánh dấu một thói quen dễ nhất ngay hôm nay để bắt đầu.")
    elif len(done)<len(habits): suggestions.append("Hoàn thành thêm một thói quen quan trọng, không cần cố làm tất cả.")
    else: suggestions.append("Bạn đã hoàn thành toàn bộ thói quen hôm nay. Hãy nghỉ ngơi và giữ nhịp.")
    if today_tasks and task_done<today_tasks: suggestions.append("Chọn một việc ưu tiên cao còn dang dở và dành 25 phút tập trung.")
    if focus<25: suggestions.append("Thử một phiên tập trung 25 phút, tắt thông báo không cần thiết.")
    if goals: 
        late=[g for g in goals if g["deadline"] and date.fromisoformat(g["deadline"])<today and g["current"]<g["target"]]
        if late: suggestions.append(f"Bạn có {len(late)} mục tiêu quá hạn. Chia nhỏ lại hoặc điều chỉnh thời hạn thực tế.")
    for s in suggestions: st.info("🌱 "+s)
    st.markdown("#### Nhật ký phản tư")
    old=get("SELECT * FROM notes WHERE user_id=? AND day=?",(uid,ds),True)
    with st.form("dailyreflection"):
        mood=st.select_slider("Tâm trạng",["Rất tốt","Tốt","Ổn","Chưa tốt","Cần nghỉ ngơi"],value=old["mood"] if old else "Ổn")
        wins=st.text_area("Hôm nay mình làm tốt điều gì?",value=old["wins"] if old else "")
        missed=st.text_area("Điều gì cần cải thiện?",value=old["missed"] if old else "")
        tomorrow=st.text_area("Một hành động 1% cho ngày mai",value=old["tomorrow"] if old else "")
        if st.form_submit_button("Lưu phản tư"):
            put("INSERT INTO notes(user_id,day,wins,missed,tomorrow,mood) VALUES(?,?,?,?,?,?) ON CONFLICT(user_id,day) DO UPDATE SET wins=excluded.wins,missed=excluded.missed,tomorrow=excluded.tomorrow,mood=excluded.mood",(uid,ds,wins,missed,tomorrow,mood)); st.success("Đã lưu. Ngày mai tiếp tục.")
with tabs[6]:
    st.subheader("Báo cáo 30 ngày")
    start=(today-timedelta(days=29)).isoformat()
    rows=get("SELECT day,COUNT(*) n FROM checks WHERE user_id=? AND day>=? GROUP BY day ORDER BY day",(uid,start))
    if rows:
        df=pd.DataFrame([dict(x) for x in rows]); df["day"]=pd.to_datetime(df["day"])
        st.plotly_chart(px.line(df,x="day",y="n",markers=True,title="Lượt thói quen hoàn thành"),use_container_width=True)
    else: st.info("Chưa có dữ liệu.")
    focusrows=get("SELECT day,SUM(minutes) minutes FROM focus WHERE user_id=? AND day>=? GROUP BY day ORDER BY day",(uid,start))
    if focusrows:
        st.plotly_chart(px.bar(pd.DataFrame([dict(x) for x in focusrows]),x="day",y="minutes",title="Phút tập trung"),use_container_width=True)
with tabs[7]:
    st.subheader("Cài đặt & dữ liệu")
    st.markdown("**Đổi mật khẩu**")
    with st.form("passwordchange"):
        oldp=st.text_input("Mật khẩu hiện tại",type="password"); newp=st.text_input("Mật khẩu mới (từ 8 ký tự)",type="password")
        if st.form_submit_button("Đổi mật khẩu"):
            row=get("SELECT * FROM users WHERE id=?",(uid,),True)
            if not verify_pw(oldp,row["password_hash"]): st.error("Mật khẩu hiện tại không đúng.")
            elif len(newp)<8: st.error("Mật khẩu mới cần ít nhất 8 ký tự.")
            else: put("UPDATE users SET password_hash=? WHERE id=?",(hash_pw(newp),uid)); st.success("Đã đổi mật khẩu.")
    if st.button("Chuẩn bị sao lưu dữ liệu"):
        buf=io.BytesIO()
        with connect() as c:
            import zipfile
            with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
                for table in ["habits","checks","goals","notes","tasks","focus"]:
                    df=pd.read_sql_query(f"SELECT * FROM {table} WHERE user_id=?",(c,),params=(uid,))
                    z.writestr(table+".csv",df.to_csv(index=False).encode("utf-8-sig"))
        st.download_button("Tải bản sao lưu ZIP",buf.getvalue(),file_name="habit_sheets_3_backup.zip")
    st.info("Bản 3.0 đã băm mật khẩu bằng PBKDF2-HMAC-SHA256. Tuy vậy, ứng dụng vẫn dùng SQLite cục bộ. Để dùng online nhiều thiết bị, cần chuyển sang Supabase Auth + PostgreSQL + Row Level Security.")
st.caption("HABIT SHEETS 3.0 · MỖI NGÀY TIẾN BỘ 1%")
