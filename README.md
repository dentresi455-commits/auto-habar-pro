# AUTO HABAR PRO v2

Telegram Bot API asosida ishlaydigan, ruxsatli guruh va kanallarga xabar yuboruvchi bot.

## Menyular
- 🚀 Avto xabar: xabarlar, guruhlar, interval, ish vaqti, boshlash/to‘xtatish, eski xabarni o‘chirish, hisobot
- 👤 Kabinet: virtual balans va statistika
- 🖼️ Akkauntlarim: bot boshqarayotgan chatlar (shaxsiy Telegram sessiyalari emas)
- 👥 Referal: shaxsiy havola va ro‘yxatdan o‘tganlar soni
- 💎 Pro tarif, 🎁 Bonus: hozircha faqat ma'lumot oynasi, to‘lov/bonus ishlamaydi

## Render
`BOT_TOKEN`, `BASE_URL`, `WEBHOOK_SECRET` muhit o‘zgaruvchilari talab qilinadi. `BASE_URL=https://auto-habar-pro.onrender.com`.

## Muhim cheklovlar
- Render Free uxlab qolishi mumkin: doimiy jadval kafolatlanmaydi.
- SQLite Render ephemeral diskda saqlanadi: restart/deployda ma'lumotlar yo‘qolishi mumkin. Production uchun PostgreSQL kerak.
- Bot va foydalanuvchi guruh/kanalda administrator bo‘lishi shart.
- Guruh xabarlarini ommaviy spam sifatida yubormang; faqat ruxsatli chatlardan foydalaning.
- Xabar o‘chirish Telegram cheklovlariga bog‘liq.
- Ushbu versiya real Telegram bilan sinovdan o‘tkazilmagan.
