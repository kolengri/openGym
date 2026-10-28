#!/usr/bin/env python3
"""Text-only evidence inventory; default read-only; --output enables artifact creation."""
import argparse,collections,csv,hashlib,json,pathlib,re
ROOT=pathlib.Path.cwd()
records=[json.loads(p.read_text()) for p in sorted((ROOT/'catalogue/exercises').glob('*.json'))]
exercises=sorted((x for x in records if not x.get('variantOf')),key=lambda x:x['id'])
aliases=[x for x in records if x.get('variantOf')]
P={}
def prop(i,en,ru,cat,relation='base',parent=None):
 P[i]={'canonical_id':i,'english_name':en,'russian_label':ru,'category':cat,'relation':relation,'parent_id':parent,'matches':{}}
def add(i,x,tier,field,quote,rule):
 d=P[i]['matches'].setdefault(x['id'],{'exercise_id':x['id'],'exercise_name':x['name'],'source':f"catalogue/exercises/{x['id']}.json",'evidence':[]})
 ev={'tier':tier,'field':field,'quote':quote[:300],'rule':rule}
 if ev not in d['evidence']:d['evidence'].append(ev)
def lines(x):
 yield 'name',x['name']
 yield 'description',x['description']
 for n,s in enumerate(x['instructions']):yield f'instructions[{n}]',s
 for n,s in enumerate(x.get('needs',[])):yield f'needs[{n}]',s
def hit(i,x,pattern):
 for field,s in lines(x):
  m=re.search(pattern,s,re.I)
  if m:
   if re.search(r'\b(?:no|without) (?:a |the )?$',s[max(0,m.start()-14):m.start()],re.I):continue
   if re.search(r'\bas if\b',s,re.I):continue
   if re.search(r'\b(?:imaginary|imagine)\b',s,re.I) and not re.search(r'tape|dots',s,re.I):continue
   tier='optional' if re.search(r'\b(optional|if desired|if needed|for comfort|can also|may use|can use|such as|or imagine| or )\b',s,re.I) else 'explicit'
   add(i,x,tier,field,s,pattern)
