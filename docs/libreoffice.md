# Мост в LibreOffice: как это работает и где ломается

Путь `--libreoffice` — **экспериментальный**. Он даёт максимально похожую на PDF вёрстку ценой
редактируемости (текст приезжает текстовыми рамками, а не абзацами), и он не входит в проверенное ядро.

## Механика: фильтр импорта, а не экспорта

`soffice --convert-to docx:writer_pdf_import` **не работает**: `--convert-to` ожидает фильтр
*экспорта*, поэтому LibreOffice пытается сохранить результат в формате, которого нет
(`Error: no export filter`), либо импортирует PDF как документ Draw и падает на сохранении в DOCX
(`impl_store ... Class:Parameter`).

Правильный способ — форсировать фильтр *импорта*:

```bash
unoconvert --input-filter writer_pdf_import  --convert-to docx  in.pdf out.docx   # Writer
unoconvert --input-filter impress_pdf_import --convert-to pptx  in.pdf out.pptx   # Impress
```

`unoconvert` входит в пакет [unoserver](https://github.com/unoconv/unoserver) и общается с уже
запущенным `unoserver` по UNO-сокету (по умолчанию 127.0.0.1:2003). `pdftoall` поднимает сервер сам,
если порт закрыт, и гасит его после конвертации.

Установка:

```bash
sudo apt install libreoffice-writer-nogui libreoffice-impress-nogui libreoffice-draw-nogui python3-uno
python3 -m pip install unoserver        # ставится в системный python, где есть модуль uno
```

## Ловушка, на которую мы наступили

Если в сборке LibreOffice не работает PDF-импорт (нет `libreoffice-draw`, битая сборка, минимальный
контейнер), конвертация **не падает с ошибкой**, а молча создаёт документ с текстом
*"This PDF file is encrypted and can't be opened."* Внешне это валидный `.docx`/`.pptx` размером 5–7 КБ.

Поэтому `validate_libreoffice_output()` читает результат и отвергает такой файл с внятной диагностикой.
Никогда не убирайте эту проверку: без неё пользователь получает пустой документ вместо ошибки.

## Что поддерживается

| Цель | Фильтр импорта | Комментарий |
|---|---|---|
| docx / odt / rtf | `writer_pdf_import` | страница разбирается как Writer-документ из рамок |
| pptx / odp | `impress_pdf_import` | страница = слайд, объекты остаются объектами |
| xlsx | — | LibreOffice так не умеет (Draw → Calc невозможен); для таблиц используйте native-движок |

## Как проверить на своей машине

```bash
pdftoall convert report.pdf --libreoffice -f docx,pptx
```

Если приходит `EngineError: LibreOffice PDF import is not working here` — импорт в этой сборке
не работает; ставьте `libreoffice-draw` или используйте native-движок. Эта проверка не входит в
обязательный CI-прогон, потому что корректность PDF-импорта зависит от дистрибутива и версии
LibreOffice, а не от нашего кода.
