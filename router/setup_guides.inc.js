/* Expandable "what is this and how to fill it in" guides for the Settings cards and the Tests page.
   Data are [English, Russian] pairs; each field has what it is, an example and the allowed range. */
var SETUP_GUIDES={
  system:{
    what:['Tells the program which two of your router VPN profiles are the main one and the reserve, and how they are named.','Говорит программе, какие два из ваших VPN-профилей роутера основной и резервный, и как они называются.'],
    why:['Auto and the reports need to know which VPN is preferred and which one takes over when the preferred one fails.','Auto и отчёты должны знать, какой VPN предпочтителен и какой подхватывает работу, когда он отказывает.'],
    fields:[
      [['Primary profile','Основной профиль'],['The VPN you normally want to use. Pick it from the list; the list comes from GL.iNet → VPN.','VPN, которым вы обычно хотите пользоваться. Выберите из списка; список берётся из GL.iNet → VPN.'],['Germany · WireGuard','Германия · WireGuard']],
      [['Reserve profile','Резервный профиль'],['The VPN used when the primary does not work. Choose a different country or provider, so one outage does not stop both.','VPN на случай, когда основной не работает. Выберите другую страну или другого провайдера, чтобы один сбой не остановил оба.'],['Netherlands · OpenVPN','Нидерланды · OpenVPN']],
      [['Name','Название'],['Your own short name shown in the tables and in reports. Optional.','Ваше короткое название в таблицах и отчётах. Необязательно.'],['Main (home)','Основной (дом)']],
      [['Priority','Приоритет'],['1 is the most preferred. The reserve gets a larger number.','1 — самый предпочтительный. У резерва число больше.'],['Primary 1, reserve 2','Основной 1, резерв 2']],
      [['Allow a brief drop of calls and downloads when switching','Разрешить короткий обрыв звонков и загрузок при переключении'],['Switching to another VPN breaks open connections for a few seconds (calls, downloads). Tick it only if you accept that.','При переходе на другой VPN открытые соединения рвутся на несколько секунд (звонки, загрузки). Отметьте, только если вас это устраивает.'],['Tick it','Отметить']]
    ]},
  recovery:{
    what:['The rules for when the router switches to the reserve and when it goes back.','Правила: когда роутер переходит на резерв и когда возвращается обратно.'],
    why:['Too sensitive rules switch on every short glitch; too lazy rules leave you without internet for long. Presets are tested starting points.','Слишком чувствительные правила переключаются при каждом сбое; слишком ленивые надолго оставляют без интернета. Пресеты — проверенные точки старта.'],
    fields:[
      [['Preset “Stability”','Пресет «Стабильность»'],['Recommended. Switches only after 5 failed checks in a row, waits 5 minutes between switches, returns after 5 good checks and 2 minutes of calm.','Рекомендуется. Переключается только после 5 неудачных проверок подряд, ждёт 5 минут между переключениями, возвращается после 5 удачных проверок и 2 минут спокойствия.'],['failures 5 · pause 300 s','сбоев 5 · пауза 300 с']],
      [['Preset “Fast recovery”','Пресет «Быстрое восстановление»'],['Switches after 3 failures, pause 1 minute, returns after 3 good checks. Reacts quickly, but may switch more often.','Переключается после 3 сбоев, пауза 1 минута, возврат после 3 удачных проверок. Реагирует быстро, но может переключаться чаще.'],['failures 3 · pause 60 s','сбоев 3 · пауза 60 с']],
      [['Preset “Hold reserve”','Пресет «Держать резерв»'],['After a switch stays on the reserve until you press “Return to primary”. Fewer surprises, but you return by hand.','После переключения остаётся на резерве, пока вы не нажмёте «Вернуться на основной». Меньше неожиданностей, но возвращаться нужно вручную.'],['pause 180 s · stay on reserve','пауза 180 с · остаться на резерве']],
      [['Failures before switching','Сбоев до переключения'],['How many failed checks in a row count as a real outage. Range 3–10.','Сколько неудачных проверок подряд считать настоящим сбоем. Диапазон 3–10.'],['5','5']],
      [['Good checks on the reserve','Удачных проверок резерва'],['How many good checks the reserve needs before the switch. Range 2–10.','Сколько удачных проверок нужно резерву перед переключением. Диапазон 2–10.'],['3','3']],
      [['Attempt limit and window','Лимит попыток и период'],['Maximum forward attempts in a rolling window of 1–15 minutes. The pause between attempts still applies; changing the values does not erase the recorded history.','Максимум попыток перехода за скользящий период 1–15 минут. Отдельная пауза между попытками сохраняется; изменение значений не стирает историю.'],['3 attempts · 15 min','3 попытки · 15 минут']],
      [['Cooldown, seconds','Пауза, секунд'],['Minimum time between two switches. Range 60–1800.','Минимальное время между двумя переключениями. Диапазон 60–1800.'],['300','300']],
      [['Minimum stay, seconds','Минимальное пребывание, секунд'],['How long to stay on the new VPN before another switch is allowed. Range 60–3600.','Сколько оставаться на новом VPN, прежде чем разрешить следующее переключение. Диапазон 60–3600.'],['300','300']],
      [['Return rule and checks','Правило возврата и проверки'],['Return when the primary is healthy (needs 2–10 good checks and 30–600 s of calm), or hold the reserve.','Возвращаться, когда основной исправен (нужно 2–10 удачных проверок и 30–600 с спокойствия), или держать резерв.'],['5 checks · 120 s','5 проверок · 120 с']]
    ]},
  monitoring:{
    what:['How often the program checks your VPNs and how much it keeps.','Как часто программа проверяет ваши VPN и сколько хранит.'],
    why:['Checks are what the statistics and Auto rely on. More frequent checks react faster but use a little more traffic and router time.','На проверках основаны статистика и Auto. Частые проверки реагируют быстрее, но чуть больше нагружают трафик и роутер.'],
    fields:[
      [['Check interval, seconds','Интервал проверок, секунд'],['Pause between checks of each connected VPN. Range 10–300.','Пауза между проверками каждого подключённого VPN. Диапазон 10–300.'],['10 (default)','10 (по умолчанию)']],
      [['Statistics saving, seconds','Сохранение статистики, секунд'],['How often the collected data is written to the router’s storage. Range 300–3600. Rarer saves wear flash less.','Как часто собранные данные пишутся в память роутера. Диапазон 300–3600. Реже — меньше износ флеш-памяти.'],['900','900']],
      [['Profile limit','Лимит профилей'],['How many connected VPNs are checked at one time. Range 1–16.','Сколько подключённых VPN проверяется одновременно. Диапазон 1–16.'],['4','4']]
    ]},
  telegram:{
    what:['Sends reports and alerts about your VPNs to a Telegram chat.','Отправляет отчёты и уведомления о ваших VPN в чат Telegram.'],
    why:['You learn about a switch or an outage without opening the router page. Optional.','Вы узнаёте о переключении или сбое, не открывая страницу роутера. Необязательно.'],
    fields:[
      [['Bot token','Токен бота'],['A secret from @BotFather (https://t.me/BotFather): send /newbot, choose a name, copy the line it gives you. It never leaves the router and is never shown again.','Секрет от @BotFather (https://t.me/BotFather): отправьте /newbot, выберите имя, скопируйте выданную строку. Он остаётся на роутере и больше не показывается.'],['123456789:AAH… (digits, colon, 30–100 characters)','123456789:AAH… (цифры, двоеточие, 30–100 символов)']],
      [['Chat ID','ID чата'],['Where to send. For yourself: write to @userinfobot (https://t.me/userinfobot) and copy “Id”. For a group the number starts with −. A public channel can be @channelname.','Куда слать. Для себя: напишите @userinfobot (https://t.me/userinfobot) и скопируйте «Id». Для группы число начинается с −. Публичный канал можно указать как @имя_канала.'],['123456789 · -1001234567890 · @my_channel','123456789 · -1001234567890 · @my_channel']],
      [['Report every, minutes','Отчёт каждые, минут'],['How often a report is sent. Range 5–10080 (one week).','Как часто слать отчёт. Диапазон 5–10080 (неделя).'],['1440 (once a day)','1440 (раз в сутки)']],
      [['Daily hour','Час суток'],['The hour of the day for daily reports, 0–23 router time.','Час суток для ежедневных отчётов, 0–23 по времени роутера.'],['9','9']]
    ],
    tail:['Then press “Test Telegram delivery”. If nothing arrives, open Help → “Telegram reports do not arrive”.','Затем нажмите «Проверить доставку Telegram». Если ничего не пришло, откройте «Помощь» → «Отчёты в Telegram не приходят».']},
  speed:{
    what:['A speed test downloads and uploads a small amount of data through one VPN and shows how fast it is.','Тест скорости скачивает и отдаёт небольшой объём данных через один VPN и показывает его скорость.'],
    why:['It helps to compare servers. It is not needed for failover, uses your traffic, and is off by default. Run it when you choose a server, not all the time.','Помогает сравнить серверы. Для переключения не нужен, расходует трафик и по умолчанию выключен. Запускайте при выборе сервера, а не постоянно.'],
    fields:[
      [['Enable speed tests','Включить тесты скорости'],['Master switch. Nothing is measured while it is off.','Главный выключатель. Пока он выключен, ничего не измеряется.'],['Off (default)','Выключено (по умолчанию)']],
      [['Test after a new server connects','Тестировать после подключения нового сервера'],['Measures a server once when it first appears connected.','Один раз измеряет сервер, когда он впервые оказался подключён.'],['On, if you often add servers','Включить, если часто добавляете серверы']],
      [['Payload budget per server, MiB','Лимит на сервер, МиБ'],['The most data one test of one server may use.','Максимум данных на один тест одного сервера.'],['8','8']],
      [['Seconds per direction · Parallel streams','Секунд на направление · Потоки'],['How long to measure download and upload, and how many connections to use.','Сколько измерять скачивание и отдачу и сколько соединений использовать.'],['5 s · 2 streams','5 с · 2 потока']],
      [['Daily quota, MiB','Суточная квота, МиБ'],['The total data all tests together may use in a day.','Сколько данных могут использовать все тесты вместе за сутки.'],['128','128']],
      [['Skip above current VPN traffic, Mbps','Не запускать при трафике выше, Мбит/с'],['No test starts while you are actively using the VPN above this speed.','Тест не стартует, пока вы активно пользуетесь VPN быстрее этого значения.'],['2','2']]
    ]}
};
function setupGuide(key){
  var g=SETUP_GUIDES[key];if(!g)return null;
  var fields=g.fields.map(function(f){return E('li',{},[E('strong',{},bi(f[0][0],f[0][1])),E('span',{},' — '+bi(f[1][0],f[1][1])),E('em',{'class':'hv-guide-example'},' '+bi('Example: ','Пример: ')+bi(f[2][0],f[2][1]))]);});
  return E('details',{'class':'hv-setup-guide'},[E('summary',{},bi('What is this and how to fill it in','Что это и как заполнить')),
    E('p',{},[E('strong',{},bi('What it is. ','Что это. ')),bi(g.what[0],g.what[1])]),
    E('p',{},[E('strong',{},bi('What it is for. ','Для чего. ')),bi(g.why[0],g.why[1])]),
    E('ul',{'class':'hv-guide-fields'},fields),
    g.tail?E('p',{},bi(g.tail[0],g.tail[1])):null].filter(Boolean));
}
