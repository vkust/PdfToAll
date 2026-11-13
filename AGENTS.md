# AGENTS.md — передача контекста

Файл для любого агента (Hermes в Orca, Claude Code, Codex, человек), который продолжает работу над
PdfToAll. Читай целиком перед первой правкой: здесь то, что уже проверено запуском, и то, что
выглядит рабочим, но не проверено.

## Что это за проект

`pdftoall` — конвертер PDF → DOCX / XLSX / PPTX, работающий локально. CLI + локальный HTTP-сервис
(FastAPI), десктоп-оболочка планируется на Tauri. Лицензия MIT, третьи стороны — см. `docs/licensing.md`.

Репозиторий: https://github.com/vkust/PdfToAll (публичный). Ветка `main`, релизы по тегам `v*`.
Текущая версия `0.1.0`, опубликован релиз с `.deb`, `.rpm`, `.tar.gz`, windows `.zip`.

## Как устроено (и почему именно так)

```
PDF ──▶ движок ──▶ Document (model.py) ──▶ рендереры (render/*) ──▶ .docx/.pptx/.xlsx
        native | docling | marker
```

`model.py` — контракт продукта. Любой движок, возвращающий `Document`, автоматически получает все три
рендерера; любой новый рендерер работает со всеми движками. Не ломай эту границу: если появляется
логика, специфичная для формата, она живёт в `render/`, если для движка — в адаптере в `engines.py`.

- `ingest.py` — native-движок: pdfplumber → символы → строки → блоки. Эвристики намеренно простые и
  объяснимые (порог заголовка 1.18× от базового кегля, склейка строк по вертикальному зазору 0.95×).
  Маркеры списков в ZapfDingbats приходят как буквы `l`/`n`/`u` — их склеивает `_merge_markers`.
- `convert.py` — фасад + путь через LibreOffice (`unoconvert`, не `soffice --convert-to`, см. ниже).
- `api.py` — FastAPI на 127.0.0.1, возвращает файл или zip.

## Что проверено запуском

- native-движок на тестовом PDF: 3 страницы, 2 таблицы, 939 символов, 4 слайда в PPTX, 6 заголовков в DOCX
- 14 тестов (тесты открывают полученные файлы и проверяют стили/таблицы/типы чисел, а не «файл создан»)
- `.deb`: установка → `env -i` запуск → конвертация → `dpkg -r`; `.rpm`: payload распакован, бинарник работает
- Windows zip: состав проверен (exe, `python312.dll`, CRT DLL, шаблоны pptx/docx). **Сам .exe не запускался**
- LibreOffice-мост: зелёный в CI (`ubuntu-latest`, LO 24.2), локально в минимальном контейнере — нет

## Что НЕ проверено (главный техдолг)

1. **Адаптеры `docling` и `marker` в `engines.py` не парсили ни одного PDF.** Написаны по документации.
   Нужна машина с 2–4 ГБ свободной RAM. Проверять так: `pdftoall engines`, затем
   `pdftoall convert samples/quarterly-review.pdf -e docling -f docx` и сравнить с native.
   У docling API: `DocumentConverter().convert(path).document`, элементы через `iterate_items()`,
   таблицы — `item.data.grid`.
2. **Windows `.exe` не запускался.** Проверка на Windows: `pdftoall.exe convert samples\quarterly-review.pdf -o out`
   и открыть полученные файлы Word/PowerPoint.
3. **Подписи нет** (Authenticode, GPG для rpm). Нужны ключи и Windows-машина.
4. **UI нет.** Tauri потребует Rust (~2.5 ГБ) и дисплея для проверки.

## Грабли, на которые уже наступали (не повторяй)

- **`soffice --convert-to docx:writer_pdf_import` не работает.** `--convert-to` ожидает фильтр
  *экспорта*: получишь `Error: no export filter` или импорт как Draw и падение на сохранении.
  Правильно — `unoconvert --input-filter writer_pdf_import|impress_pdf_import` (пакет `unoserver`
  + `python3-uno`). Подробности: `docs/libreoffice.md`.
- **Сломанный PDF-импорт LibreOffice не падает, а пишет валидный .docx на 5 КБ** с текстом
  `"This PDF file is encrypted and can't be opened."` Поэтому есть `validate_libreoffice_output()`.
  Апостроф в XML приходит как `&apos;` — маркер ищется по префиксу `encrypted and can`.
- **PyInstaller: без `--collect-all` для `pptx`/`docx`/`pdfminer` бинарник собирается, но падает
  на первой конвертации** (нет шаблонов презентации и cmap-ов). Смоук-тест после сборки обязателен.
- **nfpm строгий:** неизвестный ключ (`keywords` в корне) валит сборку с `field ... not found`.
- **rpm-payload использует абсолютные пути:** `rpm2cpio | cpio -idm` пишет в `/`. Только с
  `--no-absolute-filenames` и в пустом каталоге.
- **Тег и версия:** релизный workflow падает, если `v0.1.0` ≠ `pdftoall.__version__`. Меняешь версию —
  меняй в `pyproject.toml` и `src/pdftoall/__init__.py` (одно место лучше сделать позже).
- **Не чейнить `git commit` отдельной строкой после проверок:** упавший линт всё равно закоммитит.
  Проверки должны быть одним `&&`-конвейером до коммита.

## Как работать в этом репозитории

```bash
python3.12 -m venv .venv && . .venv/bin/activate    # на Debian/Ubuntu нужен python3.12-venv
pip install -e ".[dev,api]"
python -m pytest -q            # 14 тестов, ~2 с
python -m ruff check src tests # обязано быть чисто, CI это проверяет

# сборка пакетов (нужны pyinstaller, nfpm, binutils)
bash packaging/build-linux.sh 0.1.0
```

Конвенции: тест обязан открыть результат и проверить содержимое; комментарии объясняют «почему», а не
«что»; в README/docs — русский как основной, `README.en.md` — английский дубль.

## Приоритеты

1. Проверить docling/marker на реальном PDF и починить адаптеры (или убрать из README, если не взлетит)
2. Смоук-тест `.exe` на Windows
3. Tauri-оболочка: drag&drop, пакетный режим, предпросмотр (pdf.js, docxjs, SheetJS), локальный API уже есть
4. Подпись сборок, MSI, macOS dmg, arm64
5. Бенчмарк качества: native vs docling vs LibreOffice на корпусе PDF (скан, многоколоночный, таблицы)

## Как передать мне работу обратно

Если правки делались в другой сессии/на другой машине — запушь ветку и напиши в чат: что менял,
что проверял, где остановился. Незакоммиченное состояние другого агента для меня не существует.
