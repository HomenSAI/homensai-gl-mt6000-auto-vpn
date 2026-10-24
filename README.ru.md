# HomenS.AI Auto VPN

[Русский](README.ru.md) · [English](README.md)

Текущая версия: **0.9.1-alpha13**, ветка `feature/owner-ui-20261023`. На выделенном MT3000/4.11.0 установлена alpha13: Auto включён, подтверждён резерв, оба VPN прошли DNS/HTTPS. Проверены87файлов приложения, HTTP/HTTPS и шифрованные копии до/после. Stable **0.9.0** не изменён. Alpha12 ранее осталась с выключенным Auto после guarded-start отказов; alpha11/alpha9 — предыдущие физические базы, alpha10 — отдельный старый VM-аудит. [Матрица alpha13](qa/OWNER-BATCH-ALPHA13-2026-10-24.json).



Приложение для наблюдения за существующей парой OpenVPN/WireGuard и переключения подтверждённого маршрута. Восемь уроков содержат интерактивные схемы с запуском, паузой и пошаговым просмотром.

[Руководство](docs/CURRENT-STATE.ru.md) · [Установка](docs/INSTALL.ru.md) · [Последние изменения RU→EN](docs/LATEST-CHANGES.md) · [Documentation index](docs/DOCUMENTATION-INDEX.md) · [VM audit](docs/handoff/VM-AUDIT-2026-10-24.md)

Experimental software; MIT License. [Terms RU](DISCLAIMER.ru.md) · [Terms EN](DISCLAIMER.md). Switching can interrupt sessions. Prepared MT3000/4.11.0 continuous Auto has separate hardware evidence; MT6000 continuous mode and external LAN/IPv6 acceptance are not established. Private keys, tokens and backups stay outside Git.