# id|English name|Russian label|category|relation|parent; absent relations mean reusable base.
BASE=r"""
dumbbell|Dumbbell pair|Пара гантелей|free_weight
barbell|Straight Olympic barbell|Прямой олимпийский гриф|free_weight
ez_bar|EZ curl bar|EZ-гриф|free_weight
trap_bar|Trap/hex bar|Трэп-гриф|free_weight
kettlebell|Kettlebell|Гиря|free_weight
weight_plate|Weight plate|Блин|free_weight
sandbag|Training sandbag|Песочный мешок|free_weight
macebell|Steel mace|Стальная булава|free_weight
bottle|Weighted bottle pair|Пара бутылок с весом|free_weight
weight_unspecified|Unspecified external load|Неуточнённое отягощение|unresolved
band_loop|Resistance loop band|Кольцевая резинка|band
band_tube|Resistance tube with handles|Эспандер с рукоятями|band
band_unspecified|Resistance band, form unspecified|Резинка неуточнённой формы|band
band_anchor|Band anchor point|Точка крепления резинки|anchor
cable_station|Adjustable cable station|Блочный тренажёр|machine
cable_handle|Single cable D-handle|Одиночная блочная рукоять|attachment|attachment|cable_station
cable_rope|Cable rope handle|Канатная блочная рукоять|attachment|attachment|cable_station
cable_straight_bar|Straight cable bar|Прямая блочная рукоять|attachment|attachment|cable_station
cable_v_bar|V/close-grip cable handle|V-образная блочная рукоять|attachment|attachment|cable_station
cable_lat_bar|Wide lat-pulldown bar|Широкая тяговая рукоять|attachment|attachment|cable_station
ankle_cuff|Ankle cable/band cuff|Манжета на лодыжку|attachment
cable_wrist_cuff|Wrist cable cuff|Кистевая манжета|attachment
landmine_base|Landmine swivel anchor|Шарнир для грифа|anchor
landmine_handle|Landmine/T-bar row handle|Рукоять для лэндмайн-тяги|attachment|attachment|landmine_base
bench|Adjustable utility bench|Универсальная скамья|bench
bench_flat|Flat bench configuration|Горизонтальная скамья|bench|variant|bench
bench_incline|Incline bench configuration|Наклонная скамья|bench|variant|bench
bench_decline|Decline bench configuration|Скамья с отрицательным наклоном|bench|variant|bench
bench_preacher|Preacher curl bench|Скамья Скотта|bench
bench_hyper45|45-degree hyperextension bench|Скамья гиперэкстензии 45°|bench
bench_hyper_horizontal|Horizontal Roman-chair bench|Горизонтальный римский стул|bench
ghd|Glute-ham developer|Тренажёр GHD|bench
chair|Household chair|Стул|support
box|Plyometric box|Плиометрическая тумба|support
step|Aerobic step/riser|Степ-платформа|support
platform|Raised platform/deficit block|Помост или блок для дефицита|support
stairs|Stair flight|Лестничные ступени|environment
rack|Squat/power rack|Силовая рама|rack
barbell_rest|Barbell rack hooks/safeties|Упоры и страховочные ограничители|attachment|attachment|rack
pullup_bar|Pull-up/inverted-row bar|Перекладина|rack
dip_bars|Parallel dip bars|Брусья|rack
parallettes|Low parallettes|Низкие паралетсы|rack
captains_chair|Captain chair/vertical knee-raise station|Стойка подъёма коленей|rack
wall_bars|Stall/training wall bars|Шведская стенка|rack
suspension_straps|Suspension straps with handles|Подвесные петли с рукоятями|suspension
rings|Gymnastic rings with straps|Гимнастические кольца со стропами|suspension
suspension_anchor|Overhead suspension anchor|Верхняя точка подвеса|anchor
stability_ball|Swiss/stability ball|Фитбол|ball
medicine_ball|Medicine ball|Медицинбол|ball
massage_ball|Massage ball|Массажный мяч|ball
bosu|BOSU half ball|Полусфера BOSU|ball
foam_roller|Foam massage roller|Массажный ролл|recovery
ab_wheel|Ab wheel|Ролик для пресса|small_prop
mat|Exercise/yoga mat|Коврик|small_prop
ab_mat|Abdominal support mat|Подушка для пресса|small_prop
towel|Towel|Полотенце|small_prop
slider|Gliding disc/slider|Скользящий диск|small_prop
stick|Mobility/dowel stick|Гимнастическая палка|small_prop
strap|Stretching strap|Ремень для растяжки|small_prop
yoga_block|Yoga block|Блок для йоги|small_prop
support_block|Foot/calf support block or wedge|Опорный блок или клин для стоп|support
trampoline|Elastic bed / mini trampoline|Батут|support
punching_bag|Boxing/kickboxing heavy bag|Боксёрская груша|combat
small_ball|Small hand/grip ball|Мяч для кисти|ball
agility_ball|Agility/reaction drill ball|Мяч для координации|ball
balloon|Inflated balloon|Воздушный шар|small_prop
floor_markers|Floor tape/dot markers|Напольная разметка|small_prop
bed_sheet|Bedsheet suspension substitute|Простыня для подвеса|suspension
monkey_bars|Overhead monkey bars|Рукоход|rack
support_bar|Fixed support bar|Фиксированная опорная перекладина|rack
ball_unspecified|Ball, subtype unspecified|Мяч неуточнённого типа|unresolved
yoga_bolster|Yoga bolster/cushion|Болстер или подушка|small_prop
cone|Agility cone/marker|Конус или маркер|small_prop
hurdle|Agility hurdle|Барьер|small_prop
agility_ladder|Agility ladder|Координационная лестница|small_prop
jump_rope|Skipping rope|Скакалка|rope
battle_rope|Battle rope pair|Канаты для волн|rope
climb_rope|Climbing rope|Канат для лазания|rope
rope_unspecified|Exercise rope, type unspecified|Канат неуточнённого типа|unresolved
rope_anchor|Rope anchor point|Точка крепления каната|anchor
weight_belt|Dip/weight belt and chain|Пояс с цепью для отягощения|attachment
weight_vest|Weighted vest|Жилет-утяжелитель|free_weight
ankle_weight|Ankle weights|Утяжелители на лодыжки|free_weight
wrist_weight|Wrist weights|Утяжелители на запястья|free_weight
head_harness|Weighted head/neck harness|Головная лямка для веса|attachment
backpack|Weighted backpack|Рюкзак с весом|free_weight
wrist_roller|Wrist roller with cord and load|Кистевой роллер с тросом и весом|small_prop
hand_gripper|Hand spring gripper|Кистевой пружинный эспандер|small_prop
sledgehammer|Sledgehammer|Кувалда|strongman
tire|Training tire|Покрышка|strongman
wall|Wall surface|Стена|environment
doorframe|Door frame|Дверной проём|environment
outdoor_bicycle|Outdoor bicycle|Велосипед|cardio
pushup_handles|Push-up handles|Упоры для отжиманий|small_prop
nordic_anchor|Foot/ankle restraint for Nordic and decline work|Фиксатор стоп для нордика и наклонных упражнений|anchor
sissy_support|Sissy squat support station|Опора для сисси-приседа|support
balance_board|Balance/wobble board|Балансировочная доска|support
balance_pad|Foam balance pad|Балансировочная подушка|support
knee_pad|Kneeling/support pad or cushion|Опорная подкладка|small_prop
table|Sturdy table|Устойчивый стол|support
handrail|Support handrail|Поручень|environment
padded_seat|Seat with back pad|Сиденье с мягкой спинкой|support
punch_mitt|Boxing focus mitt/pad|Боксёрская лапа|combat
kick_pad|Kick shield/pad|Макивара для ударов ногами|combat
strongman_axle|Thick axle bar|Толстый гриф Аполлона|strongman|variant|barbell
strongman_carry_handles|Farmer carry handles/frame, ambiguous|Фермерские рукояти или рама, неоднозначно|unresolved
hula_hoop|Hula hoop|Обруч|small_prop
inline_skates|Inline skate pair|Роликовые коньки|cardio
pool|Water pool for hydrotherapy|Бассейн для водной ходьбы|environment
wheel_unspecified|Wheel used as running hand support|Колесо-опора для бега, тип неуточнён|unresolved
strongman_log|Strongman log|Бревно для силового экстрима|strongman
strongman_stone|Atlas/Husafell stone|Камень для силового экстрима|strongman
strongman_yoke|Strongman carrying yoke|Коромысло для переноски|strongman
strongman_frame|Strongman farmer/frame carry|Рама для переноски|strongman
strongman_keg|Strongman keg|Бочка|strongman
strongman_car|Strongman car/truck|Автомобиль для силового экстрима|strongman
strongman_shield|Strongman shield|Щит для переноски|strongman
strongman_wheelbarrow|Strongman wheelbarrow|Силовая тачка|strongman
strongman_iron_block|Strongman iron block|Железный блок|strongman
strongman_mas_board|Mas-wrestling foot board and stick|Доска и палка для мас-рестлинга|strongman
strongman_conan|Conan circle apparatus|Круг Конана|strongman
strongman_hercules|Hercules hold pillars|Стойки удержания Геркулеса|strongman
strongman_viking|Viking press apparatus|Тренажёр викинг-пресс|strongman
strongman_height_weight|Throwing weight with handle|Груз с ручкой для броска|strongman
"""
for row in BASE.strip().splitlines():prop(*row.split('|'))
# Distinct machine geometry; grip/stance alone does not create a model.
MACHINE=r"""
smith|Smith machine|Машина Смита|smith
pilates_reformer|Pilates reformer|Пилатес-реформер|pilates machine
assisted_dip_pullup|Assisted dip/pull-up station|Гравитрон|assisted.*(?:chin|pull|dip)
belt_squat|Belt squat machine|Тренажёр поясного приседа|lever belt
legpress_vertical|Vertical leg press|Вертикальный жим ногами|vertical leg press
legpress_horizontal|Horizontal/seated leg press|Горизонтальный жим ногами|horizontal.*leg press;seated.*leg press;lying.*(?:squat;calf press);seated.*squat calf.*press
legpress_angled|45-degree/angled leg press|Наклонный жим ногами|(?:45;angled).*?(?:leg;calf).*press;(?:leg;calf) press;sled alternating single leg negative press
hack_squat|Linear hack squat machine|Линейный гакк-тренажёр|hack squat;hack.*calf;forward angled calf
pendulum_squat|Pendulum squat machine|Маятниковый гакк-тренажёр|pendulum squat
squat_lever|Lever squat machine|Рычажный тренажёр приседа|chair squat;full squat;pistol squat;seated.*squat;lever squat
abductor_adductor_standing|Standing multi-hip machine|Мультихип стоя|abduction leg raise;abduction squat;adduction thrust;side hip;standing (?:hip;leg;rear kick)
abductor_seated|Seated hip abduction machine|Разведение ног сидя|seated hip abduction;isometric squat hip abduction
adductor_seated|Seated hip adduction machine|Сведение ног сидя|seated hip adduction
leg_extension|Seated leg extension machine|Разгибание ног|leg extension
legcurl_seated|Seated leg curl machine|Сгибание ног сидя|seated.*(?:leg;one leg).*curl
legcurl_lying|Prone leg curl machine|Сгибание ног лёжа|lying.*(?:leg;knee).*?(?:curl;flexion)
legcurl_kneeling|Kneeling leg curl machine|Сгибание ног с колена|kneeling.*leg curl
legcurl_standing|Standing leg curl machine|Сгибание ног стоя|standing.*leg curl
hip_thrust|Hip thrust machine|Тренажёр ягодичного моста|hip thrust
glute_kickback|Glute kickback/hip extension machine|Ягодичный кикбэк-тренажёр|glute press;hip extension
reverse_hyper|Reverse hyperextension machine|Обратная гиперэкстензия|reverse hyperextension
back_extension|Seated back extension machine|Разгибание спины сидя|back extension;seated good morning
calf_donkey|Donkey calf raise machine|Тренажёр ослиного подъёма на носки|donkey calf
calf_seated|Seated calf raise machine|Подъём на носки сидя|seated.*calf raise
calf_standing|Standing calf raise machine|Подъём на носки стоя|standing calf raise;rotary calf
tibialis|Tibialis/toe raise machine|Тренажёр передней голени|toe raise
chest_decline|Decline chest press machine|Жим от груди с отрицательным наклоном|decline chest press
chest_incline|Incline chest press machine|Наклонный жим от груди|incline.*chest press;incline hammer chest
chest_lying|Lying chest press machine|Жим от груди лёжа|lying chest press;bench press machine
chest_standing|Standing chest press machine|Жим от груди стоя|standing chest press
chest_press|Seated chest press machine|Жим от груди сидя|chest press;inner chest press
chest_fly|Pec deck/chest fly machine|Пек-дек для груди|pec deck;seated fly;incline fly;standing pec fly;crossovers
rear_delt|Reverse pec deck/rear-delt machine|Обратный пек-дек|(?:rear;reverse).*?(?:delt fly;fly)
shoulder_press|Shoulder press machine|Жим плечами|shoulder press;military press
lateral_raise|Lateral raise machine|Разведение плеч в тренажёре|lateral raise
pulldown|Lever lat pulldown machine|Рычажная вертикальная тяга|pulldown
high_row|High row machine|Высокая рычажная тяга|high row;vertical row
row_chest_supported|Chest-supported/T-bar lever row|Рычажная тяга с упором грудью|chest support;incline prone;lying.*row;lying.*t bar
row_tbar|Standing T-bar row machine|Т-образная рычажная тяга стоя|t.?bar;bent.over
row_seated|Seated/low lever row machine|Рычажная тяга сидя|row;scapular retraction
pullover|Pullover machine|Пуловер-машина|pullover
biceps_curl|Biceps/preacher curl machine|Бицепс-машина|bicep;preacher curl
triceps_dip|Seated triceps dip machine|Трицепсовый жим сидя|triceps dip;seated dip
triceps_extension|Triceps extension machine|Разгибание рук в тренажёре|triceps extension
shrug|Lever shrug machine|Тренажёр шрагов|shrug
gripper_machine|Lever hand gripper|Рычажный кистевой эспандер|gripper hands
neck_machine|Four-way neck machine|Тренажёр мышц шеи|neck
ab_coaster|Ab coaster machine|Тренажёр ab coaster|ab coaster
ab_swing|Ab swing machine|Тренажёр ab swing|ab swing
ab_crunch_lying|Lying/decline crunch machine|Тренажёр скручиваний лёжа|lying crunch;decline sit up;lying leg raise
ab_crunch_seated|Seated crunch machine|Тренажёр скручиваний сидя|crunch
torso_rotation|Rotary torso machine|Тренажёр поворота корпуса|twist;rotation
deadlift_lever|Lever deadlift machine|Рычажный станок для становой тяги|deadlift
stepper|Stepper machine|Степпер|stepper
stepmill|Rotating stair climber|Лестничный тренажёр|stepmill
curved_treadmill|Self-powered curved treadmill|Безмоторная изогнутая дорожка|curved treadmill
treadmill|Treadmill|Беговая дорожка|treadmill
elliptical|Elliptical/cross trainer|Эллиптический тренажёр|elliptical;cross trainer;wave machine
air_bike|Fan/air bike|Велотренажёр с вентилятором|assault bike
recumbent_bike|Recumbent exercise bike|Горизонтальный велотренажёр|bicycle recline
stationary_bike|Upright exercise bike|Вертикальный велотренажёр|stationary bike
rower|Rowing ergometer|Гребной тренажёр|rowing machine
arm_ergometer|Upper-body ergometer|Ручной велоэргометр|hands bike
skierg|Ski ergometer|Лыжный эргометр|ski ergometer
power_sled|Push/drag training sled|Сани для толкания и тяги|power sled
tank_sled|Wheeled resistance sled|Колёсные силовые сани|torque tank
vibration_plate|Vibration platform|Виброплатформа|vibrate plate
"""
M=[]
for row in MACHINE.strip().splitlines():
 i,en,ru,pattern=row.split('|',3);prop(i,en,ru,'machine');M.append((i,pattern.replace(';','|')))
