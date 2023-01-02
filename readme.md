# URLPlayer

Данное дополнение предназначено для удобного прослушивания URL-потоков.

## Предупреждение

Внимание! данное дополнение находится на этапе бета-тестирования и может содержать ошибки. Оно может нагружать процессор, замедлять NVDA или приводить к её падениям, некорректно работать, нарушать работу системы и т.п.

## Возможности

1. Воспроизведение URL-потоков
2. Остановка и запуск воспроизведения одной комбинацией клавиш
3. Переподключение при разрыве соединения
4. Регулировка громкости потока независимо от громкости системы и NVDA
5. Регулировка громкости с шагом в 1, 5 или 100%
6. Переключение между устройствами вывода при помощи комбинаций клавиш
7. Получение названия трека, играющего в данный момент
8. Приостановка воспроизведения при проигрывании звука в другом приложении

## Настройка

Настройки дополнения находятся в меню NVDA -> Параметры -> Настройки... -> URL player

### URL

URL-адрес радиостанции, звукового файла и т.п.

### Возобновлять воспроизведение после запуска NVDA

Если этот флажок отмечен, воспроизведение начнётся после запуска NVDA, если перед её выгрузкой поток проигрывался.

### Приостанавливать воспроизведение, если другое приложение проигрывает звук

Если этот флажок отмечен, Дополнение будет отслеживать другие приложения в системе и приостанавливать воспроизведение, пока в другом приложении проигрывается звук.

#### Способ мониторинга процессов

Имеется два способа отслеживать активность приложений.

##### Состояние

Когда процесс начинает воспроизведение, его состояние звуковой сессии становится активным.

Дополнение отслеживает это состояние и приостанавливает воспроизведение.

Когда воспроизведение заканчивается, состояние звуковой сессии приложения становится неактивным и дополнение возобновляет воспроизведение потока.

##### Пиковая громкость

Windows позволяет получить пиковое значение звука приложения (фактическую громкость его звучания в данный момент).

Дополнение отслеживает пиковые значения приложений и приостанавливает поток, когда пик превышает определённый уровень.

Когда пик снижается, воспроизведение потока возобновляется.

###### Минимальный пик для срабатывания

Значение в процентах. Дополнение будет приостанавливать поток, если пиковое значение приложения выше выбранного.

Можно подобрать это значение таким образом, чтобы поток приостанавливался при, например, воспроизведении видео, но не приостанавливался при получении сообщения.

Для подбора используйте метод тыка, интуицию и логику, а также вам может помочь функция дополнения, показывающая пиковое значение процесса текущего окна.

Данная, также как и другие настройки, не актуальна сразу после изменения, для применения настроек используйте соответствующую кнопку.

##### Минусы первого способа

1. Воспроизведение потока будет приостанавливаться в любом случае, даже если звук, воспроизведённый другим приложением, будет коротким и тихим
2. Воспроизведение будет возобновляться не сразу, так как некоторые приложения не сразу закрывают сессию, и от окончания проигрывания звука до изменения состояния на неактивное может проходить несколько секунд

##### Плюсы первого способа

1. Воспроизведение потока будет останавливаться примерно в тот же момент, когда началось проигрывание звука в другом приложении
2. Воспроизведение потока не будет возобновляться, даже если приложение, проигрывающее звук, какое-то время транслирует тишину (пауза в речи, участок видео без аудио-дорожки и т.п.)

##### Минусы второго способа

1. Воспроизведение потока может останавливаться позже, чем началось проигрывание в другом приложении, так как звук может быть тихим (заставка видео без аудио, начало музыкального трека и т.п.)
2. Воспроизведение потока может возобновиться, если пик процесса стал ниже порогового, то есть приложение, проигрывающее звук, транслирует его слишком тихо (пауза в речи, участок видео без аудио-дорожки и т.п.)

##### Плюсы второго способа

1. Минимальное Пиковое значение можно подобрать таким образом, что воспроизведение потока не будет приостанавливаться, когда звук, воспроизведённый другим приложением, будет коротким и тихим (сообщение в мессенджере, звуковые оповещения в приложениях, обладающих таким функционалом (например TeamTalk) и т.п.)
2. Воспроизведение будет возобновляться раньше, чем при первом способе, так как пиковое значение, скорее всего, снизится раньше изменения состояния сессии на неактивное (подтверждено в TeamTalk и YouTube (Google Chrome)

#### Исключённые процессы

Здесь можно перечислить названия процессов, которые нужно игнорировать, то есть не приостанавливать поток, когда указанные процессы проигрывают звук.

#### Игнорировать фоновые процессы

Если этот флажок отмечен, поток не будет приостанавливаться, когда приложение не на переднем плане проигрывает звук.

## Управление

Все жесты вы можете найти и настроить в меню NVDA -> Параметры -> Жесты ввода -> URL player.

## История изменений

### 0.7

Исправлено некорректное поведение дополнения при добавлении / удалении процесса из исключений.

Повышена стабильность компонента, отвечающего за мониторинг звука приложений.

Реализован тестовый функционал перезагрузки библиотеки bass, используйте его, если уверены, что радио должно играть, но оно не играет.

### 0.6.2

Произведён рефакторинг кода

Выполнен перевод на английский язык (теперь он является стандартным языком дополнения)

### 0.6.1

Внесены незначительные исправления.

### 0.6

Упрощены жесты управления.

Исправлена ошибка, приводившая к падению монитора приложений.

### 0.5

Исправлено некорректное поведение при быстром переключении устройств вывода.

### 0.4-beta

Теперь можно указывать нулевой пик для срабатывания, приложения, пик которых больше нуля будут вызывать приостановку воспроизведения, если соответствующая настройка включена (раньше минимальный порог нельзя было установить меньше 1%).

### 0.3-beta

Добавлена возможность включать / выключать мониторинг других приложений при помощи сочетания клавиш.

Исправление ошибок (некорректное поведение плеера при сохранении настроек, игнорирование некоторых приложений при воспроизведении звука и т.п.).

### 0.2-beta

Значение громкости по умолчанию было 10%, теперь 5%.

Добавлена возможность открывать настройки дополнения при помощи сочетания клавиш.

### 0.1-beta

Первый релиз.
