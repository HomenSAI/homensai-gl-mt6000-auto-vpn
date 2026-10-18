"""Russian/English pairs for table headers and evidence lines that used to be English-only.

Each row is (exact old source text, replacement). Every row must match exactly once so a stale row fails the build.
"""


def bi(en, ru):
    return "bi('" + en.replace("'", "\\'") + "','" + ru.replace("'", "\\'") + "')"


ROWS = [
    # Recovery evidence section: one paragraph style, both languages.
    ("var age=latest==null?'No retained event timestamp':latest>now?'UNKNOWN-FUTURE-TIMESTAMP':Math.floor(now-latest)+' s since latest retained event';",
     "var age=latest==null?" + bi('No retained event timestamp', 'Нет сохранённых отметок времени событий')
     + ":latest>now?'UNKNOWN-FUTURE-TIMESTAMP':Math.floor(now-latest)+' '+" + bi('s since the latest retained event', 'с прошло с последнего сохранённого события') + ";"),
    ("E('small',{},'Calendar boundaries: '+(history.timezone||'Europe/Berlin')+'. Event timestamps: UTC. Durations measure retained APPLYING → controller-confirmed outcome events, not full outage duration. Retry episode IDs describe controller evidence, not certified LAN outages. Categories overlap and must not be summed.'),",
     "E('p',{'class':'hv-ready-intro'},"
     + bi('Calendar boundaries: ', 'Границы дней: ') + "+(history.timezone||'Europe/Berlin')+"
     + bi('. Event times are in UTC. Durations are measured from the retained APPLYING event to the event that confirmed the outcome, not the full outage. Retry episode numbers describe what the controller saw, not certified LAN outages. Categories overlap and must not be added up.',
          '. Время событий указано в UTC. Длительность считается от сохранённого события APPLYING до события, подтвердившего результат, а не как полный простой. Номера повторных эпизодов описывают то, что видел контроллер, а не подтверждённые сбои LAN. Категории пересекаются, их нельзя суммировать.') + "),"),
    ("[E('th',{},'Time · Berlin'),E('th',{},'State'),E('th',{},'Profiles'),E('th',{},'Reason')]",
     "[E('th',{}," + bi('Time · Berlin', 'Время · Берлин') + "),E('th',{}," + bi('State', 'Состояние') + "),E('th',{}," + bi('Profiles', 'Профили') + "),E('th',{}," + bi('Reason', 'Причина') + ")]"),
    ("[E('th',{},'Month'),E('th',{},'Attempts'),E('th',{},'Trials passed'),E('th',{},'Automatic commits'),E('th',{},'Rollbacks'),E('th',{},'Blocked episodes')]",
     "[E('th',{}," + bi('Month', 'Месяц') + "),E('th',{}," + bi('Attempts', 'Попытки') + "),E('th',{}," + bi('Trials passed', 'Тестов пройдено') + "),E('th',{}," + bi('Automatic commits', 'Автопереключений') + "),E('th',{}," + bi('Rollbacks', 'Откатов') + "),E('th',{}," + bi('Blocked episodes', 'Заблокированных эпизодов') + ")]"),
    ("['Time · Berlin','Code','Profiles','Scope'].map(function(text){return E('th',{},text);} )",
     "[" + bi('Time · Berlin', 'Время · Берлин') + "," + bi('Code', 'Код') + "," + bi('Profiles', 'Профили') + "," + bi('Scope', 'Область') + "].map(function(text){return E('th',{},text);} )"),
    ("'Download, Mbps','Upload, Mbps'", bi('Download, Mbps', 'Скачивание, Мбит/с') + "," + bi('Upload, Mbps', 'Отдача, Мбит/с')),
    ("(last.protocol||'unknown')+' / '+(last.channel||'default')", "(last.protocol||" + bi('unknown', 'неизвестно') + ")+' / '+(last.channel||" + bi('default', 'по умолчанию') + ")"),
]


def apply(source):
    for old, new in ROWS:
        assert source.count(old) == 1, old[:80]
        source = source.replace(old, new, 1)
    return source
