# Handoff: LLM tools for local Home Assistant Assist intents

## 1. Цель

Нужно добавить к Home Assistant LLM-провайдеру инструменты для локальных
Assist-интентов, которые уже работают через `custom_sentences` и
`intent_script`.

Цель — чтобы LLM выбирала локальный интент, когда пользователь говорит о
действии, для которого такой интент существует. Это особенно важно для
света: физические световые реле имеют `domain: switch` и находятся в тех же
областях, что и розетки. Универсальный вызов `HassTurnOn/Off` по области и
домену поэтому выполняет слишком широкое действие.

Пример ошибки из production:

```text
Пользователь: ты можешь выключить свет в коридоре

LLM tool call:
  tool_name: HassTurnOff
  tool_args:
    area: Коридор
    domain:
      - switch

HA result:
  switch.bh_light
  switch.hw_light
  switch.kt_light
```

Ожидаемое поведение — вызов локального `HallwayLightOff`, который выполняет
существующий сценарий и выключает только `switch.hw_light`.

## 2. Репозитории и границы работы

### Репозиторий конфигурации Home Assistant

Путь:

```text
C:\Users\klonw\PhpstormProjects\home-assistant
```

Здесь находятся:

- `prompt.txt` — полный системный prompt LLM;
- `custom_sentences/ru/*.yaml` — Assist sentence grammar;
- `src/packages/...` — package-конфигурация Home Assistant;
- `intent_script` — фактические обработчики локальных интентов;
- `custom_components/` — установленный/dist-каталог интеграций. По правилам
  этого репозитория его не следует редактировать напрямую.

В этом репозитории должны появиться только package-метаданные рядом с
существующими `intent_script` и, при необходимости, общие правила в
`prompt.txt`. Исходник LLM-интеграции здесь не хранится.

### Репозиторий исходника интеграции

Путь:

```text
C:\Users\klonw\WebstormProjects\home-assistant-llm-local-intents
```

Текущая база этого репозитория фактически является исходником интеграции
`llm_reminders`:

```text
custom_components/llm_reminders/
  __init__.py
  config_flow.py
  const.py
  helpers.py
  llm.py
  llm_diagnostics.py
  llm_tools.py
  manager.py
  prompt_loader.py
  prompts/
tests/
```

В базе уже есть рабочий пример Home Assistant LLM platform:

- `llm.py` реализует `async_get_tools(hass, llm_context, api_id)`;
- `llm_tools.py` показывает классы `llm.Tool`, `vol.Schema`,
  `ToolInput`, `LLMContext` и `HomeAssistantError`;
- `prompt_loader.py` загружает общий prompt и языковые дополнения;
- тесты запускаются через `python -m pytest tests`;
- README требует Home Assistant Core 2026.8.0+ и проверку
  `python -m compileall -q custom_components/llm_reminders`.

Рекомендуется создать отдельный integration domain
`local_assist_llm` в `custom_components/local_assist_llm/`, переиспользовав
паттерны текущего `llm_reminders`. Не нужно смешивать reminder manager и
исполнение локальных интентов в одном классе.

Консервативное предположение: существующие reminder tools не удалять, пока
новые local-intent tools не заработают. Если итоговый репозиторий должен
заменять reminders полностью, это отдельная миграционная задача: смена
domain, manifest, README, HACS и release-please.

## 3. Что входит в scope

В scope входят только локальные Assist-интенты, определённые через
`custom_sentences` и `intent_script`.

В scope не входят:

- `yandex_station_intents` и связанные с ними automations/scripts;
- изменение hardware-сущностей или переименование `switch` в `light`;
- удаление стандартных `HassTurnOn`, `HassTurnOff` и других native HA tools;
- автоматический file watcher для YAML;
- изменение существующего поведения локальных scripts.

Стандартные `HassTurnOn/Off` остаются доступными. Это означает, что гарантия
приоритета локального инструмента вероятностная, а не формально enforced:
модель всё ещё может ошибиться. Приоритет повышается отдельными tools,
описаниями, примерами и prompt-фрагментом.

## 4. Принятые решения

1. Если существует подходящий локальный Assist-интент, LLM должна предпочесть
   его универсальному native tool.
2. Правило применяется ко всем локальным Assist-интентам, а не только к
   свету.
3. Если локального интента нет, native HA tool разрешён как fallback только
   для однозначного действия.
4. Если локальный интент найден, но выполнение завершилось ошибкой, нельзя
   повторять действие через `HassTurnOn/Off`; нужно сообщить об ошибке.
5. Дополнительное подтверждение перед локальным интентом не требуется.
6. Размер prompt и небольшая дополнительная задержка допустимы; точность
   важнее компактности.
