import os, sqlite3, asyncio, secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Request, HTTPException
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, Update
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN=os.environ['BOT_TOKEN']; BASE_URL=os.environ['BASE_URL'].rstrip('/'); SECRET=os.environ['WEBHOOK_SECRET']
DB=os.getenv('DB_PATH','bot.db'); TZ=ZoneInfo('Asia/Tashkent')
bot=Bot(TOKEN); dp=Dispatcher(); scheduler=AsyncIOScheduler(timezone='UTC'); lock=asyncio.Lock()
states={}

def sql(statement, params=(), fetch=False):
    with sqlite3.connect(DB,timeout=20) as db:
        db.row_factory=sqlite3.Row
        result=db.execute(statement,params)
        return [dict(x) for x in result.fetchall()] if fetch else result.lastrowid

def init_db():
    sql('CREATE TABLE IF NOT EXISTS chats(owner INTEGER,chat_id INTEGER,title TEXT,PRIMARY KEY(owner,chat_id))')
    sql('CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,owner INTEGER,body TEXT)')
    sql('CREATE TABLE IF NOT EXISTS settings(owner INTEGER PRIMARY KEY,interval_min INTEGER DEFAULT 60,active INTEGER DEFAULT 0,last_sent TEXT)')
    sql('CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY AUTOINCREMENT,owner INTEGER,chat_id INTEGER,status TEXT,detail TEXT,created_at TEXT,message_id INTEGER)')
    sql('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,referrer INTEGER,joined TEXT,balance INTEGER DEFAULT 0)')
    sql('CREATE TABLE IF NOT EXISTS options(owner INTEGER PRIMARY KEY,work_start INTEGER DEFAULT 0,work_end INTEGER DEFAULT 24,delete_old INTEGER DEFAULT 0)')
    cols={x['name'] for x in sql('PRAGMA table_info(logs)',fetch=True)}
    if 'message_id' not in cols: sql('ALTER TABLE logs ADD COLUMN message_id INTEGER')

def keyboard(items):
    k=ReplyKeyboardBuilder()
    for label in items: k.button(text=label)
    k.adjust(2)
    return k.as_markup(resize_keyboard=True)

MAIN=['➕ Akkaunt qo‘shish','🚀 Avto xabar','👤 Kabinet','🖼️ Akkauntlarim','💎 Pro tarif','🎁 Bonus','👥 Referal','💡 Yordam']
CONTROL=['▶️ Boshlash','⏹ To‘xtatish','📝 Xabar qo‘shish','📋 Xabarlar','➕ Guruh qo‘shish','👥 Guruhlar','⏱ Interval','📊 Hisobot','🕒 Ish vaqti','🗑 Eski xabarni o‘chirish','🔄 Yangilash','⬅️ Asosiy menyu']

def ensure(uid,ref=None):
    sql('INSERT OR IGNORE INTO settings(owner) VALUES(?)',(uid,))
    sql('INSERT OR IGNORE INTO options(owner) VALUES(?)',(uid,))
    sql('INSERT OR IGNORE INTO users(id,referrer,joined) VALUES(?,?,?)',(uid,ref,datetime.now(timezone.utc).isoformat()))

def count(table,uid): return sql(f'SELECT COUNT(*) n FROM {table} WHERE owner=?',(uid,),True)[0]['n']

async def overview(m):
    uid=m.from_user.id; ensure(uid)
    s=sql('SELECT * FROM settings WHERE owner=?',(uid,),True)[0]
    await m.answer(f"🚀 AUTO HABAR PRO\n\nHolat: {'🟢 Faol' if s['active'] else '🔴 To‘xtagan'}\n📝 Xabarlar: {count('messages',uid)}\n👥 Guruhlar: {count('chats',uid)}\n⏱ Interval: {s['interval_min']} daqiqa\n\nFaqat siz va bot administrator bo‘lgan guruh/kanallarga yuboriladi.",reply_markup=keyboard(CONTROL))

@dp.message(CommandStart())
async def start(m:Message):
    ref=None
    parts=(m.text or '').split(maxsplit=1)
    if len(parts)==2 and parts[1].startswith('ref_'):
        try:
            candidate=int(parts[1][4:]); ref=candidate if candidate!=m.from_user.id else None
        except ValueError: pass
    ensure(m.from_user.id,ref)
    await m.answer('AUTO HABAR PRO ga xush kelibsiz!\nRuxsat berilgan chatlar uchun avtomatik xabar yuborish tizimi.',reply_markup=keyboard(MAIN))