prop('machine_unspecified','Unresolved machine geometry','Неуточнённая геометрия тренажёра','unresolved')
EQ={'barbell':'barbell','olympic barbell':'barbell','dumbbell':'dumbbell','ez barbell':'ez_bar','trap bar':'trap_bar','kettlebell':'kettlebell','weight plate':'weight_plate','sandbag':'sandbag','macebell':'macebell','stability ball':'stability_ball','medicine ball':'medicine_ball','massage ball':'massage_ball','bosu ball':'bosu','roller':'foam_roller','wheel roller':'ab_wheel','hammer':'sledgehammer','tire':'tire','landmine':'landmine_base','cable':'cable_station'}
# id|regex (semicolon encodes regex alternation).
RULE_TEXT=r"""
dumbbell|\bdumbbells?\b
barbell|\bbarbell\b
ez_bar|\bez[- ](?:bar;curl)
trap_bar|\b(?:trap;hex) bar\b
kettlebell|\bkettlebells?\b
weight_plate|\b(?:weight(?:ed)? plates?;plate[- ]loaded;plates? (?:on;onto;in each;against;with);hold (?:a ;the )?plate)\b
bottle|\bbottles?\b
sandbag|\bsandbag\b
macebell|\b(?:steel mace;macebell)\b
band_loop|\b(?:loop band;mini[- ]band;looped band;band loop;loop the band;band around (?:your )?(?:knees;thighs;ankles;legs))\b
band_tube|\b(?:resistance tubes?;band handles;handles of the (?:resistance )?band)\b
band_anchor|\b(?:anchor;anchored;attach;attached;secure;secured;fix;fixed;loop).{0,55}\bband\b;\bband\b.{0,55}\b(?:anchor;anchored;attach;attached;secure;secured;fixed;stable object)\b
cable_handle|\b(?:d[- ]handles?;single[- ]handles?;stirrup handle)\b
cable_rope|\brope (?:attachment;handle);\b(?:attach;grasp;hold;grip).{0,20}(?:a ;the )?rope\b
cable_straight_bar|\b(?:straight;short) bar (?:attachment;handle);\battach.{0,15}straight bar\b
cable_v_bar|\bv[- ]bar\b;\bclose[- ]grip (?:attachment;handle)\b
cable_lat_bar|\b(?:lat[- ]pulldown bar;wide[- ]grip bar;wide bar;long bar)\b
ankle_cuff|\bankle (?:cuff;strap;attachment);\bcuff.{0,20}ankle\b
cable_wrist_cuff|\bwrist (?:cuff;strap;attachment)\b
landmine_handle|\b(?:landmine;t[- ]bar).{0,20}handle;\bhandle.{0,20}(?:landmine;t[- ]bar)\b
bench|\bbench(?:es)?\b
bench_flat|\bflat bench\b
bench_incline|\binclin(?:e;ed) bench\b
bench_decline|\bdeclin(?:e;ed) bench\b
bench_preacher|\bpreacher (?:bench;pad);\bscott bench\b
bench_hyper45|\b45.{0,20}(?:hyperextension;back extension;hip extension;side bend);\b(?:hyperextension;back extension).{0,25}45\b
bench_hyper_horizontal|\b(?:roman(?:ian)? chair;horizontal hyperextension bench)\b
ghd|\b(?:glute[- ]ham developer;glute ham;ghd)\b
chair|\bchairs?\b
box|\b(?:box(?:es)?;stepbox)\b
step|\b(?:step platform;aerobic step;step box;raised step;low step;stable step;sturdy step;on a step;edge of a step;off step)\b
platform|\b(?:platform;raised block;deficit;elevated surface;raised surface;incline surface;feet elevated on a stable surface)\b
stairs|\b(?:stairs;staircase;stairs steps)\b
rack|\b(?:squat rack;power rack;squat stand;rack the bar;unrack;re-rack;racking)\b
barbell_rest|\b(?:safety bars;safety pins;safety stops;rack hooks;j-hooks)\b
pullup_bar|\b(?:pull[- ]up bar;chin[- ]up bar;horizontal bar;low bar;fixed bar;overhead bar)\b
dip_bars|\b(?:parallel bars;dip bars;dip cage;high parallel)\b
parallettes|\bparallett?es?\b
captains_chair|\bcaptain'?s? chair\b
wall_bars|\b(?:wall bars;stall bars;training wall)\b
rings|\b(?:gymnastic rings;rings;ring (?:pull;row;fly;dip;rollout;curl;arm;face;one;single;reverse;chest;isometric;elevated;wide;resistance;rocky;skin;leg;kneeling;high))\b
suspension_straps|\b(?:suspension trainer;suspension straps;suspender;trx)\b
suspension_anchor|\b(?:overhead anchor;anchor point;securely anchored;securely anchor;sturdy anchor)\b
stability_ball|\b(?:stability;swiss;exercise;fitness) ball\b
medicine_ball|\bmedicine ball\b
massage_ball|\b(?:massage;lacrosse;tennis) ball\b
bosu|\bbosu\b
foam_roller|\b(?:foam;massage) roller\b
ab_wheel|\b(?:ab wheel;ab roller;wheel roller;wheel rollerout)\b
mat|\bmat\b
ab_mat|\bab[- ]?mat\b
towel|\btowels?\b
slider|\b(?:sliders?;gliding discs?;sliding discs?)\b
stick|\b(?:stick;dowel;broomstick)\b
strap|\b(?:stretch(?:ing)? strap;yoga strap;strap around (?:your )?(?:foot;feet);hands or a strap)\b
yoga_block|\byoga blocks?\b
yoga_bolster|\b(?:bolster;cushion;pillow)\b
cone|\bcones?\b;\bagility markers?\b
hurdle|\bhurdles?\b
agility_ladder|\bagility ladder\b
jump_rope|\b(?:jump;skipping;skip) rope\b
battle_rope|\b(?:battling;battle) ropes?\b
climb_rope|\bbodyweight rope\b;\blondon bridge\b;\brope climb;\bropes? climb;\bclimbing rope\b
rope_anchor|\b(?:anchor;attach;secure).{0,40}\bropes?\b;\bropes?\b.{0,40}\b(?:anchor;attach;secured)\b
weight_belt|\b(?:dip belt;weight(?:ed)? belt;belt with (?:a )?(?:weight;chain);weight on a belt;weight with a belt;belt or vest)\b
weight_vest|\b(?:weight(?:ed)? vest;vest)\b
ankle_weight|\bankle weights?\b
wrist_weight|\bwrist weights?\b
head_harness|\b(?:head;neck) harness\b
backpack|\bbackpack\b
wrist_roller|\bwrist rollere?r?\b
hand_gripper|\b(?:hand gripper;hand spring;grip trainer)\b
sledgehammer|\b(?:sledge[- ]?hammer;sledge hammer)\b
tire|\btires?\b
wall|\bwall\b
doorframe|\b(?:doorframe;door frame;doorway;against door)\b
outdoor_bicycle|\boutdoor bicycle\b
pushup_handles|\bpush[- ]?up handles?\b
nordic_anchor|\b(?:nordic;ankles (?:secured;anchored);secure your (?:feet;ankles);feet (?:secured;anchored))\b
sissy_support|\bsissy squat (?:machine;bench);\bsissy.*support\b
balance_board|\b(?:balance;wobble) board\b
strongman_axle|\b(?:apollons axle;thick axle;axle bar)\b
strongman_carry_handles|\bstrongman barbell farmers walk\b
hula_hoop|\bhula hoop\b
inline_skates|\binline skat(?:es;ing)\b
pool|\b(?:hydrotherapy;waist.deep water;chest.deep water)\b
wheel_unspecified|\bwheel run\b
strongman_log|\bstrongman log;\blog lift\b
strongman_stone|\b(?:atlas stones?;hood stones?;husafell;weighted stone;heavy stone)\b
strongman_yoke|\byoke\b
strongman_frame|\btimber carry;\b(?:farmer;carry) frame\b
strongman_keg|\bkeg\b
strongman_car|\b(?:car flip;truck pull)\b
strongman_shield|\bshield carry\b
strongman_wheelbarrow|\bwheelbarrow\b
strongman_iron_block|\biron block\b
strongman_mas_board|\bmas wrestling\b
strongman_conan|\bcircle of conan\b
strongman_hercules|\bhercules hold\b
strongman_viking|\bviking press\b
strongman_height_weight|\bweight for height\b
"""
RULE_TEXT += r"""
support_block|\b(?:block;blocks;wedge)\b
trampoline|\b(?:elastic bed;trampoline)\b
punching_bag|\b(?:boxing bag;punching bag;heavy bag)\b
small_ball|\b(?:small ball;grip ball;soft ball;squeeze ball)\b
agility_ball|\bagility ball\b
balloon|\bballoon\b
floor_markers|\b(?:tape on the floor;line of tape;mark five dots;floor markers;dot markers)\b
bed_sheet|\bbed ?sheet\b
monkey_bars|\bmonkey bars\b
support_bar|\b(?:high bar;vertical bar;set a bar;toes to bar;hangback bar;hang from a bar;hanging from a bar;under a bar;bar or (?:sturdy surface;handles))\b
balance_pad|\b(?:balance pad;foam balance)\b
knee_pad|\b(?:pad under (?:your ;the )?(?:back )?knee;pad under your knee;knee pad;lying back with pad)\b
table|\b(?:hand;forearm).{0,20}(?:on ;resting on )(?:a ;the )?table;\b(?:sturdy table;strong table;under table)\b
handrail|\b(?:rail;railing;handrail)\b
padded_seat|\b(?:seat with your back against the pad;seated back with pad)\b
punch_mitt|\b(?:boxing.{0,40}with partner;partner.s pad;holds a pad)\b
kick_pad|\b(?:kick pad;kickboxing.{0,40}with partner)\b
"""
RULES=[(row.split('|',1)[0],row.split('|',1)[1].replace(';','|')) for row in RULE_TEXT.strip().splitlines() if row.strip()]
machine_eq={'leverage machine','sled machine','smith machine','stepmill machine','stationary bike','elliptical machine','upper body ergometer','skierg machine'}
issues=[]
for x in exercises:
 eq=x['equipment'];name=x['name'];matched_machine=False
 if eq in EQ:
  if not ((eq=='weight plate' and name.startswith('strongman ')) or (eq=='barbell' and re.search(r'yoke|apollons axle|barbell farmers walk',name))):
   add(EQ[eq],x,'explicit','equipment',eq,'equipment exact')
  else:issues.append({'exercise_id':x['id'],'issue':'Coarse equipment enum conflicts with named strongman implement; textual implement takes precedence.'})
 machine_text=' '.join(v for _,v in lines(x))
 if eq in machine_eq or re.search(r'\b(?:treadmill|vibrate plate|smith bar)\b',machine_text) or x['id']=='1028':
  for i,pat in sorted(M,key=lambda z: 0 if z[0] in {'smith','pilates_reformer','assisted_dip_pullup','treadmill','elliptical','air_bike','recumbent_bike','stationary_bike','rower','arm_ergometer','skierg','stepper','stepmill','power_sled','tank_sled','vibration_plate','curved_treadmill'} else 1):
   machine_match=re.search(pat,machine_text if i in {'curved_treadmill','treadmill'} else name,re.I)
   if machine_match:
    field,quote=next(((f,q) for f,q in lines(x) if re.search(pat,q,re.I)),('name',name))
    add(i,x,'explicit',field,quote,pat);matched_machine=True;break
  if not matched_machine and not re.search(r'glute ham|glute ham developer',name):
   add('machine_unspecified',x,'explicit','equipment',eq,'unresolved machine metadata')
 if eq in {'band','resistance band'} or re.search(r'\b(?:band[- ]assisted|band assisted|resistance band)\b',name):add('band_unspecified',x,'explicit','equipment',eq,'equipment exact')
 if eq=='suspension trainer':
  add('rings' if re.search(r'\bring\b',name) else 'suspension_straps',x,'explicit','equipment',eq,'suspension geometry from name')
  add('suspension_anchor',x,'inferred','equipment',eq,'suspended prop needs a load-bearing anchor')
 if eq=='landmine':add('barbell',x,'inferred','equipment',eq,'landmine uses a straight bar')
 for i,pattern in RULES:
  if i=='barbell' and (eq in {'ez barbell','trap bar','smith machine'} or re.search(r'yoke|apollons axle|barbell farmers walk',name)):continue
  if i=='small_ball' and eq=='massage ball':continue
  if i=='support_block' and 'yoga' in name:continue
  if i=='bench' and eq=='leverage machine' and not re.search(r'belt bulgarian',name):continue
  if i=='punch_mitt' and re.search(r'kick|knee kick',name):continue
  if i.startswith('cable_') and i!='cable_station' and eq!='cable':continue
  if i=='rope_anchor' and eq=='cable':continue
  if i=='suspension_anchor' and eq not in {'suspension trainer','body weight'}:continue
  if i=='chair' and re.search(r'chair pose|revolved chair|captain|roman',name):continue
  if i=='stick' and name=='1 2 stick drill':
   issues.append({'exercise_id':x['id'],'issue':'stick in drill name may mean landing/hold cue; instructions specify no physical stick'});continue
  hit(i,x,pattern)
 if eq=='cable':
  for i,pat in [('cable_rope',r'rope'),('cable_v_bar',r'v[- ]bar'),('cable_lat_bar',r'lat pulldown|wide.grip.*pulldown')]:
   if re.search(pat,name,re.I):add(i,x,'inferred','name',name,'attachment inferred from movement/name')
 if eq=='weight plate' and name.startswith('strongman ') and not any(x['id'] in P[i]['matches'] for i in ['weight_plate','strongman_log','strongman_stone','strongman_conan','strongman_hercules','strongman_shield','strongman_viking','strongman_frame','strongman_iron_block','strongman_mas_board','strongman_wheelbarrow']):
  add('weight_unspecified',x,'explicit','description',x['description'],'strongman text specifies load without implement geometry; enum is coarse')
 if eq=='weighted' and not any(x['id'] in P[i]['matches'] for i in ['bottle','weight_plate','sandbag','backpack','weight_vest','ankle_weight','wrist_weight','head_harness','strongman_car','strongman_keg','strongman_height_weight','strongman_stone','hand_gripper','wrist_roller','vibration_plate','dumbbell','barbell','kettlebell']):
  add('weight_unspecified',x,'explicit','equipment',eq,'metadata specifies load without resolved geometry')
 if eq=='body weight' and 'ball' in name and not re.search(r'ballerina|balls of',name) and not any(x['id'] in P[i]['matches'] for i in ['stability_ball','medicine_ball','massage_ball','bosu','small_ball','agility_ball']):
  add('ball_unspecified',x,'explicit','name',name,'ball subtype unspecified')
 if eq=='rope' and not any(x['id'] in P[i]['matches'] for i in ['jump_rope','battle_rope','climb_rope','strap','strongman_car']):
  add('rope_unspecified',x,'explicit','equipment',eq,'rope subtype not resolved')
 if eq=='body weight' and re.search(r'\b(?:pull[- ]?up|chin[- ]?up|inverted row|hang)\b',name) and not re.search(r'between chairs|wall|floor|partner|self assisted',name) and not any(x['id'] in P[i]['matches'] for i in ['pullup_bar','dip_bars','rings','climb_rope']):
  add('pullup_bar',x,'inferred','name',name,'bar inferred from hanging/pulling exercise')
 if re.search(r'\b(?:step up|step-up)\b',name) and not any(x['id'] in P[i]['matches'] for i in ['box','bench','chair','step','stairs']):
  add('step',x,'inferred','name',name,'step-up needs raised support, exact geometry unspecified')
 if re.search(r'\bpreacher curl\b',name) and eq in ['barbell','ez barbell','dumbbell','cable']:
  add('bench_preacher',x,'inferred','name',name,'preacher movement needs arm support')
 if re.search(r'\bnordic\b',name):add('nordic_anchor',x,'inferred','name',name,'Nordic needs foot restraint; partner may substitute')
 if re.search(r'\b(?:hyperextension|45 degrees back extension)\b',name) and eq not in machine_eq and not any(x['id'] in P[i]['matches'] for i in ['stability_ball','ghd','bench','bench_hyper45','bench_hyper_horizontal']):
  add('bench_hyper_horizontal',x,'inferred','name',name,'hyperextension support required; angle unspecified')

