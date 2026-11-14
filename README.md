# AUTO HABAR PRO

Theguyso/telegram-auto-sender loyihasidagi **xabarlarni navbatlash, interval va log** g'oyalaridan foydalanilgan, Bot API asosida qayta yozilgan MVP. Original Telethon akkaunt sessiyalari ishlatilmaydi.

## Render
1. GitHub'da yangi repository yarating va ushbu fayllarni yuklang.
2. Render > New > Blueprint > repository tanlang.
3. `BOT_TOKEN` — BotFather'dan **yangilangan** token.
4. `BASE_URL` — Render bergan `https://...onrender.com` manzil.
5. `WEBHOOK_SECRET` Render tomonidan generatsiya qilinadi.
6. Deploy qiling, so'ng Telegram'da /start bosing.

## Cheklovlar
- Render free service uxlab qoladi; shu sababli rejalashtirilgan xabarlar kafolatli 24/7 ishlamaydi.
- SQLite fayli Render'da doimiy disk bo'lmasa deploy/restartda yo'qolishi mumkin.
- Ishlab chiqarish uchun persistent PostgreSQL va doimiy worker kerak.
- Xabarlar faqat foydalanuvchi hamda bot administrator bo'lgan chatlarga yuboriladi.
- Hozircha matnli xabarlar, guruh qo'shish, interval, start/stop va oddiy hisobot ishlangan; media, to'lov, referal keyingi bosqich.
- Dastur Render'da real sinovdan o'tkazilmagan.
