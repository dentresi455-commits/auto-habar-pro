import os
import sqlite3
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, Update
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = os.environ["BOT_TOKEN"]
BASE_URL = os.environ["BASE_URL"].rstrip("/")
SECRET = os.environ["WEBHOOK_SECRET"]
DB = os.getenv("DB_PATH", "bot.db")
bot = Bot(TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="UTC")
lock = asyncio.Lock()

def query(sql, params=(), fetch=False):
    with sqlite3.connect(DB) as c:
        c.row_factory = sqlite3.Row
        result = c.execute(sql, params)
        return [dict(x) for x in result.fetchall()] if fetch else result.lastrowid

def init_db():
    query("""CREATE TABLE IF NOT EXISTS chats(
        owner INTEGER NOT NULL, chat_id INTEGER NOT NULL,
        title TEXT, PRIMARY KEY(owner,chat_id))""")
    query("""CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT, owner INTEGER NOT NULL, body TEXT NOT NULL)""")
    query("""CREATE TABLE IF NOT EXISTS settings(
        owner INTEGER PRIMARY KEY, interval_min INTEGER DEFAULT 60,
        active INTEGER DEFAULT 0, last_sent TEXT)""")
    query("""CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT, owner INTEGER,
        chat_id INTEGER, status TEXT, detail TEXT, created_at TEXT)""")

def menu():
    k=ReplyKeyboardBuilder()
    for label in ["📝 Xabar qo‘shish","📋 Xabarlar","➕ Guruh qo‘shish","👥 Guruhlar",
                  "⏱ Interval","▶️ Boshlash","⏹ To‘xtatish","📊 Hisobot"]:
        k.button(text=label)
    k.adjust(2)
    return k.as_markup(resize_keyboard=True)

states = {}
@dp.message(CommandStart())
async def start(m: Message):
    query("INSERT OR IGNORE INTO settings(owner) VALUES(?)",(m.from_user.id,))
    await m.answer("AUTO HABAR PRO — faqat o‘zingiz boshqaradigan yoki ruxsat olingan chatlar uchun.",reply_markup=menu())

@dp.message(F.text == "📝 Xabar qo‘shish")
async def add_msg(m: Message):
    states[m.from_user.id]="message"
    await m.answer("Yuboriladigan matnni kiriting (4096 belgigacha).")

@dp.message(F.text == "➕ Guruh qo‘shish")
async def add_chat(m: Message):
    states[m.from_user.id]="chat"
    await m.answer("Bot admin bo‘lgan guruh/kanal ID sini yuboring (masalan -100...). Siz ham administrator bo‘lishingiz kerak.")

@dp.message(F.text == "⏱ Interval")
async def interval(m: Message):
    states[m.from_user.id]="interval"
    await m.answer("Intervalni daqiqada kiriting (kamida 15).")

@dp.message(F.text == "📋 Xabarlar")
async def list_msgs(m: Message):
    rows=query("SELECT id,body FROM messages WHERE owner=? ORDER BY id DESC LIMIT 20",(m.from_user.id,),True)
    await m.answer("\n".join(f"#{r['id']}: {r['body'][:80]}" for r in rows) or "Xabar yo‘q.")

@dp.message(F.text == "👥 Guruhlar")
async def list_chats(m: Message):
    rows=query("SELECT chat_id,title FROM chats WHERE owner=?",(m.from_user.id,),True)
    await m.answer("\n".join(f"{r['title']}: {r['chat_id']}" for r in rows) or "Guruh yo‘q.")

@dp.message(F.text == "▶️ Boshlash")
async def begin(m: Message):
    uid=m.from_user.id
    if not query("SELECT id FROM messages WHERE owner=?",(uid,),True) or not query("SELECT chat_id FROM chats WHERE owner=?",(uid,),True):
        return await m.answer("Avval xabar va guruh qo‘shing.")
    query("INSERT OR IGNORE INTO settings(owner) VALUES(?)",(uid,))
    query("UPDATE settings SET active=1 WHERE owner=?",(uid,))
    await m.answer("Yuborish yoqildi. Belgilangan interval asosida ishlaydi.")

@dp.message(F.text == "⏹ To‘xtatish")
async def stop(m: Message):
    query("UPDATE settings SET active=0 WHERE owner=?",(m.from_user.id,))
    await m.answer("Yuborish to‘xtatildi.")

