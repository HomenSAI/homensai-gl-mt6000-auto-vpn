# Alpha39: stopped channel is started; stock leftovers tolerated

The dedicated MT3000 runs 0.9.1-alpha39-1 (source 56fb842, package SHA256 27f4822e...). Exact dual-runtime CI passed and two isolated builds equal the CI hash. Auto is ON / RUNNING and, because the primary WG channel lost 71% of 60 test packets, it automatically switched to the working reserve (COMMITTED, client confirmed). Both channels are enabled; the reserve carries traffic and the primary is watched for return.

Earlier installs on the same day exposed two real firmware side effects and are preserved as failed evidence: alpha37 held the pair when the stock client added firewall bookkeeping options, alpha38 held it when the firmware removed stopped leftover client sections. The held session was archived with the owner's approval; old interface flags were not restored. A forced return to the primary order was performed on the owner's choice before installing alpha39. [Receipt](../qa/MT3000-ALPHA39-2026-10-27.json).

Limits: no external LAN confirmation, 24-hour soak, power-cut or IPv6 test; return to a recovered primary was not observed. Not published to GitHub or Gitea.

# Альфа39: остановленный канал запускается

На выделенном MT3000 работает 0.9.1-alpha39-1. Auto включён и сам переключился на рабочий резерв, потому что основной WG терял 71% пакетов. Прежние установки alpha37/38 выявили два побочных эффекта прошивки; сессия архивирована с согласия владельца, возврат на основной выполнен по выбору владельца. Публикация не выполнялась.