# Parametric machine configurations are explicit variants, not independent base machines.
for mid,_ in M:
 for x in exercises:
  if x['id'] not in P[mid]['matches']:continue
  for suffix,label,ru,pat in [
   ('plate_loaded','plate loaded','с блинами',r'plate[- ]loaded'),
   ('stack','weight stack','с грузоблоком',r'\bstack\b'),
   ('outdoor','outdoor','уличный',r'\boutdoor\b')]:
   if re.search(pat,x['name'],re.I):
    vid=mid+'__'+suffix
    if vid not in P:prop(vid,P[mid]['english_name']+' — '+label,P[mid]['russian_label']+' — '+ru,'machine','variant',mid)
    add(vid,x,'explicit','name',x['name'],pat)
for child in ['band_loop','band_tube']:
 P[child]['relation']='variant';P[child]['parent_id']='band_unspecified'
P['band_unspecified']['english_name']='Resistance band base family'
P['band_unspecified']['russian_label']='Резинка: базовое семейство'
# Detect lexical misses and text contradictions as review tasks rather than inventing geometry.
for x in exercises:
 if x['id'] in ['10198','1447','4245','6550','2197','2724','2722','5965','8610','3637','2734']:
  issues.append({'exercise_id':x['id'],'name':x['name'],'issue':'Review geometry or terminology against owner intent; text/metadata alone is insufficient.'})

