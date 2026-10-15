"""Generate the bilingual UI from its Russian source; fail on untranslated literals."""
import json
from pathlib import Path
import re

PAIRS = '''Туннель не подключён|Tunnel disconnected
HTTPS через VPN не проходит|HTTPS through VPN failed
DNS не отвечает|DNS unavailable
Маршрут не соответствует VPN|Route does not match VPN
Путь проверки не подтверждён|Probe path unverified
Ошибка службы или зависимости|Service or dependency error
Ошибка сохранения статистики|Statistics storage error
Статистика восстановлена из резервной копии|Statistics restored from backup
Время роутера ещё не установлено|Router clock is not set
Профиль сейчас не подключён|Profile currently inactive
Профиль вне лимита текущего раунда|Profile outside this round's limit
Служба остановлена|Service unavailable
График появится после двух успешных измерений. Искусственных данных здесь нет.|The chart appears after two successful measurements. No synthetic data is used.
История HTTPS-задержки подключённых серверов в миллисекундах|HTTPS latency history of connected servers in milliseconds
HTTPS, мс · последние доступные измерения за час. Разрывы длиннее 90 секунд не соединяются.|HTTPS, ms · available samples from the last hour. Gaps longer than 90 seconds are not connected.
Нативный монитор alpha: реальные IPv4 HTTPS/DNS-проверки на роутере. Автоматическое изменение маршрутов пока недоступно.|Native alpha monitor: real IPv4 HTTPS/DNS probes on the router. Automatic route switching is unavailable.
Служба наблюдения|Monitoring service
Включить наблюдение|Enable monitoring
Интервал, секунд|Probe interval, seconds
Лимит подключённых профилей за раунд|Connected profile limit per round
Сохранение статистики во flash, секунд|Flash checkpoint interval, seconds
Отправлять отчёты в Telegram|Send Telegram reports
Интервал Telegram-отчётов, минут|Telegram report interval, minutes
Токен бота · настройка Telegram|Bot token · Telegram setup
Проверьте формат токена BotFather|Check the BotFather token format
Оставьте пустым, чтобы сохранить действующий токен.|Leave empty to keep the current token.
Токен сохранится на роутере; в отчёты и статус не включается.|The token stays on the router and is excluded from reports and status.
Каналы и существующие профили|Channels and existing profiles
Ваше название|Display name
Профиль роутера|Router profile
Ваш канал|Channel name
Приоритет|Priority
Наблюдать|Monitor
Режим: наблюдение. Ни профили VPN, ни firewall не изменяются. Проверки процесса роутера ещё не подтверждают путь LAN-клиента. IPv6 здесь не проверяется.|Monitor mode. VPN profiles and firewall remain unchanged. Router probes do not verify a LAN client's path. IPv6 is not tested.
включён · интервал |enabled · interval\s
 мин · последняя отправка | min · last sent\s
ожидается|pending
отключён|disabled
Подключённые серверы|Connected servers
Остальные профили не запускаются|Other profiles are not started
Проверки сейчас|Current probes
 из | of\s
HTTPS и DNS с роутера · IPv4|Router HTTPS and DNS · IPv4
Трафик месяца|Monthly traffic
Нет данных|No data
Неполный период · с начала наблюдения|Partial period · since monitoring started
Ошибка|Error
Каждые |Every\s
 мин| min
Отключён|Disabled
Отправлен |Sent\s
Нет подтверждённой отправки|No confirmed delivery
Подключённые VPN-серверы|Connected VPN servers
 мс · HTTPS| ms · HTTPS
Измерено |Measured\s
нет данных|no data
Подключённые серверы не обнаружены.|No connected servers detected.
Задержка серверов во времени|Server latency over time
Сервер|Server
Канал|Channel
Протокол|Protocol
Интерфейс|Interface
Результат|Result
HTTPS, мс|HTTPS, ms
Время проверки|Probe time
Текущие проверки серверов|Current server probes
Неактивные профили перечислены без запуска: тестирование такого сервера требует отдельного согласованного окна подключения.|Inactive profiles are listed without being started. Testing one requires a separate approved connection window.
Рейтинг измеренных профилей|Measured profile ranking
Успех проверок|Probe success
Средняя HTTPS-задержка|Average HTTPS latency
 мс| ms
Это рейтинг по часовым агрегатам до семи дней наблюдения, не тест пропускной способности. Приоритеты не применяются автоматически.|Ranking uses hourly aggregates from up to seven days of monitoring. This is not a bandwidth test; priorities are not applied automatically.
VPN-трафик по календарным месяцам · Europe/Berlin|VPN traffic by calendar month · Europe/Berlin
Месяц|Month
Входящий|Received
Исходящий|Sent
Всего|Total
Наблюдение|Observation
 интерфейс-часов| interface-hours
 · граница оценена| · estimated month boundary
Уникальные VPN-интерфейсы считаются один раз. Это объёмы интерфейсов, включая служебный трафик. Пропуски наблюдения: |Unique VPN interfaces are counted once, including protocol overhead. Observation gaps:\s
. После потери питания возможна потеря последнего интервала checkpoint.|. A power loss may lose the latest checkpoint interval.
Монитор служб|Service monitor
Скачать журнал|Export events
Серверы, качество связи и трафик — реальные измерения на роутере|Servers, connection quality and traffic — real router measurements
Запрошен раунд проверок подключённых профилей.|A probe round for connected profiles was requested.
Проверить сейчас|Probe now
Настроить Telegram|Set up Telegram
Мастер подключения Telegram|Telegram setup wizard
Настройки мониторинга, Telegram и названия серверов|Monitoring settings, Telegram and server names
Подключение Telegram|Connect Telegram
Создайте бота через @BotFather и скопируйте токен.|Create a bot with @BotFather and copy its token.
Отправьте боту /start. Введите свой Chat ID и токен ниже.|Send /start to your bot. Enter your own chat ID and bot token below.
Включите отправку, выберите интервал и нажмите Save & Apply. Роутер отправит первый отчёт; результат появится в статусе Telegram сверху.|Enable reports, select an interval and click Save & Apply. The router sends its first report; delivery status appears above.
Токен — секрет. После сохранения он не показывается; повторная настройка открывается отдельной кнопкой.|The token is secret. It is not displayed after saving. Use the separate setup button to replace it.'''

