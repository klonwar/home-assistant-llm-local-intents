# Design: универсальные LLM-инструменты для локальных Assist-интентов

Статус: дизайн подтверждён пользователем; runtime-реализация выполнена,
конфигурационные изменения HA переданы отдельному агенту.

## Понимание задачи

- Довести существующий скелет `llm_local_intents` до полной реализации для
  всего inventory локальных Assist-интентов.
- Предоставлять отдельный LLM tool для каждого опубликованного intent, чтобы
  LLM предпочитала точный локальный handler широкому native tool.
- Поддерживать пользовательские `intent_script` и встроенные Assist-интенты,
  проверяя фактический runtime handler.
- Оставить конфигурационный репозиторий Home Assistant неизменённым; после
  реализации подготовить отдельный handoff для агента, который внесёт туда
  metadata и выполнит реальные HA-проверки.
- Поддерживать Home Assistant Core `2026.8.0+`, любой HA LLM provider и один
  экземпляр примерно до 100 локальных интентов.
- В первом релизе публиковать generic policy на русском и английском; не
  встраивать в исходный код имена комнат, сущностей, hardware или intent из
  конкретной установки.

## Предположения

- Домен интеграции и top-level YAML key сохраняются как `llm_local_intents`.
- Metadata приходит через объединённый Home Assistant mapping; интеграция не
  читает YAML-файлы напрямую.
- Стабильные имена tools имеют префикс `local_assist_`.
- Прямой вызов intent API инкапсулирован в HA adapter; точная сигнатура
  проверяется против Core `2026.8.0` во время реализации.
- Поля `description` и `examples` задаются конкретной установкой и входят в
  tool descriptions; generic policy не содержит project-specific примеров.
- Для языка берётся `llm_context.language`; `ru` и `en` имеют свои policy,
  остальные языки используют английский fallback.
- Владельцы репозитория поддерживают schema и документацию; новые поля должны
  добавляться обратно совместимо. File watcher не нужен.

## Не входит в scope

- Изменение hardware-сущностей или переименование `switch` в `light`.
- Изменение `yandex_station_intents` и существующих scripts.
- Удаление или отключение native Home Assistant tools.
- File watcher, UI/config flow и повторный вызов Conversation API из tool.
- Изменения в отдельном Home Assistant configuration repository.

## Принятые решения

1. Выбран подход с отдельным динамическим tool на каждый intent. Один общий
   dispatcher и Conversation API wrapper отклонены из-за худшей точности,
   контроля и риска рекурсии.
2. Каталог строится из merged YAML mapping при setup/reload и хранится как
   immutable snapshot в `hass.data[DOMAIN]`.
3. Ошибка одной записи пропускается; неудачная полная сборка не заменяет
   предыдущий рабочий snapshot; успешная сборка публикуется атомарно.
4. Tool хранит точное имя Assist-интента и не принимает имя handler от модели.
5. Fixed intent получает пустую schema; parameterized intent — schema slots с
   типами и ограничениями.
6. Выполнение идёт через прямой intent API. После ошибки local handler native
   fallback запрещён.
7. Native tools остаются доступными. Priority используется для сортировки и
   диагностики, но не даёт формальной гарантии выбора моделью.
8. Policy fragment универсален: только общие правила выбора local tool,
   fallback и retry; тексты на `ru`/`en` выбираются по языку запроса.
9. Реальные package metadata, configuration reload и Gemma acceptance будут
   выполнены следующим агентом по отдельному handoff-документу.

## Архитектура

`async_setup` принимает уже объединённый `llm_local_intents` mapping и
передаёт его в чистые parser/validator. Descriptor содержит имя Assist-интента,
имя tool, description, examples, priority, category и slot schema. HA adapter
проверяет наличие handler и изолирует внутреннюю сигнатуру intent API.

В `hass.data[llm_local_intents]` хранятся catalog, исходный config, generation
и unsubscribe callback. `async_get_tools` только читает snapshot, сортирует
descriptors и создаёт динамические экземпляры tools. При config-update свежий
merged config запрашивается через штатный HA reload helper. Mutable global
registry и сетевые вызовы не используются.

## Контракт tool

```text
LLM -> local_assist_<intent>
    -> schema validation
    -> direct intent adapter
    -> registered Assist handler
    -> JSON-serializable result
```

Успех возвращает объект с `success`, точным `intent` и коротким `speech`.
Невалидные args, отсутствующий handler, недоступный service и исключение
handler преобразуются в `HomeAssistantError`. Tool не вызывает native tool и
не запускает Conversation API рекурсивно.

## Metadata и валидация

Минимальная запись имеет вид:

```yaml
llm_local_intents:
  intents:
    ExampleIntent:
      description: "Короткое описание действия"
      examples:
        - "естественная фраза"
      slots: {}
```

`description` и непустой `examples` обязательны; defaults — `expose: true`,
`priority: 50`, `slots: {}`. Slot DSL ограничен документированными типами и
проверяемыми `minimum`/`maximum`/`enum`. Некорректная запись skipped с
техническим warning. Дубли диагностируются там, где provenance доступен; в
handoff для HA требуется глобальная уникальность имён.

## Policy и выбор инструмента

Generic policy на русском и английском требует сначала проверять local tools,
выбирать наиболее специфичный, не подменять его area/domain native вызовом и
не повторять действие другим tool после ошибки. При равной неоднозначности
модель должна задать один короткий вопрос. Конкретные phrases и examples
поступают только из metadata данной установки.

## Надёжность и диагностика

Логируются только технические поля: counts каталога, generation, имена tools,
tool-call id, outcome и класс исключения. Пользовательские фразы, secrets,
tokens и полные args не пишутся в info-логи. При отсутствии рабочей версии
интеграция может загрузиться с пустым каталогом и warning.

## Проверки и handoff

Нужно покрыть parser, slot schemas, dynamic tools, direct handler adapter,
generic `ru`/`en` policy, error/no-fallback и atomic reload тестами. Обязательны:

```bash
python -m compileall -q custom_components/llm_local_intents
python -m pytest tests
```

Создан `docs/home-assistant-config-handoff.md` с точным YAML key
`llm_local_intents`, таблицей inventory, metadata для package-файлов, правилами
validation/reload и acceptance-матрицей реального HA/Gemma.