@dp.message(F.text=='⬅️ Asosiy menyu')
async def home(m:Message): await m.answer('Asosiy menyu',reply_markup=keyboard(MAIN))
@dp.message(F.text.in_({'🚀 Avto xabar','🔄 Yangilash'}))
async def panel(m:Message): await overview(m)
@dp.message(F.text=='🖼️ Akkauntlarim')
async def accounts(m:Message):
    await m.answer('🖼️ Akkauntlarim\n\nHozir faqat Telegram Bot API orqali ulangan bot ishlaydi. Shaxsiy akkauntlar uchun xavfsiz alohida ulash xizmati hali mavjud emas.\n\nTasdiqlash kodi yoki ikki bosqichli parolingizni bu chatga yubormang.',reply_markup=keyboard(MAIN))

@dp.message(F.text=='➕ Akkaunt qo‘shish')
async def account_add(m:Message):
    await m.answer('🔐 Akkaunt qo‘shish\n\nShaxsiy Telegram akkauntini ulash uchun alohida himoyalangan autentifikatsiya xizmati talab etiladi. Bu bot telefon raqami, Telegram tasdiqlash kodi yoki 2FA parolini qabul qilmaydi.\n\nHozircha ushbu imkoniyat ishga tushirilmagan.',reply_markup=keyboard(MAIN))

@dp.message(F.text=='👤 Kabinet')
async def cabinet(m:Message):
    uid=m.from_user.id; ensure(uid)
    s=sql('SELECT * FROM users WHERE id=?',(uid,),True)[0]
    sent=sql("SELECT COUNT(*) n FROM logs WHERE owner=? AND status='sent'",(uid,),True)[0]['n']
    await m.answer(f"👤 Kabinet\nID: {uid}\n💰 Bonus balansi: {s['balance']} (virtual birlik)\n🖼️ Ulangan bot chatlari: {count('chats',uid)}\n📨 Yuborilgan: {sent}\n💎 Tarif: Bepul MVP\n\nTo‘lovlar hozircha yoqilmagan.",reply_markup=keyboard(MAIN))
@dp.message(F.text=='💎 Pro tarif')
async def pro(m:Message): await m.answer('💎 Pro tarif\nTarif va to‘lov tizimi hali ishga tushirilmagan. Hozirgi bot bepul MVP rejimida.',reply_markup=keyboard(MAIN))
@dp.message(F.text=='🎁 Bonus')
async def bonus(m:Message): await m.answer('🎁 Bonus va promokod tizimi tayyorlanmoqda. Hozircha haqiqiy bonus berilmaydi.',reply_markup=keyboard(MAIN))
@dp.message(F.text=='👥 Referal')
async def referral(m:Message):
    uid=m.from_user.id; ensure(uid)
    me=await bot.get_me(); n=sql('SELECT COUNT(*) n FROM users WHERE referrer=?',(uid,),True)[0]['n']
    await m.answer(f'👥 Referal havolangiz:\nhttps://t.me/{me.username}?start=ref_{uid}\n\nTaklif orqali ro‘yxatdan o‘tganlar: {n}\nHozircha pul mukofoti berilmaydi.',reply_markup=keyboard(MAIN))
@dp.message(F.text=='💡 Yordam')
async def help_msg(m:Message): await m.answer('1. Botni o‘zingiz administrator bo‘lgan guruh/kanalga administrator qiling.\n2. 🚀 Avto xabar → ➕ Guruh qo‘shish orqali chat ID kiriting.\n3. Xabar qo‘shing, interval tanlang va Boshlash tugmasini bosing.\n\nShaxsiy akkaunt sessiyalari yoki tasdiqlash kodlari talab qilinmaydi.',reply_markup=keyboard(MAIN))
@dp.message(F.text=='📝 Xabar qo‘shish')
async def add_message(m:Message):
    states[m.from_user.id]='add_message'; await m.answer('Yangi xabar matnini yuboring (4096 belgigacha).')
@dp.message(F.text=='➕ Guruh qo‘shish')
async def add_chat(m:Message):
    states[m.from_user.id]='add_chat'; await m.answer('Siz va bot administrator bo‘lgan guruh yoki kanalning raqamli chat ID sini yuboring (masalan -100...).')
@dp.message(F.text=='⏱ Interval')
async def interval(m:Message):
    states[m.from_user.id]='interval'; await m.answer('Intervalni daqiqada yuboring: 5, 10, 15, 30, 60 va hokazo (5–10080).')
