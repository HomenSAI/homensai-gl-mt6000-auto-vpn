<!-- current-release-context:0.9.0 -->
> Component/lab reference, not current product-readiness evidence. [Current release and scope](../docs/CURRENT-STATUS.md).

# Стенд отказов HomenSAI Auto VPN

Это отдельный референсный симулятор будущего протокола применения маршрутов. Он не является драйвером GL.iNet и не подключён к локальному dashboard.

- router_sim.js — транзакция, модель flash, обе семьи IP, блокировка forwarding, workers, conntrack и перезапуск.
- test_router_faults.js — 200 комбинаций в десяти категориях; путь JSON-отчёта первым аргументом.
- test_transaction_regressions.js — семь точечных проверок протокола восстановления.
- test_process_crash.py — 20 реальных SIGKILL собственного child-процесса в Docker, файловые записи/fsync/replace и модельное восстановление.

Команды и границы результатов: [отчёт](../qa/ROUTER_FAULT_REPORT.md). Не запускать никакие команды на роутере на основании одного факта успешного прохождения этих тестов.
