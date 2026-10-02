"""What to buy: exact names and pages on chipdip.ru, as returned by a search of the site.

I could not open chipdip.ru pages from the build environment, so titles and links come from the
search results ("check" says what was and was not confirmed). Stock and prices change: check them
on the page before ordering.
"""
CD = 'https://www.chipdip.ru/'

# ref (or group key) -> description; 'title' is the product title on chipdip.ru when it was found.
CATALOG = {
    'U1': dict(group='Модули и микросхемы', name='Raspberry Pi Pico 2 (RP2350)', title='Raspberry Pi Pico 2, Программируемый контроллер на базе RP2350 (2 х Arm Cortex-M33 или 2 х Hazard3 RISC-V)',
               url=CD + 'product/raspberry-pi-pico-2-programmiruemyy-kontroller-raspberry-pi-9001738774', pkg='модуль 21 × 51 мм, 40 выводов',
               note='Плата продаётся без штырей: впаяйте штыревую вилку PLS-40 (2 × 20) и вставьте Pico в две панельки PBS-20.', check='название и страница найдены в выдаче chipdip.ru'),
    'U2': dict(group='Модули и микросхемы', name='MCP3008-I/P — АЦП 10 бит, 8 каналов, SPI', title='MCP3008-I/P, АЦП, восьмиканальный, 10 бит, 200 К выборок/с, однополярный, 2.7 В, 5.5 В, [DIP-16]',
               url=CD + 'product/mcp3008-i-p-atsp-vosmikanalnyy-10-bit-200-k-microchip-9000275866', pkg='DIP-16 (0,3″)', note='Ставится в панельку SCS-16.', check='название и страница найдены в выдаче chipdip.ru'),
    'U3': dict(group='Модули и микросхемы', name='Модуль I2S-усилителя на MAX98357A (3 Вт, класс D)', title='DEV-14809, MAX98357A Audio Interface Audio Platform Evaluation Expansion Board',
               url=CD + 'product/dev-14809-max98357a-audio-interface-platform-sparkfun-8005982168', pkg='плата с гребёнкой выводов 2,54 мм',
               note='Выводы: VIN, GND, SD, GAIN, DIN, BCLK, LRC и два вывода для динамика. Порядок смотрите по надписям на плате. Аналог: Adafruit 3006 (документация есть на chipdip.ru, страницу товара подтвердить не удалось).',
               check='страница найдена; наличие и срок поставки не проверены'),
    'Q1': dict(group='Транзисторы и диоды', name='Транзистор BC547B (NPN, 45 В, 0,1 А)', title='BC547B, Транзистор NPN 45В 0.1А 0.63Вт [TO92], Fairchild',
               url=CD + 'product/bc547b-fairchild', pkg='TO-92 (выводы по порядку: коллектор, база, эмиттер)', note='Годится любой NPN малой мощности с коэффициентом усиления > 100.', check='название и страница найдены в выдаче chipdip.ru'),
    'D1': dict(group='Транзисторы и диоды', name='Диод Шоттки 1N5819 (40 В, 1 А)', title='1N5819, Диод Шоттки 40В 1А/25А [DO-41]',
               url=CD + 'product/1n5819-diod-shottki-40v-1a-25a-do-41-mic-9001076085', pkg='DO-41, полоса — катод', note='', check='название и страница найдены в выдаче chipdip.ru'),
    'D2': dict(group='Транзисторы и диоды', name='Светодиод 3 мм, сине-зелёный 505 нм (GNL-3014BGC)', title='Серия GNL-3014 (G-nor), каталог chipdip.ru; модель GNL-3014BGC: сине-зелёный 505 нм, 3 мм, 30°',
               url=CD + 'catalog/popular/gnl-3014', pkg='3 мм, выводы: длинный — анод',
               note='Это страница каталога серии GNL-3014 на chipdip.ru; точную страницу товара BGC найти не удалось. Цвет ближе всего к бирюзовому акценту прибора.', check='модель в выдаче найдена (G-nor, 505 нм); ссылка ведёт на серию, не на сам товар'),
    'R1': dict(group='Резисторы', name='Резистор 4,7 кОм, 0,25 Вт, 5 %', title='CF-25 (С1-4) 0.25Вт, 4.7 кОм, 5%, Резистор углеродистый',
               url=CD + 'product/cf-25-s1-4-0.25vt-4.7-kom-5-rezistor-uglerodistyy-33723', pkg='выводной, 6,3 × 2,3 мм', note='', check='название и страница найдены в выдаче chipdip.ru'),
    'R2': dict(group='Резисторы', name='Резистор 180 Ом, 0,25 Вт, 5 %', title='CF-25 (С1-4) 0.25 Вт, 180 Ом, 5%, Резистор углеродистый, Тайвань',
               url=CD + 'product0/105', pkg='выводной, 6,3 × 2,3 мм', note='', check='название и страница найдены в выдаче chipdip.ru'),
    'C1': dict(group='Конденсаторы', name='Конденсатор электролитический 470 мкФ, 16 В, 105 °C', title='470 мкФ, 16 В, 105°C, TK 8X11, TKR471M1CF11, Конденсатор электролитический алюминиевый (Jamicon)',
               url=CD + 'product/470-mkf-16-v-105-c-tk-8x11-tkr471m1cf11-kondensator-jamicon-9000251734', pkg='радиальный, 8 × 11 мм', note='Полоса на корпусе — минус.', check='название и страница найдены в выдаче chipdip.ru'),
    'C2': dict(group='Конденсаторы', name='Конденсатор электролитический 10 мкФ, 16 В, 105 °C', title='ECAP (К50-35), 10 мкФ, 16 В, 105°C, Конденсатор электролитический алюминиевый',
               url=CD + 'product0/591662343', pkg='радиальный', note='Полоса на корпусе — минус.', check='название и страница найдены в выдаче chipdip.ru'),
    'C3': dict(group='Конденсаторы', name='Конденсатор керамический 100 нФ, 50 В, X7R', title='CM-100N-X7R, Конденсатор керамический, MLCC, монолитный, 100нФ, 50В, X7R, ±10%, SR Passives',
               url=CD + 'product/cm-100n-x7r-kondensator-keramicheskiy-sr-passives-8007033755', pkg='выводной, шаг 5 мм', note='', check='название и страница найдены в выдаче chipdip.ru'),
    'RV1': dict(group='Регуляторы', name='Резистор переменный 10 кОм линейный (B10K), ось 25 мм', title='R-0904N-B10K, L25F, 10 кОм, Резистор переменный, Song Huei',
                url=CD + 'product/r-0904n-b10k-l25f', pkg='9 мм, на плату (выводы под пайку проводов)',
                note='Диаметр оси 6 мм и тип оси (с лыской или рифлёная) по выдаче подтвердить не удалось; ручки ниже крепятся винтом и подходят к обеим.', check='название и страница найдены; диаметр оси не подтверждён'),
    'SW1': dict(group='Разъёмы и коммутация', name='Кнопка с фиксацией ON-OFF (1 А, 250 В AC), красная', title='PBS-11A red, Кнопка с фиксацией ON-OFF (1A 250VAC), красная (SPA-101A1), Jietong Switch',
                url=CD + 'product/pbs-11a-red', pkg='на панель, выводы под пайку', note='Есть также зелёная: PBS-11A green. Размер отверстия в панели смотрите в документации на странице товара: из выдачи подтвердить не удалось.', check='название и страница найдены; размеры не подтверждены'),
    'J1': dict(group='Разъёмы и коммутация', name='Гнездо питания DC 5,5 × 2,1 мм на корпус, с гайкой', title='Гнездо питания DC 5.5x2.1мм на корпус с гайкой, пластик; №10017 гн пит DC 2,1D5,5\\2C\\\\пан М8\\\\DJK-32A\\',
               url=CD + 'product/gnezdo-pitaniya-dc-5.5x2.1mm-na-korpus-s-gaykoy-plastik-8008360461', pkg='крепление М8 в стенке корпуса', note='', check='название и страница найдены в выдаче chipdip.ru'),
    'SPK1': dict(group='Разъёмы и коммутация', name='Динамик 8 Ом, 2 Вт, ø64 мм (VISATON K 64 WP)', title='K 64 WP - 8 OHM, Динамик, миниатюрный, майларовый, универсальный, водостойкий, 2Вт, VISATON',
                 url=CD + 'product0/8002644307', pkg='ø64 мм', note='Дешевле: PSR66N08AK (Mallory, 8 Ом, 1,5 Вт, ø66 мм), но у него полоса от 500 Гц и басов почти нет.', check='название и страница найдены в выдаче chipdip.ru'),
}

