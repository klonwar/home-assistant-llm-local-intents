# Handoff: metadata для Home Assistant `llm_local_intents`

Этот документ предназначен следующему агенту, который работает в
конфигурационном репозитории Home Assistant. Репозиторий интеграции уже
содержит runtime-код; данный handoff описывает только изменения конфигурации
и проверки в реальном HA.

## Границы

- Репозиторий конфигурации: `C:\Users\klonw\PhpstormProjects\home-assistant`.
- Не изменять исходник интеграции напрямую и не редактировать dist-каталог
  `custom_components` в конфигурационном репозитории.
- Не менять hardware-сущности, существующие scripts, `yandex_station_intents`
  или native `HassTurnOn`/`HassTurnOff` tools.
- Не добавлять центральный manifest. Metadata должна находиться рядом с
  соответствующим `intent_script` в том же package-файле.

## Точный YAML-контракт

Используется top-level key `llm_local_intents` (имя интеграции не
переименовывать):

```yaml
intent_script:
  ExampleIntent:
    # существующий handler без изменений
    action: ...

llm_local_intents:
  intents:
    ExampleIntent:
      description: "Короткое описание конкретного действия"
      examples:
        - "естественная фраза пользователя"
        - "альтернативная естественная фраза"
      priority: 50
      slots: {}
```

`description` и минимум один непустой `examples` обязательны. `expose` по
умолчанию `true`; служебные handlers можно скрыть через `expose: false`.
`priority` по умолчанию `50`, большее значение используется для сортировки и
диагностики. Slot metadata поддерживает `integer`, `number`, `string`,
`boolean`, `required`, `minimum`, `maximum` и `enum`. Для enum mapping ключ —
значение, которое отправляет LLM, значение — внутреннее значение handler.

Повторяющиеся `llm_local_intents` sections из packages должны быть объединены
Home Assistant в mapping. Имена intent должны быть глобально уникальны. Не
добавлять metadata для `yandex_station_intents`.

## Inventory для metadata

Добавить записи для всех существующих локальных Assist-интентов, сопоставив их
с package-файлом, где объявлен handler:

- `package_lights_sockets.yaml`: `LargeRoomLightOn/Off`,
  `BedroomLightOn/Off`, `BathroomLightOn/Off`, `GuestRoomLightOn/Off`,
  `GuestRoomLampOn/Off`, `GuestRoomBraOn/Off`, `HallwayLightOn/Off`,
  `HallwayBedBulbOn/Off`, `KitchenLightOn/Off`, `AllLightsOn/Off`,
  `KitchenStripOn/Off`, `DimaDeskLampOn/Off`, `DimaRaspberryPiOn/Off`,
  `DimaCarpetOn/Off`, `AnnaMonitorOn/Off`, `AnnaDeskLampOn/Off`,
  `AnnaChargerOn/Off`.
- `package_features.yaml`: `CancelAssistant`, `TurnOffEverything`,
  `HassSetVolume`, `HassSetVolumeRelative`.
- `package_temperature.yaml`: `LargeRoomTemperature`, `BedroomTemperature`,
  `BathroomTemperature`, `HouseTemperature`.
- `package_vacuum.yaml`: `StartPauseVacuum`, `StartVacuum`, `PauseVacuum`,
  `HomeVacuum`, `EmptyVacuum`, `CleanEntranceVacuum`, `CleanKitchenVacuum`,
  `CleanHallwayVacuum`, `CleanLargeRoomVacuum`, `CleanBedroomVacuum`,
  `CleanBathroomVacuum`, `CleanGuestRoomVacuum`, `CleanMainVacuum`,
  `CleanSecondaryVacuum`.

Имена `HassSetVolume` и `HassSetVolumeRelative` могут быть встроенными
Assist-интентами, а не `intent_script`; всё равно добавлять metadata, если
runtime handler зарегистрирован. Для volume проверить slot contract и передать
числовые значения без изменения семантики.

Для каждой записи написать 2–4 естественных примера на русском, отражающих
реальные sentence grammar. Не копировать project-specific examples в исходник
интеграции: они принадлежат только этому конфигурационному репозиторию.

## Применение и проверка

1. Установить/обновить интеграцию `llm_local_intents` из её исходного
   репозитория и перезапустить HA при необходимости.
2. Выполнить Home Assistant configuration check. Исправить YAML/schema ошибки
   до reload; отдельно проверить duplicate intent names.
3. Выполнить штатный reload YAML-конфигурации и убедиться в логах, что число
   declared/exposed/skipped entries соответствует ожиданиям.
   Интеграция получает свежий merged config через штатный HA reload helper,
   поэтому не требуется watcher или ручное чтение package-файлов.
4. В Assist Debug проверить наличие generated tools. Имена строятся как
   `local_assist_` + snake_case имени intent, например
   `local_assist_hallway_light_off`.

## Acceptance matrix

- «выключи свет в коридоре» вызывает `local_assist_hallway_light_off` и
  выключает только `switch.hw_light`.
- «включи свет на кухне» вызывает `local_assist_kitchen_light_on`.
- «выключи весь свет» вызывает `local_assist_all_lights_off`.
- Фразы guest room для lamp, bra и общего light выбирают разные tools.
- Команды уборки выбирают соответствующий vacuum intent по комнате.
- Команды установки абсолютной и относительной громкости передают правильные
  числовые slots.
- Команда без local match может использовать native HA fallback, если цель
  однозначна.
- Намеренно падающий local handler возвращает ошибку и не вызывает native tool.
- Формулировка с `area + domain=switch` не выключает розетки, когда доступен
  соответствующий local light tool.

Зафиксировать фактические tool calls и результаты в отчёте следующего агента.