root = Path(__file__).parent/'files/www/luci-static/resources/view/homensai-vpn'
source = (root/'dashboard9.js').read_text(encoding='utf-8')
pairs = dict((k,v.replace('\\s',' ')) for k,v in (line.split('|',1) for line in PAIRS.splitlines()))
pattern = r"'([^'\n]*[\u0400-\u04ff][^'\n]*)'"
missing = sorted(set(re.findall(pattern, source))-pairs.keys())
if missing:
    raise SystemExit('Untranslated strings: '+repr(missing))
source = re.sub(pattern, lambda m:'tr('+json.dumps(m[1],ensure_ascii=False)+')', source)
locale = """
var locale = localStorage.getItem('homensai-vpn-language') || 'en';
var translations = DICTIONARY;
function tr(value){return locale==='ru'?value:(translations[value]||value);}
function bi(en,ru){return locale==='ru'?ru:en;}
""".replace('DICTIONARY',json.dumps(pairs,ensure_ascii=False))
source = source.replace("'require ui';", "'require ui';\n"+locale)
source = source.replace('v0.1.0-alpha9','v0.2.0-alpha1')
source = source.replace("E('span',{'class':'hv-version'},'v0.2.0-alpha1'),", "E('span',{'class':'hv-version'},'v0.2.0-alpha1'),E('select',{'aria-label':'Language','change':function(ev){localStorage.setItem('homensai-vpn-language',ev.target.value);window.location.reload();}},[E('option',{value:'en',selected:locale==='en'},'English'),E('option',{value:'ru',selected:locale==='ru'},'Русский')]),")
source = source.replace("var panel=E('div',{'class':'hv-panel'}),self=this;", "var panel=E('div',{'class':'hv-panel'}),self=this,period='day';")
source = source.replace("      var table=E('table'", "      panel.appendChild(histogram(status.accounting||{},function(value){period=value;draw(status);},period));\n      var table=E('table'",1)
source = source.replace("),panel,E('a',{'class':'btn'", "),E('p',{'class':'hv-developer'},[bi('Developer: ','Разработчик: '),E('a',{href:'https://homensai.com',target:'_blank',rel:'noopener noreferrer'},'Serhii Khomenko · HomenS.AI')]),panel,E('a',{'class':'btn'",1)
source=source.replace('return view.extend({', (Path(__file__).parent/'ui_histogram.js').read_text(encoding='utf-8')+'return view.extend({',1)
(root/'dashboard10.js').write_text(source,encoding='utf-8')