@dp.message(F.text=='🕒 Ish vaqti')
async def work(m:Message):
    states[m.from_user.id]='hours'; await m.answer('Toshkent vaqti bo‘yicha ish soatlarini HH-HH shaklida kiriting (masalan 09-18). 00-24 = doimiy.')
@dp.message(F.text=='🗑 Eski xabarni o‘chirish')
async def delete_toggle(m:Message):
    uid=m.from_user.id; ensure(uid)
    sql('UPDATE options SET delete_old=1-delete_old WHERE owner=?',(uid,))
    flag=sql('SELECT delete_old FROM options WHERE owner=?',(uid,),True)[0]['delete_old']
    await m.answer('Eski yuborilgan xabarni o‘chirish: '+('YONIQ' if flag else 'O‘CHIQ')+'\nFaqat bot yuborgan va Telegram o‘chirishga ruxsat bergan xabarlarda ishlaydi.')
@dp.message(F.text=='📋 Xabarlar')
async def messages(m:Message):
    uid=m.from_user.id; ensure(uid)
    rows=sql('SELECT id,body FROM messages WHERE owner=? ORDER BY id DESC LIMIT 20',(uid,),True)
    await m.answer(('📝 Xabarlar:\n'+'\n'.join(f"#{r['id']}: {r['body'][:75]}" for r in rows) if rows else 'Xabarlar yo‘q.')+'\n\nO‘chirish: /delmsg ID')
@dp.message(F.text=='👥 Guruhlar')
async def chats(m:Message):
    rows=sql('SELECT chat_id,title FROM chats WHERE owner=?',(m.from_user.id,),True)
    await m.answer(('👥 Guruhlar:\n'+'\n'.join(f"{r['title']} — {r['chat_id']}" for r in rows) if rows else 'Guruhlar yo‘q.')+'\n\nO‘chirish: /delchat CHAT_ID')
@dp.message(F.text=='▶️ Boshlash')
async def begin(m:Message):
    uid=m.from_user.id; ensure(uid)
    if not count('messages',uid) or not count('chats',uid): return await m.answer('Avval kamida bitta xabar va guruh qo‘shing.')
    sql('UPDATE settings SET active=1 WHERE owner=?',(uid,))
    await m.answer('🟢 Avtomatik yuborish yoqildi. Birinchi yuborish rejalashtiruvchi tekshiruvda boshlanadi.')
@dp.message(F.text=='⏹ To‘xtatish')
async def stop(m:Message):
    sql('UPDATE settings SET active=0 WHERE owner=?',(m.from_user.id,)); await m.answer('🔴 Avtomatik yuborish to‘xtatildi.')
@dp.message(F.text=='📊 Hisobot')
async def report(m:Message):
    uid=m.from_user.id
    rows=sql('SELECT status,COUNT(*) n FROM logs WHERE owner=? GROUP BY status',(uid,),True)
    await m.answer('📊 Hisobot\n'+('\n'.join(f"{r['status']}: {r['n']}" for r in rows) if rows else 'Hali yuborishlar yo‘q.'))
@dp.message(F.text.startswith('/delmsg '))
async def delmsg(m:Message):
    try: mid=int(m.text.split()[1])
    except (IndexError,ValueError): return await m.answer('Namuna: /delmsg 1')
    sql('DELETE FROM messages WHERE id=? AND owner=?',(mid,m.from_user.id)); await m.answer('Xabar o‘chirildi (mavjud bo‘lsa).')
@dp.message(F.text.startswith('/delchat '))
async def delchat(m:Message):
    try: cid=int(m.text.split()[1])
    except (IndexError,ValueError): return await m.answer('Namuna: /delchat -100123')
    sql('DELETE FROM chats WHERE chat_id=? AND owner=?',(cid,m.from_user.id)); await m.answer('Guruh ro‘yxatdan chiqarildi (mavjud bo‘lsa).')