@dp.message(F.text == "📊 Hisobot")
async def report(m: Message):
    rows=query("SELECT status,COUNT(*) n FROM logs WHERE owner=? GROUP BY status",(m.from_user.id,),True)
    await m.answer("Hisobot:\n" + ("\n".join(f"{r['status']}: {r['n']}" for r in rows) or "Hali yuborish bo‘lmagan."))

@dp.message(F.text)
async def inputs(m: Message):
    uid=m.from_user.id
    state=states.pop(uid,None)
    if state=="message":
        if len(m.text)>4096: return await m.answer("Matn juda uzun.")
        query("INSERT INTO messages(owner,body) VALUES(?,?)",(uid,m.text))
        return await m.answer("Xabar saqlandi.",reply_markup=menu())
    if state=="interval":
        try: n=int(m.text)
        except ValueError: return await m.answer("Raqam kiriting.")
        if not 15<=n<=10080: return await m.answer("15 dan 10080 gacha daqiqa kiriting.")
        query("INSERT OR IGNORE INTO settings(owner) VALUES(?)",(uid,))
        query("UPDATE settings SET interval_min=? WHERE owner=?",(n,uid))
        return await m.answer(f"Interval: {n} daqiqa.",reply_markup=menu())
    if state=="chat":
        try: chat_id=int(m.text)
        except ValueError: return await m.answer("Chat ID raqam bo‘lishi kerak.")
        try:
            user_member=await bot.get_chat_member(chat_id,uid)
            bot_member=await bot.get_chat_member(chat_id,(await bot.get_me()).id)
            if user_member.status not in ("administrator","creator") or bot_member.status not in ("administrator","creator"):
                return await m.answer("Siz ham, bot ham chatda administrator bo‘lishi kerak.")
            chat=await bot.get_chat(chat_id)
            query("INSERT OR REPLACE INTO chats(owner,chat_id,title) VALUES(?,?,?)",(uid,chat_id,chat.title))
            return await m.answer("Guruh qo‘shildi.",reply_markup=menu())
        except Exception:
            return await m.answer("Chat tekshirilmadi. Botni administrator qilib, ID ni qayta tekshiring.")
    await m.answer("Menyudan tanlang.",reply_markup=menu())

async def send_due():
    async with lock:
        now=datetime.now(timezone.utc)
        for s in query("SELECT * FROM settings WHERE active=1",fetch=True):
            last=datetime.fromisoformat(s["last_sent"]) if s["last_sent"] else None
            if last and (now-last).total_seconds()<s["interval_min"]*60: continue
            msgs=query("SELECT body FROM messages WHERE owner=? ORDER BY id",(s["owner"],),True)
            chats=query("SELECT chat_id FROM chats WHERE owner=?",(s["owner"],),True)
            if not msgs or not chats: continue
            count=query("SELECT COUNT(*) n FROM logs WHERE owner=? AND status='sent'",(s["owner"],),True)[0]["n"]
            body=msgs[count % len(msgs)]["body"]
            for chat in chats:
                try:
                    await bot.send_message(chat["chat_id"],body)
                    status,detail="sent","ok"
                except Exception as exc:
                    status,detail="error",str(exc)[:200]
                query("INSERT INTO logs(owner,chat_id,status,detail,created_at) VALUES(?,?,?,?,?)",
                      (s["owner"],chat["chat_id"],status,detail,now.isoformat()))
                await asyncio.sleep(1)
            query("UPDATE settings SET last_sent=? WHERE owner=?",(now.isoformat(),s["owner"]))

@asynccontextmanager
async def lifespan(app):
    init_db()
    await bot.set_webhook(BASE_URL+"/webhook",secret_token=SECRET)
    scheduler.add_job(send_due,"interval",seconds=60,max_instances=1,coalesce=True)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)
    await bot.session.close()

app=FastAPI(lifespan=lifespan)
@app.get("/")
async def health():
    return {"status":"ok"}
@app.post("/webhook")
async def webhook(request:Request):
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token")!=SECRET:
        raise HTTPException(403)
    update=Update.model_validate(await request.json(),context={"bot":bot})
    await dp.feed_update(bot,update)
    return {"ok":True}