# parts bought per group of refs rather than per ref
SHARED = {
    ('C4', 'C5', 'C6', 'C7'): 'C3',
    ('RV2', 'RV3', 'RV4'): 'RV1',
}

EXTRA = [
    dict(group='Монтаж', name='Плата макетная 70 × 90 мм, шаг 2,54 мм', title='PCB 70x90 green, Плата макетная, 70мм х 90мм, PCB (шаг2.54мм), ChipDipDac', url=CD + 'product/pcb-70x90-green', qty='1',
         note='Сквозная металлизация, 26 × 33 отверстия, крепёжные отверстия 3,2 мм.', check='название и страница найдены в выдаче chipdip.ru'),
    dict(group='Монтаж', name='Вилка штыревая 1 × 40, шаг 2,54 мм', title='PLS-40 (DS1021-1x40), Вилка штыревая 2.54мм 1х40pin прямая тип1 на плату', url=CD + 'product/pls-40-ds1021-1x40-vilka-shtyrevaya-2.54mm-1x40pin-connfly-39606', qty='2',
         note='Одна планка режется на две по 20 контактов и впаивается в Pico, вторая — для модуля усилителя (7 контактов).', check='название и страница найдены в выдаче chipdip.ru'),
    dict(group='Монтаж', name='Гнездо на плату 1 × 20, шаг 2,54 мм', title='PBS-20 (DS-1023 - 1x20), Гнездо на плату 2.54мм 1х20pin прямое, Connfly', url=CD + 'product/pbs20', qty='3',
         note='Две — под Pico, из третьей отрежьте 7 контактов под модуль усилителя.', check='название и страница найдены в выдаче chipdip.ru'),
    dict(group='Монтаж', name='Панелька DIP-16 узкая', title='SCS-16 (DS1009-16AN), DIP панель 16 контактов узкая, Connfly', url=CD + 'product/scs-16', qty='1', note='Под MCP3008.', check='название и страница найдены в выдаче chipdip.ru'),
    dict(group='Монтаж', name='Стойка для плат М3 × 15 мм, латунь, отверстие–отверстие', title='PCHSS-15, Стойка для печатных плат, шестигр., латунь, М3, 15 мм', url=CD + 'product/pchss-15-stoyka-dlya-pechatnyh-plat-shestigr-latun-m3-15-connfly-12029', qty='4',
         note='Плата крепится к лицевой панели. Нужны ещё 8 винтов М3 × 6 мм: в выдаче не искал.', check='название и страница найдены в выдаче chipdip.ru'),
    dict(group='Монтаж', name='Набор монтажного провода 0,2–0,5 мм², 30 м', title='ММП (АМП)-Н30-0205, Набор монтажного провода 0.2-0.5 кв.мм, 30 метров, Россия', url=CD + 'product/amp50-mgshv-0.2', qty='1', note='Для проводов к ручкам, кнопке, светодиоду, динамику и перемычек на плате.', check='название и страница найдены в выдаче chipdip.ru'),
    dict(group='Ручки', name='Ручка пластмассовая ø15,7 мм, отверстие 6 мм, с металлической вставкой', title='41009-1, D15.7мм, отв. 6мм, Ручка пластмассовая (метал. вставка)', url=CD + 'product/41009-1-d15.7mm-otv-6mm-ruchka-plastmassovaya-metal-knobs-61887', qty='3', note='Tide, Tone, Volume.', check='название и страница найдены в выдаче chipdip.ru'),
    dict(group='Ручки', name='Ручка ø28 мм, отверстие 6 мм', title='KYP25-18-6, Ручка для РЭА D28мм отв.6мм, Daier', url=CD + 'product/kyp25-18-6', qty='1', note='Surf (большая ручка).', check='название и страница найдены в выдаче chipdip.ru'),
    dict(group='Питание', name='Блок питания 5 В, 2 А, штекер 5,5 × 2,1 мм', title='Блок питания Gembird NPA-AC12, 5В/2А, 10Вт, 3 штекера 5.5х2.1+4x1.7+3.5x1.35мм, черный', url=CD + 'product/blok-pitaniya-gembird-npa-ac12-5v-2a-10vt-3-8048463864', qty='1',
         note='Проверьте по наклейке, что центральный контакт штекера — «плюс».', check='название и страница найдены в выдаче chipdip.ru'),
    dict(group='Прочее', name='Корпус и лицевая панель', title='', url='', qty='1', note='≈ 192 × 101 × 39 мм: два отверстия-кармана под плату и динамик, отверстия под ручки, кнопку, светодиод и гнездо. Печатается на 3D-принтере или режется из листа.', check='в магазине не искал'),
]
