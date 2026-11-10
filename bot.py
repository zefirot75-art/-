<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Умный администратор для салона — презентация</title>
<style>
  * {margin:0; padding:0; box-sizing:border-box;}
  body {font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif; background:#1c1226; color:#2b2135;}
  .slide {display:none; min-height:100vh; padding:6vh 8vw; background:linear-gradient(135deg,#fff7f2 0%,#ffe9ef 100%);}
  .slide.active {display:flex; flex-direction:column; justify-content:center;}
  h1 {font-size:3.2rem; line-height:1.15; margin-bottom:24px; color:#3a2b45;}
  h2 {font-size:2.4rem; margin-bottom:28px; color:#3a2b45;}
  p.sub {font-size:1.5rem; color:#7a6885; margin-bottom:18px;}
  ul {font-size:1.45rem; line-height:1.7; list-style:none;}
  ul li {margin-bottom:14px;}
  .accent {color:#d63d6e; font-weight:700;}
  .card {background:#fff; border-radius:20px; padding:28px 32px; box-shadow:0 10px 30px rgba(90,40,80,.12); margin-top:18px;}
  .shots {display:flex; gap:28px; margin-top:26px; flex-wrap:wrap;}
  .shot {flex:1 1 300px; background:#fff; border-radius:16px; padding:14px; box-shadow:0 10px 30px rgba(90,40,80,.12); text-align:center;}
  .shot img {max-width:100%; border-radius:10px;}
  .shot .cap {font-size:1.05rem; color:#7a6885; margin-top:10px;}
  .shot.noimg {min-height:260px; display:flex; align-items:center; justify-content:center; color:#b9a8c4; font-size:1.1rem; border:2px dashed #e3cdd9;}
  .shot.noimg::after {content:"Место для вашего скриншота (положите файл рядом с презентацией)";}
  .price {font-size:2.6rem; font-weight:800; color:#d63d6e;}
  .nav {position:fixed; bottom:18px; right:22px; display:flex; gap:10px; z-index:10;}
  .nav button {font-size:1.2rem; padding:8px 18px; border:none; border-radius:12px; background:#3a2b45; color:#fff; cursor:pointer;}
  .counter {position:fixed; bottom:22px; left:24px; color:#9b8aa6; font-size:1rem; z-index:10;}
  @media print {
    body {background:#fff;}
    .nav,.counter {display:none;}
    .slide {display:block !important; min-height:96vh; page-break-after:always;}
  }
</style>
</head>
<body>

<section class="slide">
  <p class="sub">Telegram-бот с AI-мозгом для сферы красоты</p>
  <h1>Умный администратор<br>для вашего салона</h1>
  <p class="sub">Ловит клиентов и отвечает на их вопросы 24/7 — пока вы работаете или спите</p>
  <div class="card">Игорь · +7 (___) ___-__-__ · @ваш_telegram</div>
</section>

<section class="slide">
  <h2>Где теряются клиенты 💸</h2>
  <ul>
    <li>🌙 Клиент пишет в 23:47 — администратор спит. Утром клиент записан в другом месте</li>
    <li>💇 Пик на приёме: сообщения ждут ответа часами, клиент уходит к конкуренту</li>
    <li>📉 Каждое неотвеченное сообщение — несостоявшийся визит на 2 500–7 900₽</li>
  </ul>
  <div class="card">Вопрос: сколько таких сообщений было у вашего салона на этой неделе?</div>
</section>

<section class="slide">
  <h2>Решение: AI-администратор 🤖</h2>
  <ul>
    <li>💬 Мгновенно отвечает на вопросы клиентов: цены, мастера, парковка, Wi-Fi</li>
    <li>📥 Ловит заявку: услуга, желаемое время, телефон — даже ночью</li>
    <li>🔥 Присылает её владельцу кнопками в одно касание: подтверждена / выполнена / отмена</li>
    <li>🗂 Все заявки хранятся в базе и доступны командой /leads</li>
  </ul>
</section>

<section class="slide">
  <h2>Как это выглядит в жизни 📱</h2>
  <div class="shots">
    <div class="shot"><img src="shot_dialog.png" onerror="this.parentElement.classList.add('noimg');this.remove();" alt=""><div class="cap">Клиент пишет своими словами — бот понимает и ловит заявку</div></div>
    <div class="shot"><img src="shot_lead.png" onerror="this.parentElement.classList.add('noimg');this.remove();" alt=""><div class="cap">Заявка владельцу со статус-кнопками</div></div>
  </div>
</section>

<section class="slide">
  <h2>Бот не обманывает ваших клиентов 🤝</h2>
  <ul>
    <li>🚫 Не выдумывает скидки и акции</li>
    <li>🕐 Не обещает несуществующие свободные окна</li>
    <li>⚠️ Если услуги нет в прайсе — честно скажет и предложит альтернативы</li>
    <li>📞 Не знает ответа — передаст администратору и сохранит контакт клиента</li>
  </ul>
  <div class="card">Репутация салона под защитой: бот никогда не обещает больше, чем салон может выполнить.</div>
</section>

<section class="slide">
  <h2>Не заменяет — усиливает 🧩</h2>
  <ul>
    <li>✅ Не заменяет DIKIDI и CRM — работает рядом с ними</li>
    <li>📅 Дальше: интеграция с DIKIDI — реальные слоты и мгновенная запись</li>
    <li>♻️ Лист ожидания: отменённый слот сам предлагается тем, кто хотел это время</li>
    <li>📊 Аналитика отмен и неявок: где салон теряет деньги</li>
  </ul>
</section>

<section class="slide">
  <h2>Попробуйте на своём салоне бесплатно 🎁</h2>
  <ul>
    <li>🚀 10 дней полного функционала: настроим бота, заполним карточку салона, дадим QR-код и картинку для клиентов</li>
    <li>🛠 Всё включено: хостинг, обновления, поддержка</li>
    <li>📄 Без годовых договоров и платы за внедрение</li>
  </ul>
  <div class="card">Далее — <span class="price">1 500₽/мес</span><br>дешевле, чем один упущенный визит клиента</div>
</section>

<section class="slide">
  <h2>Посмотрите вживую прямо сейчас ✨</h2>
  <p class="sub">Возьмите мой телефон и напишите боту любой вопрос, как клиент: цену, запись, каверзный вопрос.</p>
  <div class="card">Бот: @ваш_bot_username<br>Игорь · +7 (___) ___-__-__ · @ваш_telegram</div>
</section>

<div class="counter" id="counter"></div>
<div class="nav">
  <button onclick="go(-1)">←</button>
  <button onclick="go(1)">→</button>
</div>

<script>
let i = 0;
const slides = document.querySelectorAll('.slide');
function show() {
  slides.forEach((s, k) => s.classList.toggle('active', k === i));
  document.getElementById('counter').textContent = (i + 1) + ' / ' + slides.length;
}
function go(d) { i = Math.min(slides.length - 1, Math.max(0, i + d)); show(); }
document.addEventListener('keydown', e => {
  if (e.key === 'ArrowRight' || e.key === ' ') go(1);
  if (e.key === 'ArrowLeft') go(-1);
});
show();
</script>
</body>
</html>