7. Метаданные должны находиться в том же package-файле, где объявлен
   соответствующий `intent_script`.
8. Центральный manifest в Home Assistant-конфигурации не используется.
9. После полного применения конфигурации каталог пересобирается; на лету
   отслеживать изменения файлов не нужно.

## 5. Как package-файл будет задавать metadata

Нельзя добавлять произвольный ключ внутрь записи `intent_script`: schema
`intent_script` может отклонить неизвестное поле. Поэтому используется
соседний top-level блок custom integration в том же package-файле.

Пример для `src/packages/light/rooms/hallway_light.yaml`:

```yaml
intent_script:
  HallwayLightOff:
    action:
      - action: script.automation_diagnostic_log
        data:
          source: hw_light_off
          event: started
      - service: script.hw_light_off
      - service: script.local_assistant_silent_message
        response_variable: result
      - stop: done
        response_variable: result
    speech:
      text: "{{ action_response.message }}"

local_assist_llm:
  intents:
    HallwayLightOff:
      description: "Выключить только основной свет в коридоре"
      examples:
        - "выключи свет в коридоре"
        - "погаси свет в коридоре"
      priority: 100
      slots: {}
```

Другой intent в том же файле может быть описан рядом:

```yaml
local_assist_llm:
  intents:
    HallwayLightOn:
      description: "Включить только основной свет в коридоре"
      examples:
        - "включи свет в коридоре"
        - "зажги свет в коридоре"
      priority: 100
      slots: {}
```

HA должен объединить повторяющиеся `local_assist_llm` sections из packages в
одну mapping. Это обязательно проверить на целевой версии HA через
configuration check/reload; не полагаться только на unit tests интеграции.

### Поля записи

Для `expose: true` обязательны:

- `description` — одно короткое русское описание действия;
- `examples` — минимум одна естественная фраза, желательно 2–4;
- `slots` — `{}` для fixed-argument intent либо явная схема аргументов.

Необязательные поля:

- `expose` — default `true`; `false` скрывает служебный intent;
- `priority` — default `50`, большее значение означает более высокий
  приоритет при конфликте;
- `category` — например `light`, `vacuum`, `media`, `query`;
- ограничения slot: `type`, `minimum`, `maximum`, `enum`, внутренние значения;
- `notes` — только диагностика, не отправляется модели.

Автоматически выводятся из mapping:

- точное имя Assist-интента;
- имя LLM-инструмента с префиксом `local_assist_`;
- наличие metadata и handler;
- конфликты имён.

Пример параметрического intent:

```yaml
local_assist_llm:
  intents:
    HassSetVolume:
      description: "Установить громкость"
      examples:
        - "сделай громкость на половину"
        - "поставь громкость на максимум"
      category: media
      slots:
        volume_level:
          type: integer
          minimum: 0
          maximum: 100
```

Если опубликованный intent не содержит обязательных полей, он не должен
становиться инструментом; интеграция должна вывести понятную ошибку и
продолжить работу с остальными entries.

## 6. Инвентарь текущих локальных Assist-интентов

Это стартовый inventory из Home Assistant configuration repo. Он нужен для
проверок и для добавления соседних metadata blocks. Не включать в него
`yandex_station_intents`.

### `custom_sentences/ru/package_lights_sockets.yaml`

- `LargeRoomLightOn`, `LargeRoomLightOff`
- `BedroomLightOn`, `BedroomLightOff`
- `BathroomLightOn`, `BathroomLightOff`
- `GuestRoomLightOn`, `GuestRoomLightOff`
- `GuestRoomLampOn`, `GuestRoomLampOff`
- `GuestRoomBraOn`, `GuestRoomBraOff`
- `HallwayLightOn`, `HallwayLightOff`
- `HallwayBedBulbOn`, `HallwayBedBulbOff`
- `KitchenLightOn`, `KitchenLightOff`
- `AllLightsOn`, `AllLightsOff`
- `KitchenStripOn`, `KitchenStripOff`
- `DimaDeskLampOn`, `DimaDeskLampOff`
- `DimaRaspberryPiOn`, `DimaRaspberryPiOff`
- `DimaCarpetOn`, `DimaCarpetOff`
- `AnnaMonitorOn`, `AnnaMonitorOff`
- `AnnaDeskLampOn`, `AnnaDeskLampOff`
- `AnnaChargerOn`, `AnnaChargerOff`

### `custom_sentences/ru/package_features.yaml`

- `CancelAssistant`
- `TurnOffEverything`
- `HassSetVolume`
- `HassSetVolumeRelative`

### `custom_sentences/ru/package_temperature.yaml`