@dp.message(F.text)
async def input_handler(m:Message):
    uid=m.from_user.id; state=states.pop(uid,None)
    if state=='add_message':
        if not 1<=len(m.text)<=4096: return await m.answer('Xabar 1–4096 belgidan iborat bo‘lsin.')
        sql('INSERT INTO messages(owner,body) VALUES(?,?)',(uid,m.text)); return await m.answer('✅ Xabar saqlandi.',reply_markup=keyboard(CONTROL))
    if state=='interval':
        try: n=int(m.text)
        except ValueError: return await m.answer('Butun son kiriting.')
        if not 5<=n<=10080: return await m.answer('5–10080 oralig‘ida bo‘lishi kerak.')
        ensure(uid); sql('UPDATE settings SET interval_min=? WHERE owner=?',(n,uid)); return await m.answer(f'⏱ Interval: {n} daqiqa.',reply_markup=keyboard(CONTROL))
    if state=='hours':
        try:
            a,b=map(int,m.text.split('-'))
            if not (0<=a<=23 and 1<=b<=24 and a!=b): raise ValueError()
        except ValueError: return await m.answer('Masalan: 09-18 yoki 00-24')
        ensure(uid); sql('UPDATE options SET work_start=?,work_end=? WHERE owner=?',(a,b,uid)); return await m.answer('🕒 Ish vaqti saqlandi.',reply_markup=keyboard(CONTROL))
    if state=='add_chat':
        try: cid=int(m.text)
        except ValueError: return await m.answer('Raqamli chat ID kiriting.')
        try:
            user=await bot.get_chat_member(cid,uid)
            me=await bot.get_me(); member=await bot.get_chat_member(cid,me.id)
            if user.status not in ('administrator','creator') or member.status not in ('administrator','creator'):
                return await m.answer('Siz ham, bot ham administrator bo‘lishi kerak.')
            chat=await bot.get_chat(cid)
            sql('INSERT OR REPLACE INTO chats(owner,chat_id,title) VALUES(?,?,?)',(uid,cid,chat.title or str(cid)))
            return await m.answer('✅ Guruh qo‘shildi.',reply_markup=keyboard(CONTROL))
        except Exception: return await m.answer('Chatni tekshirib bo‘lmadi. ID va administratorlikni tekshiring.')
    await m.answer('Menyudan bo‘lim tanlang.',reply_markup=keyboard(MAIN))

async def send_due():
    async with lock:
        now=datetime.now(timezone.utc); hour=now.astimezone(TZ).hour
        for s in sql('SELECT * FROM settings WHERE active=1',fetch=True):
            uid=s['owner']; last=datetime.fromisoformat(s['last_sent']) if s['last_sent'] else None
            if last and (now-last).total_seconds()<s['interval_min']*60: continue
            opt=sql('SELECT * FROM options WHERE owner=?',(uid,),True)
            if not opt: continue
            opt=opt[0]; a,b=opt['work_start'],opt['work_end']
            if not ((a<=hour<b) if a<b else (hour>=a or hour<b)): continue
            msgs=sql('SELECT body FROM messages WHERE owner=? ORDER BY id',(uid,),True)
            chats=sql('SELECT chat_id FROM chats WHERE owner=?',(uid,),True)
            if not msgs or not chats: continue
            sent=sql("SELECT COUNT(*) n FROM logs WHERE owner=? AND status='sent'",(uid,),True)[0]['n']
            body=msgs[sent%len(msgs)]['body']
            for c in chats:
                cid=c['chat_id']; status='sent'; detail='ok'; mid=None
                try:
                    if opt['delete_old']:
                        previous=sql("SELECT message_id FROM logs WHERE owner=? AND chat_id=? AND status='sent' AND message_id IS NOT NULL ORDER BY id DESC LIMIT 1",(uid,cid),True)
                        if previous:
                            try: await bot.delete_message(cid,previous[0]['message_id'])
                            except Exception: pass
                    response=await bot.send_message(cid,body); mid=response.message_id
                except Exception as exc: status='error'; detail=str(exc)[:200]
                sql('INSERT INTO logs(owner,chat_id,status,detail,created_at,message_id) VALUES(?,?,?,?,?,?)',(uid,cid,status,detail,now.isoformat(),mid))
                await asyncio.sleep(1)
            sql('UPDATE settings SET last_sent=? WHERE owner=?',(now.isoformat(),uid))

@asynccontextmanager
async def lifespan(app):
    init_db()
    await bot.set_webhook(BASE_URL+'/webhook',secret_token=SECRET)
    scheduler.add_job(send_due,'interval',seconds=60,max_instances=1,coalesce=True)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)
    await bot.session.close()

app=FastAPI(lifespan=lifespan)
@app.get('/')
async def health(): return {'status':'ok','name':'AUTO HABAR PRO'}
@app.post('/webhook')
async def webhook(request:Request):
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token')!=SECRET: raise HTTPException(403)
    update=Update.model_validate(await request.json(),context={'bot':bot})
    await dp.feed_update(bot,update)
    return {'ok':True}