# Relations describe reusable models and their replaceable components.
for aid in ['ankle_cuff','cable_wrist_cuff']:
 P[aid]['relation']='attachment';P[aid]['parent_id']='cable_station'
for aid in ['weight_belt','head_harness']:
 P[aid]['relation']='attachment'
P['nordic_anchor']['relation']='attachment'
# A small hand ball's exact compliance remains a parameter needing owner confirmation.
for x in exercises:
 if x['id']=='11794':add('small_ball',x,'inferred','name',x['name'],'fingers-on-ball version, paired with 11791')
for x in exercises:
 if x['id']=='11794' and x['id'] in P['ball_unspecified']['matches']:del P['ball_unspecified']['matches'][x['id']]
per_ex=collections.defaultdict(list);out=[]
for i,p in P.items():
 if not p['matches']:continue
 matches=sorted(p['matches'].values(),key=lambda d:d['exercise_id'])
 counts=collections.Counter(ev['tier'] for m in matches for ev in m['evidence'])
 tier=min(counts,key=lambda k:{'explicit':0,'inferred':1,'optional':2}[k])
 n=len(matches);priority='P0' if n>=100 and p['category']!='unresolved' else 'P1' if n>=20 and p['category']!='unresolved' else 'P2' if p['category']!='unresolved' else 'REVIEW'
 r={k:v for k,v in p.items() if k!='matches'}
 r.update(evidence_tier=tier,evidence_tiers=dict(counts),tier_exercise_counts={t:sum(any(e['tier']==t for e in m['evidence']) for m in matches) for t in ['explicit','inferred','optional']},exercise_count=n,exercise_ids=[m['exercise_id'] for m in matches],examples=matches[:5],production_priority=priority)
 out.append(r)
 for m in matches:per_ex[m['exercise_id']].append({'canonical_id':i,'evidence':m['evidence']})