- `LargeRoomTemperature`
- `BedroomTemperature`
- `BathroomTemperature`
- `HouseTemperature`

### `custom_sentences/ru/package_vacuum.yaml`

- `StartPauseVacuum`
- `StartVacuum`
- `PauseVacuum`
- `HomeVacuum`
- `EmptyVacuum`
- `CleanEntranceVacuum`
- `CleanKitchenVacuum`
- `CleanHallwayVacuum`
- `CleanLargeRoomVacuum`
- `CleanBedroomVacuum`
- `CleanBathroomVacuum`
- `CleanGuestRoomVacuum`
- `CleanMainVacuum`
- `CleanSecondaryVacuum`

Some names are built-in HA intents with custom sentences (for example
`HassSetVolume`), while others are handled by `intent_script`. The provider
must validate the exact runtime handler instead of assuming every name is a
script.

## 7. Runtime architecture

The new integration should expose a Home Assistant LLM platform. Official
references:

- [Home Assistant LLM API](https://developers.home-assistant.io/docs/core/llm/)
- [Firing intents](https://developers.home-assistant.io/docs/intent_firing/)
- [Conversation API](https://developers.home-assistant.io/docs/intent_conversation_api/)

### Setup

The integration domain is `local_assist_llm`. It needs YAML configuration
support, because package files contain the `local_assist_llm` top-level block.
Do not keep `cv.config_entry_only_config_schema(DOMAIN)` from the reminder
integration for this new domain unless YAML and config-entry modes are
explicitly supported.

At setup:

1. Validate the merged `local_assist_llm` config.
2. Validate intent names and handler availability.
3. Build an immutable catalog and store it under a domain-specific `hass.data`
   key.
4. Build common prompt text for the selected language.
5. Register any reload handling required by the target HA version.

The catalog should be replaced atomically after a successful reload. A broken
entry should be skipped and logged; it should not erase a previously valid
catalog or prevent unrelated packages from loading.

### `async_get_tools`

Home Assistant invokes the LLM platform hook per request. The hook should:

1. read the current immutable catalog;
2. filter by request language if language-specific metadata is introduced;
3. create one tool per exposed intent;
4. sort tools by priority for deterministic diagnostics (sorting is not a
   formal guarantee for the model);
5. return `llm.LLMTools(tools=tools, prompt=prompt_fragment)`.

Use the existing `llm_reminders/llm.py` as the API pattern, but do not reuse
the reminder manager lookup.

### Tool naming

Use stable names such as:

```text
local_assist_hallway_light_off
local_assist_kitchen_light_on
local_assist_clean_hallway_vacuum
```

The exact Assist intent name is stored in the tool instance, not supplied by
the model as a free string. This prevents the model from selecting an
arbitrary handler.

Dynamic tool classes can be created by a factory. Each instance needs its own
`name`, `description`, and `parameters` schema while sharing one execution
implementation.

### Tool execution

For a fixed intent:

```text
LLM → local_assist_hallway_light_off
    → validate empty args
    → intent.async_handle("HallwayLightOff", ...)
    → existing intent_script/script
    → structured success or HomeAssistantError
```

For a parameterized intent, validated `tool_input.tool_args` are converted to
the slots/data shape expected by the handler.

Prefer direct `intent.async_handle` over calling
`conversation.process` from inside the LLM tool. Calling conversation from
inside the selected LLM agent can recursively invoke the same LLM. If the
target HA version makes direct handler invocation impossible for a particular
case, isolate that case and explicitly use the deterministic/default Assist
agent; do not silently call the user-selected LLM agent again.

Tool results must be JSON-serializable. Return enough information for the LLM
to produce a short voice response, for example:

```json
{
  "success": true,
  "intent": "HallwayLightOff",
  "speech": ""
}
```

Raise `HomeAssistantError` for missing handlers, invalid execution data,
unavailable services, or handler failures. The prompt must tell the model not
to retry the action with a native tool after such an error.

## 8. Prompt policy

The integration should return a compact policy fragment with its tools. The
full Home Assistant `prompt.txt` may also contain equivalent rules, but the
integration must not depend on the external prompt being edited correctly.

Suggested Russian fragment:

```text
Для управления Home Assistant сначала проверь локальные Assist-инструменты.
Если запрос соответствует локальному инструменту, обязательно вызови его.
Не заменяй локальный инструмент HassTurnOn/HassTurnOff по области или домену.
Это правило действует даже если физическая сущность имеет domain switch.

«Свет», «люстра», «бра», «подсветка», «пылесос» и другие функциональные
названия относятся к локальным инструментам, если такой инструмент доступен.
HassTurnOn/HassTurnOff используй только если подходящего локального инструмента
нет и действие однозначно.

Если локальный инструмент вернул ошибку, сообщи об ошибке и не повторяй действие
через другой инструмент. Если подходят несколько локальных инструментов,
выбери наиболее специфичный и при равной неоднозначности задай один короткий
вопрос.
```

Every tool description must be self-contained. For example:

```text
Выключает только основной свет коридора через локальный Assist-интент.
Используй для «выключи свет в коридоре» и «погаси свет в коридоре».
Не используй для розеток и не заменяй вызовом по area/domain.
```

Tool descriptions should not expose implementation secrets. Entity IDs are
not necessary in the LLM description; the existing intent handler owns the
actual target.

## 9. Priority, conflicts and fallback

Expected logical order:

1. exact/specific local intent;
2. more specific local intent over generic one;
3. highest declared `priority` for an otherwise equal match;
4. clarification when two local actions remain equally plausible;
5. native HA tool only if no local intent matches and the requested target is
   unambiguous;
6. no fallback after a local handler error.

The provider cannot formally prevent the model from choosing native
`HassTurnOn/Off`, because those tools remain enabled by decision. This is a
known residual risk and must be covered by real acceptance tests with Gemma.

Known overlap to test: `AllLightsOff` has broad phrases such as «выключи свет»,
while room-specific light intents have room phrases. Preserve the existing
Assist semantics; encode explicit examples and priorities rather than silently
inventing a new interpretation.

## 10. Diagnostics

Log structured milestones without secrets:

- catalog load start/end;
- number of declared, valid, skipped and exposed intents;
- tool names returned for an LLM API request;
- tool-call id, local tool name and sanitized args;
- handler success/failure and exception class;
- reload result.

Do not log reminder text, tokens, credentials, or arbitrary user content at
info level. Debug logging can include carefully bounded metadata.

## 11. Tests for the new repository

Keep the existing reminder tests green. Add focused tests for local intents.

### Catalog/config tests

- valid fixed intent creates metadata;
- missing description/examples is rejected or skipped;
- invalid slot type/range is rejected;
- `expose: false` does not create a tool;
- unknown intent handler is reported;
- duplicate intent names are reported;
- multiple package sections merge correctly;
- one invalid entry does not remove valid entries;
- reload atomically replaces the catalog.

### Tool tests

- generated name is stable and unique;
- description contains examples and local-priority warning;
- fixed intent has an empty schema;
- parameterized intent validates required slots and enum/range;
- `HallwayLightOff` calls only `HallwayLightOff` through the mocked intent API;
- no `area`/`domain` target is generated by the local tool;
- handler error raises `HomeAssistantError`;
- no native fallback is invoked by the wrapper;
- tool result is JSON-serializable;
- language/prompt fragment is selected correctly.

### Commands from the existing repository

```bash
python -m compileall -q custom_components/<integration_domain>
python -m pytest tests
```

The Home Assistant configuration repository has no local HA test suite. Its
side must be checked with HA configuration validation/reload and a real Assist
Debug run.

### Acceptance matrix in the real Home Assistant instance

At minimum verify:

- «выключи свет в коридоре» → `local_assist_hallway_light_off` → only
  `switch.hw_light`;
- «включи свет на кухне» → `local_assist_kitchen_light_on`;
- «выключи весь свет» → `local_assist_all_lights_off`;
- guest room lamp/bra/light phrases select distinct tools;
- vacuum room commands select the corresponding vacuum intent;
- volume commands pass the correct numeric/relative slot;
- a command with no local intent can use native HA fallback;
- an intentionally failing local handler produces an error and no retry;
- a phrase that could be broad `area + domain=switch` does not turn off sockets
  when a local light tool is available.

## 12. Implementation order for the next agent

1. Read the target repository README, existing tests and current `llm.py`/
   `llm_tools.py` patterns.
2. Decide whether the old `llm_reminders` integration remains in the release
   or is later replaced. Do not break it while building the first local-intent
   slice.
3. Create the new `local_assist_llm` integration domain with YAML config
   support and an `llm.py` platform.
4. Implement pure catalog parsing/validation and unit tests before HA-specific
   handler execution.
5. Implement dynamic per-intent tools and direct intent handler invocation.
6. Add prompt generation and diagnostics.
7. Add package metadata blocks in the Home Assistant configuration repository,
   beginning with hallway light and kitchen light.
8. Run integration tests and compile checks.
9. Run Home Assistant configuration validation/reload in the real instance.
10. Execute the Gemma acceptance matrix and inspect actual tool calls.

Do not solve the problem by renaming all switches to `light`, by changing
`yandex_station_intents`, or by adding a broad `area + domain=switch` rule.

