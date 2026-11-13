# PdfToAll

[![ci](https://github.com/vkust/PdfToAll/actions/workflows/ci.yml/badge.svg)](https://github.com/vkust/PdfToAll/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

PDF → **DOCX · XLSX · PPTX** прямо **на твоей машине**. Без загрузки на сервер, без аккаунтов, без лимитов на размер файла.

*English version: [README.en.md](README.en.md)*

Проект появился потому, что рынок «PDF → Office» либо закрытый (Adobe, ABBYY, Wondershare), либо облачный
(Smallpdf, iLovePDF, ConvertAPI) — а облако означает, что договоры, медицинские карты и финансовые отчёты
покидают ноутбук. Даже самый сильный open-source PDF-проект, Stirling-PDF, — серверный продукт: документ
всё равно куда-то едет.

**Статус:** v0.1.0 — native-конвейер работает end-to-end и покрыт тестами. Нейродвижки (docling, marker)
и десктоп-оболочка подключены архитектурно, но ещё не поставлены.

```bash
# текстовый PDF, без моделей, ~50 мс на страницу
pip install -e .[dev]
pdftoall convert report.pdf -o out/            # -> report.docx, report.pptx, report.xlsx
pdftoall info report.pdf                       # скан? сколько таблиц? какой движок?
pdftoall engines                               # что установлено
```

## Установка из релизов

Готовые сборки лежат в [Releases](https://github.com/vkust/PdfToAll/releases) — бинарник самодостаточный,
Python ставить не нужно.

```bash
# Debian / Ubuntu
sudo dpkg -i pdftoall_0.1.0_amd64.deb

# Fedora / RHEL / openSUSE
sudo rpm -i pdftoall-0.1.0-1.x86_64.rpm

# любой Linux без пакетного менеджера
tar -xzf pdftoall-0.1.0-linux-x86_64.tar.gz && ./pdftoall/pdftoall --version
```

Windows: распаковать `pdftoall-0.1.0-windows-x64.zip` и запустить `pdftoall.exe` — установка не требуется.
Сборки пока не подписаны: SmartScreen покажет предупреждение («Подробнее» → «Выполнить в любом случае»),
а `rpm` ругнётся на отсутствие GPG-подписи. Контрольные суммы — в `SHA256SUMS.txt` рядом с файлами.

Размер: `.deb`/`.rpm`/`.tar.gz` ~41 МБ (в распакованном виде ~91 МБ), zip для Windows — см. релиз.
Внутри — только native-движок (pdfplumber); docling/marker ставятся отдельно и в пакет не входят.

## Что реально получается на выходе

| Формат | Результат |
|---|---|
| DOCX | Настоящие стили Word (`Heading 1..4`, `List Bullet`), редактируемые абзацы, нативные таблицы |
| PPTX | Один слайд на страницу PDF, **геометрия сохранена** (блоки держат относительные позиции), нативные редактируемые таблицы |
| XLSX | Отдельный лист на каждую найденную таблицу, оформленная шапка, числа остаются числами, плюс лист-индекс |

Чего пока нет: извлечение картинок и графики, векторные объекты, подбор шрифтов, попиксельно точная вёрстка.
Если нужен результат «выглядит ровно как PDF» — есть экспериментальный мост в LibreOffice (`--libreoffice`):
он меняет редактируемость на точность и зависит от сборки LibreOffice, см. `docs/libreoffice.md`.

## Архитектура

```
PDF ──▶ Движок ────▶ Модель документа ────▶ Рендереры ────▶ .docx / .pptx / .xlsx
        (native |    (Page, Block,         (python-docx,
         docling |    Table; только MIT)    python-pptx,
         marker)                            openpyxl)
```

Модель документа — контракт продукта: любой движок, который умеет отдавать `Document`, автоматически
получает все три рендерера, а любой новый рендерер работает со всеми движками. Движок выбирается под
конкретный файл: чистый «цифровой» PDF проходит native-путём за миллисекунды, скан договора — через OCR
docling/marker.

```
src/pdftoall/
  model.py        Document/Page/Block/Table — промежуточное представление
  ingest.py       native-движок: pdfplumber -> модель (строки, блоки, заголовки, списки, таблицы)
  engines.py      реестр движков + адаптеры docling/marker + определение LibreOffice
  convert.py      фасад «одна функция» + резервный путь через LibreOffice
  render/         docx.py, pptx.py, xlsx.py
  api.py          локальный сервис FastAPI (127.0.0.1) — мост для Tauri/Electron-интерфейса
  cli.py          команда `pdftoall`
```

## Движки

| Движок | Установка | Лицензия | Когда использовать |
|---|---|---|---|
| native | входит в пакет | MIT | цифровые PDF, простая вёрстка, важна скорость |
| docling | `.[docling]` | MIT | многоколоночный текст, сложные таблицы, нужен OCR — лучший баланс лицензии и качества |
| marker | `.[marker]` | Apache-2.0 код / OpenRAIL-M веса | плохие сканы, максимальная точность; работает на CPU |
| LibreOffice | apt + unoserver | MPL-2.0 | **экспериментально** (проверяется отдельным job'ом в CI): сохранение вёрстки, `--libreoffice` — см. `docs/libreoffice.md` |

Сознательно **не** используется: PyMuPDF (AGPL-3.0) — см. `docs/licensing.md`, прежде чем его добавлять.

## API для десктоп-оболочки

```bash
uvicorn pdftoall.api:app --port 8765
curl -F file=@report.pdf -F formats=docx,pptx http://127.0.0.1:8765/convert -o out.zip
```

## Место на диске

Замерено на тестовой машине этого репозитория (разбивка — в `docs/footprint.md`):

- код и тесты: **< 5 МБ**
- `pip install -e .[dev]`: **172 МБ** (venv, включая FastAPI)
- мост LibreOffice: **186 МБ скачать / ~765 МБ установить**
- + docling: **~2 ГБ** (torch 539 МБ + модели 530 МБ)
- + marker: **~3–4 ГБ**
- десктоп-оболочка (Tauri + Rust-тулчейн): **~2.5 ГБ**, только для сборки

Для релизной сборки: **~1.5 ГБ** инсталлятор с мостом LibreOffice, **~2.5–3 ГБ** со встроенным docling,
**~150 МБ** в варианте только с native-движком.

## План

- [x] native-движок + три рендерера + CLI + локальный API + тесты
- [ ] извлечение и размещение изображений
- [ ] docling по умолчанию для сложных макетов (авто-роутинг по `detect()`)
- [ ] бенчмарк качества против LibreOffice/Stirling на публичном корпусе PDF
- [ ] десктоп-оболочка на Tauri (drag & drop, предпросмотр «до/после» через pdf.js/docxjs/SheetJS, пакетный режим)
- [ ] OCR для сканов без GPU
- [ ] подписанные инсталляторы для Windows/macOS/Linux

## Лицензия

MIT. Матрица лицензий сторонних компонентов — `docs/licensing.md`.

Продолжаешь работу над проектом (человек или агент)? Начни с `AGENTS.md`: состояние, проверенное и
непроверенное, найденные грабли.