coverage=[]
for x in exercises:
 mapped=per_ex[x['id']];unresolved=[m['canonical_id'] for m in mapped if P[m['canonical_id']]['category']=='unresolved']
 status='unresolved_prop_geometry' if unresolved else 'mapped_props' if mapped else 'no_prop_documented_in_text'
 coverage.append({'exercise_id':x['id'],'name':x['name'],'equipment':x['equipment'],'status':status,'props':mapped})
alias_bookkeeping=[{'alias_id':x['id'],'canonical_exercise_id':x['variantOf'],'source':f"catalogue/exercises/{x['id']}.json"} for x in aliases]
visible_ids={x['id'] for x in exercises}
assert len(visible_ids)==len(exercises)==len(coverage)
assert all(a['canonical_exercise_id'] in visible_ids for a in alias_bookkeeping)
assert all(p['exercise_count']==len(set(p['exercise_ids'])) for p in out)
assert all(p['parent_id'] is None or p['parent_id'] in P for p in out)
summary={'source_record_count':len(records),'visible_exercise_count':len(exercises),'figure_alias_count':len(aliases),'examined_visible_records':len(coverage),'buildable_prop_rows':sum(p['category']!='unresolved' for p in out),'unresolved_placeholder_rows':sum(p['category']=='unresolved' for p in out),'buildable_base_models':sum(p['category']!='unresolved' and p['relation']=='base' for p in out),'buildable_variants':sum(p['category']!='unresolved' and p['relation']=='variant' for p in out),'buildable_attachments':sum(p['category']!='unresolved' and p['relation']=='attachment' for p in out),'all_exercises_accounted_for':len(coverage)==len(exercises),'catalogue_sha256':hashlib.sha256(''.join(json.dumps(x,sort_keys=True) for x in records).encode()).hexdigest(),'equipment_counts':dict(collections.Counter(x['equipment'] for x in exercises)),'canonical_prop_count':len(out),'prop_relation_counts':dict(collections.Counter(p['relation'] for p in out)),'prop_category_counts':dict(collections.Counter(p['category'] for p in out)),'exercise_coverage_counts':dict(collections.Counter(x['status'] for x in coverage)),'production_priority_counts':dict(collections.Counter(x['production_priority'] for x in out)),'issues':issues,'limitations':['Every visible English record is examined; figure aliases are excluded as independent exercises.','Text only: no licensed media is opened, copied or provided to an AI tool.','Regex extraction supports audit and production planning, not a guarantee of visual geometry completeness.','No-prop-documented means no supported prop match in current text; it does not prove equipment-free performance. A floor/ground surface is assumed as part of the scene.','Dimensions, materials, stack-vs-plate mechanisms and hidden accessories often need owner review.','Unresolved generic load/rope/machine rows are retained rather than silently guessed.','Priority is an ordinal planning judgment from exercise count, not measured production time.','Variants may share a reusable model; parent links do not automatically count parent coverage.']}
def report():
 rows=['# Exercise 3D props inventory','',f"Examined **{len(exercises):,} visible exercises** and excluded **{len(aliases):,} figure aliases** from **{len(records):,} source records**.",'',f"Text-supported inventory: **{len(out)} canonical rows**, including unresolved placeholders. This is a complete pass over records, not a claim of complete visual geometry.",'','## Coverage','',f"Buildable rows: **{summary['buildable_prop_rows']}** = {summary['buildable_base_models']} reusable bases + {summary['buildable_variants']} variants + {summary['buildable_attachments']} attachments. Unresolved placeholders: **{summary['unresolved_placeholder_rows']}**.",'']
 rows += [f"- {k}: {v:,}" for k,v in summary['exercise_coverage_counts'].items()]
 rows+=['','## Canonical inventory','','| ID | English | Russian | Category | Relation | Tier | Exercises | Examples | Priority |','|---|---|---|---|---|---|---:|---|---|']
 rows += [f"| {p['canonical_id']} | {p['english_name']} | {p['russian_label']} | {p['category']} | {p['relation']}"+(f" → {p['parent_id']}" if p['parent_id'] else '')+f" | {p['evidence_tier']} | {p['exercise_count']} | {', '.join(p['exercise_ids'][:3])} | {p['production_priority']} |" for p in out]
 rows+=['','## Evidence and limits','']+['- '+s for s in summary['limitations']]
 rows+=['','## Ambiguous and unmapped records','']
 rows += [f"- {issue['exercise_id']}: {issue['issue']}" for issue in issues]
 rows+=['','See exercise-coverage.json for every exercise, its evidence and status; inventory.json for all prop IDs and source examples; summary.json for counts and checksum, and aliases.json for all 922 alias-to-exercise links.','']
 return '\n'.join(rows)
def write_outputs(dest):
 dest.mkdir(parents=True,exist_ok=True)
 for name,data in [('inventory.json',out),('exercise-coverage.json',coverage),('summary.json',summary),('aliases.json',alias_bookkeeping)]:(dest/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 (dest/'report.md').write_text(report())
 with (dest/'inventory.csv').open('w',newline='') as f:
  fields=['canonical_id','english_name','russian_label','category','relation','parent_id','evidence_tier','exercise_count','production_priority','exercise_ids','example_ids']
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader()
  for p in out:w.writerow({**{k:p[k] for k in fields if k not in ['exercise_ids','example_ids']},'exercise_ids':' '.join(p['exercise_ids']),'example_ids':' '.join(m['exercise_id'] for m in p['examples'])})
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=pathlib.Path);ap.add_argument('--list',action='store_true');args=ap.parse_args()
 if args.output:write_outputs(args.output)
 print(json.dumps(summary,ensure_ascii=False,indent=2))
 if args.list:
  for p in out:print(p['canonical_id'],p['exercise_count'],p['examples'][0]['exercise_id'],p['examples'][0]['exercise_name'])
