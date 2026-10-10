# 이미지 생성 프롬프트 — 《내 남자친구는 구미호》

**목표:** 목록에서 스치듯 봐도 멈추게 되는 **대한제국의 미남 구미호**. 화풍은 반실사 웹툰 일러스트이고, 옷과 배경은 개화기 대한제국 감성으로 맞춥니다.

## 확정 디자인 (모든 이미지 공통)

| 항목 | 기준 |
|---|---|
| 눈 — 사람일 때 | 두 눈 모두 **맑은 푸른 눈**, 둥근 사람의 동공 |
| 눈 — 구미호로 변할 때 | **오른쪽 눈**만 푸른 빛을 내는 홍채에 **은빛 세로 동공**. 왼쪽 눈은 사람의 푸른 눈으로 남는다. (오른쪽은 인물 기준이라 화면에서는 **왼쪽**에 보인다) |
| 눈 — 본모습 전체 | 두 눈 모두 푸른 빛 홍채 + 은빛 세로 동공 |
| 꼬리 | **새하얀 꼬리** 아홉 개, 끝까지 순백. 털 장식이나 목도리처럼 보이면 안 된다 |
| 여우불 | 푸른 여우불이 꼬리와 몸을 **휘감아 도는** 흐름. 흩날리는 불씨가 아니라 리본처럼 감기는 불길 |
| 제복 | 대한제국 문관 대례복을 본뜬 **무늬 없는** 검푸른 울 프록코트. 높은 스탠드 칼라와 소매 끝에만 가는 은사 이화문 띠, 은 단추 한 줄, 왼쪽 어깨의 짧은 망토. **꽃무늬 원단, 꽃 브로치, 꼰 장식 줄은 쓰지 않는다** |
| 얼굴 | 창백한 피부, 흐트러진 7:3 흑발, 눈꼬리 홍조, **왼쪽 눈썹 끝의 점** |
| 배경 | 석조전 같은 서양식 석조 궁전, 단청 처마, 가스등, 보름달 |

**쓰지 않는 것:** 갓, 금색 자수, 용·봉황, 꼰 장식 줄과 술 장식, 꽃무늬 원단, 중국풍 건축과 의상.

---

## A. 지금 만든 이미지 고치기

얼굴, 구도, 배경이 잘 나왔으니 다시 생성하기보다 **부분만 고치는 편**이 빠릅니다. 쓰는 도구에 맞는 방법 하나를 고르세요.

### A-1. 말로 고치는 이미지 편집 (ChatGPT, Gemini 등)

이미지를 올리고 아래 문장을 그대로 보내세요.

```
이 이미지의 얼굴, 머리 모양, 표정, 구도, 배경, 타로 카드, 장갑은 그대로 유지하고 아래만 고쳐 주세요.
1. 인물의 오른쪽 눈(화면에서 왼쪽, 앞머리에 가린 쪽)이 보이도록 앞머리를 살짝 걷고, 그 눈을 푸른 빛이 은은하게 나는 홍채에 은색의 가느다란 세로 동공으로 바꿔 주세요. 여우의 눈처럼요.
2. 인물의 왼쪽 눈(화면에서 오른쪽)은 둥근 동공의 평범한 사람의 푸른 눈으로 두세요.
3. 어깨 뒤의 회색 털을 새하얀 여우 꼬리 2~3개로 바꿔 주세요. 끝이 뾰족하게 가늘어지는 풍성한 꼬리이고, 끝까지 순백이며, 옷의 털 장식이나 목도리가 아니라 등 뒤에서 솟아오른 동물의 꼬리로 보여야 해요.
4. 푸른 여우불이 그 흰 꼬리와 인물의 몸을 리본처럼 휘감아 돌게 해 주세요. 흩어진 불씨가 아니라 한 줄기로 감기는 흐름이에요.
5. 제복의 꽃무늬를 줄여 주세요. 옷감은 무늬 없는 검푸른 울로, 은색 꽃 자수는 높은 칼라와 소매 끝에 가는 띠로만 남기고, 가슴의 꽃 브로치와 오른쪽 어깨의 꼰 장식 줄은 지워 주세요. 1900년대 대한제국 관원의 서양식 예복처럼 단정하게요.
```

### A-2. 영어로 고치는 이미지 편집

```
Keep the face, hairstyle, expression, composition, background, tarot card and gloves exactly the same. Change only the following:
1. Lift the fringe slightly so his right eye (on the viewer's left) is visible, and make that eye a fox eye: an iris glowing soft blue with a thin silver vertical slit pupil.
2. Keep his left eye (on the viewer's right) a normal human blue eye with a round pupil.
3. Replace the grey fur behind his shoulders with two or three fluffy pure snow-white fox tails that taper to a point, white to the very tip, clearly animal tails rising from behind him, not a fur collar or coat trim.
4. Add blue foxfire that swirls around the white tails and his body like a flowing ribbon, one continuous spiraling stream of flame rather than scattered sparks.
5. Simplify the uniform: plain unpatterned dark navy wool, silver plum-blossom embroidery only as narrow bands on the high standing collar and the cuffs, remove the flower brooch on the chest and the braided cord on the shoulder. Neat, like a 1900s Korean Empire official's Western-style ceremonial coat.
```

### A-3. 부위별 인페인팅 (Stable Diffusion, NovelAI 등)

해당 부위만 칠하고 프롬프트를 넣으세요. 한 번에 한 부위씩 고치면 결과가 안정적입니다.

**오른쪽 눈** (화면 왼쪽. 앞머리를 같이 칠해야 눈이 드러납니다)
```
fox eye, iris glowing soft blue, thin silver vertical slit pupil, long lower lashes, faint red flush at the outer eye corner, strands of black fringe partly crossing it
```

**왼쪽 눈** (화면 오른쪽)
```
human eye, clear blue iris, round pupil, long lower lashes, faint red flush at the outer eye corner
```
네거티브: `slit pupil, glowing eye`

**꼬리** (어깨 뒤 털 부분)
```
two or three fluffy pure snow-white fox tails rising from behind his shoulders, each tapering to a point, white to the very tip, soft long fur, clearly animal tails
```
네거티브: `grey fur, black fur, fur collar, fur trim, scarf`

**여우불** (꼬리와 몸 주변)
```
blue-white foxfire swirling around the white fox tails and his body like a flowing ribbon, one continuous spiraling stream of flame, glowing particles along the stream
```

**제복** (가슴과 소매, 어깨)
```
plain unpatterned dark navy wool frock coat, high standing collar with a narrow silver plum-blossom embroidery band, narrow silver embroidered band on the cuffs, one row of plain silver buttons, short dark navy cape over the left shoulder
```
네거티브: `floral pattern, brocade, flower brooch, braided cord, aiguillette, epaulette fringe`

---

## B. 처음부터 생성하기 — 10종

| 순서 | 이미지 | 쓰는 곳 | 비율 |
|---|---|---|---|
| 0 | 도겸 기준 시트 | 얼굴 고정용 참조 (업로드 안 함) | 3:2 |
| 1 | **대표 · 썸네일** | 썸네일 + 갤러리 '본모습' | 2:3 |
| 2 | 백도겸 프로필 | 캐릭터 1번 카드 | 1:1 |
| 3 | 윤서 프로필 | 캐릭터 2번 카드 | 1:1 |
| 4 | 면객 프로필 | 캐릭터 3번 카드 | 1:1 |
| 5 | 소개팅의 오판 | 갤러리 '카페' | 2:3 |
| 6 | 월하당 대문 | 갤러리 '월하당' | 2:3 |
| 7 | 안채의 저녁 | 갤러리 '안채' | 2:3 |
| 8 | 가면 행렬 | 갤러리 '가면의 밤' | 2:3 |
| 9 | 본모습 | 갤러리 '본모습' · **비밀** | 2:3 |

1~5번이면 공모전의 '이미지 5장 이상'을 채웁니다.

**만드는 요령**
- **0번을 먼저 만드세요.** 그 얼굴을 캐릭터 참조로 넣고 나머지를 만들면 인물이 흔들리지 않습니다.
- 레퍼런스 그림은 분위기만 참고하세요. 다른 작가의 그림을 참조로 넣어 따라 그리게 하면 저작권 문제가 생길 수 있고, 공모전은 오리지널만 받습니다.
- 실사풍과 글자는 피하고, 전체 이용가 기준을 지키세요.

### 0. 백도겸 기준 시트 (참조용, 업로드하지 않음)

```
Character reference sheet, Korean manhwa romance-fantasy illustration, semi-realistic painterly digital art, soft airbrushed shading, delicate fine line art, clean light grey background, not photorealistic, no text, no labels.
Top row: the same man full body in four views (front, three-quarter, side, back) wearing outfit A. Bottom row: the same man full body front view in outfit B, plus two head close-ups (neutral, smiling).
Baek Dogyeom, a strikingly beautiful Korean man who looks about 30, 184cm, lean but firm build, long neck. Pale porcelain skin, sharp V-line jaw, high straight nose, soft rose-tinted thin lips. Long narrow eyes with slightly downturned outer corners and a faint red flush at the outer corners like natural eyeliner, long lower lashes, clear blue irises with round human pupils. A tiny mole at the outer end of his LEFT eyebrow. Glossy black hair with individually rendered strands, parted 7:3 on his right side, a messy fringe partly covering one eye, nape-length at the back. Human ears. Slender long fingers.
Outfit A: black modern hanbok durumagi coat below the knee over a charcoal jeogori with a thin white collar, a dark navy Western waistcoat over the jeogori with a silver pocket-watch chain, ink stains on one sleeve cuff, black felt fedora with a small silver plum-blossom pin, thin black smart band on his left wrist.
Outfit B: fictional 2050 palace night gatekeeper uniform inspired by Korean Empire (1897-1910) civil officials' Western-style ceremonial dress — plain unpatterned dark navy wool frock coat above the knee, high standing collar, narrow silver plum-blossom embroidery bands only on the collar and cuffs, one row of plain silver buttons, short dark navy cape over the left shoulder, narrow black leather belt, black boots, silver ID card on a black lanyard, short dark navy peaked ceremonial cap with a small silver plum-blossom badge.
No gat, no gold embroidery, no dragons, no floral fabric pattern.
```

### 1. 대표 이미지 · 썸네일 ★

파일명: `대표_구미호_밤.png` · **썸네일로 지정** · 갤러리 그룹은 '본모습'(공개). 일상 그룹에는 넣지 않습니다.

```
Vertical 2:3 cover art, Korean manhwa romance-fantasy illustration, semi-realistic painterly digital art, soft airbrushed shading, delicate fine line art, luminous pale skin, glossy hair with individually rendered strands, cinematic night lighting with soft bloom, shallow depth of field, elegant and alluring cover-art quality, not photorealistic, no text, no watermark, no signature.
Close-up from the chest up. Baek Dogyeom, a strikingly beautiful Korean man who looks about 30: pale porcelain skin, sharp V-line jaw, high straight nose, soft rose-tinted lips, long narrow eyes with slightly downturned outer corners and a faint red flush at the corners, long lower lashes, a tiny mole at the outer end of his LEFT eyebrow, glossy black hair parted 7:3 with a messy fringe, human ears, bare head.
Eyes are the key detail: his RIGHT eye (on the viewer's left) is a fox eye, clearly visible through the fringe, the iris glowing soft blue with a thin silver vertical slit pupil; his LEFT eye (on the viewer's right) is a normal human eye with a clear blue iris and a round pupil.
He wears a plain unpatterned dark navy wool frock coat in the style of 1900s Korean Empire officials' Western-style ceremonial dress: high standing collar and cuffs with only narrow bands of silver plum-blossom (ihwa) embroidery, one row of plain silver buttons, a short dark navy cape over one shoulder. No floral fabric, no brooch, no braided cords.
Head slightly tilted, he looks straight at the viewer with a dangerously gentle half smile. One black-gloved hand rises near his lips, holding a tarot card face-down; the card back is navy with a silver crescent moon and fox.
Behind his shoulders, two or three fluffy pure snow-white fox tails rise and curl into the frame, tapering to a point, white to the very tip, clearly animal tails.
Blue-white foxfire swirls around the white tails and his body like a flowing ribbon, one continuous spiraling stream of flame, with a few red maple leaves caught in it.
Background: deep navy night with a full moon, the softly blurred stone columns of a Western neoclassical palace hall like Deoksugung's Seokjojeon, Korean palace eaves with dancheong, warm gas-lamp street lights. Korean Empire atmosphere, not Chinese. Palette: deep navy, pure white, silver, blue foxfire, autumn red accents.
```

### 2. 백도겸 프로필 (캐릭터 1번 카드)

파일명: `백도겸_프로필.png`

```
Square bust portrait, Korean manhwa romance-fantasy illustration, semi-realistic painterly digital art, soft airbrushed shading, delicate fine line art, luminous pale skin, glossy hair with individually rendered strands, muted pastel palette with soft bloom, shallow depth of field, not photorealistic, no text, no watermark.
Baek Dogyeom, a strikingly beautiful Korean man who looks about 30: pale porcelain skin, sharp V-line jaw, high straight nose, soft rose-tinted lips, long narrow eyes with slightly downturned outer corners and a faint red flush at the corners, long lower lashes, clear blue human eyes with round pupils, a tiny mole at the outer end of his LEFT eyebrow, glossy black hair parted 7:3 with a messy fringe, human ears.
One hand tipping the brim of a black felt fedora with a small silver plum-blossom pin. Black modern hanbok durumagi over a dark navy Western waistcoat, a silver pocket-watch chain at his chest, thin white jeogori collar.
A thin wisp of blue foxfire curls around his fingertips at the hat brim.
Soft, teasing half smile toward the viewer, the left corner of the mouth rising first.
Warm late-afternoon light, a hanok roof and a ginkgo branch softly blurred behind him, gold ginkgo leaves drifting. Korean Empire era (1897-1910) gentleman elegance.
```

### 3. 윤서 프로필 (캐릭터 2번 카드)

파일명: `윤서_프로필.png`

```
Square bust portrait, Korean manhwa romance-fantasy illustration, semi-realistic painterly digital art, soft airbrushed shading, delicate fine line art, warm pastel palette, shallow depth of field, not photorealistic, no text, no watermark.
Yunseo: a pretty Korean woman in her early 30s, round friendly face, bright smiling eyes, glossy dark brown wavy bob with one side tucked behind her ear.
Pale yellow quilted baeja (hanbok vest) over a white blouse with a small lace collar in Korean Empire era style, a blank name badge on a lanyard (no letters), holding a transparent tablet near her chest.
Cheerful, quick-witted expression, mid-laugh.
Softly blurred hanok alley shop behind her with hanging fabric scraps and paper masks, warm daylight.
```

### 4. 면객 프로필 (캐릭터 3번 카드)

파일명: `면객_프로필.png`

```
Square portrait, Korean folk-fantasy manhwa illustration, semi-realistic painterly digital art, soft airbrushed shading, muted cold palette, not photorealistic, no text, all-ages.
A tall mysterious figure wearing a smooth white faceless mask with hanji paper texture: NO eye holes, NO nose, NO mouth, one faint silver thread mark across the forehead.
Faded, worn white durumagi-like robe. One long, smooth white hand with barely visible joints offers a single clear candy wrapped with a silver string on its palm. Fine silver threads hang from its long sleeve.
Grey-blue dusk background with a softly blurred gas-lamp street and festival lanterns.
Quiet, elegant and eerie — unsettling but beautiful, no blood, no wounds.
```

### 5. 소개팅의 오판

파일명: `카페_메뉴판_낮.png` · 그룹: 카페

```
Vertical 2:3, Korean manhwa romance-fantasy illustration, semi-realistic painterly digital art, soft airbrushed shading, delicate fine line art, luminous pale skin, warm pastel daylight with soft bloom, shallow depth of field, not photorealistic, no text.
A sunny café window in alternate-history Seoul, 2050, where the Korean Empire still stands: outside, an old wooden palace gate and a vintage-style streetcar on glass-roofed tracks, softly blurred.
Baek Dogyeom, a strikingly beautiful Korean man about 30, pale skin, long narrow eyes with a faint red flush at the corners, clear blue human eyes with round pupils, tiny mole at the outer end of his LEFT eyebrow, glossy black hair parted 7:3 with a messy fringe, grey wool coat over a charcoal modern jeogori with a thin white collar, thin black smart band on his left wrist.
He pulls one of two cups of cinnamon tea back toward himself while sliding an open menu across the table toward the viewer, with a shy, embarrassed smile — caught being wrong and charming about it.
A paper flyer with small illustrated masks lies at the table edge. Cozy first-date mood, warm backlight.
```

### 6. 월하당 대문

파일명: `월하당_대문_낮.png` · 그룹: 월하당

```
Vertical 2:3, Korean manhwa romance-fantasy illustration, semi-realistic painterly digital art, soft airbrushed shading, delicate fine line art, luminous pale skin, muted pastel palette with soft bloom, not photorealistic, no text, no signboards with letters.
The end of a narrow hanok alley under the palace's north wall, 2050 Seoul; a gas-lamp style street light at the corner, fabric scraps from a hanbok tailor and white paper masks hanging along the alley, gold ginkgo leaves on the stone path.
A wooden gate with a small brass wind chime on a red cord. Baek Dogyeom holds the gate open but stands aside so the doorway is clear, one palm open in a gentle welcome, looking at the viewer with a soft smile.
Dogyeom: strikingly beautiful Korean man about 30, pale skin, long narrow eyes with a faint red flush at the corners, clear blue human eyes, tiny mole at the outer end of his LEFT eyebrow, glossy black hair parted 7:3 with a messy fringe, bare head, black modern durumagi below the knee over a dark navy Western waistcoat with a silver pocket-watch chain, ink stains on the cuffs. His black felt fedora hangs on a peg inside the gate.
Behind him, a glimpse of a fortune-teller's room with a low table and tarot cards, lit by hanji-filtered afternoon light.
```

### 7. 안채의 저녁

파일명: `안채_탈끈_밤.png` · 그룹: 안채

```
Vertical 2:3, Korean manhwa romance-fantasy illustration, semi-realistic painterly digital art, soft airbrushed shading, delicate fine line art, luminous skin, warm orange lamplight with soft bloom, not photorealistic, no text.
A traditional hanok room at night lit by an antique brass lamp. A low table with a bowl of soup gone cold, a crooked white paper mask, and a tangled mask string.
Baek Dogyeom kneels at the table in an off-white cotton jeogori with sleeves rolled to the elbows, collar slightly loose, hair messy with the fringe falling over his forehead, laughing at himself as he fails to untie the string.
Dogyeom: strikingly beautiful Korean man about 30, long narrow eyes with a faint red flush at the corners, clear blue human eyes with round pupils, tiny mole at the outer end of his LEFT eyebrow, glossy black hair, human ears, no fox features.
Behind him on a wooden rack hangs his plain dark navy uniform frock coat with a high collar edged in a narrow silver band, and a short navy cape.
At the table edge, the viewer's hand hesitates (neutral hand, no rings, grey knit sleeve). Intimate, cozy, everyday romance.
```

### 8. 2050 황궁 가면 행렬

파일명: `가면행렬_북문_해질녘.png` · 그룹: 가면의 밤

```
Vertical 2:3, Korean manhwa romance-fantasy illustration, semi-realistic painterly digital art, soft airbrushed shading, dusk sky from gold to deep blue, glowing lanterns and gas-lamp lights with soft bloom, not photorealistic, no text.
A Halloween mask parade flows out of an old wooden palace north gate into a hanok alley in alternate-history Seoul, 2050, where the Korean Empire still stands; a neoclassical stone palace hall glows behind the gate. People wear festive modern hanbok and coats with paper masks; paper lanterns and a vintage-style streetcar in the distance.
In the foreground at the rope line stands Baek Dogyeom in a fictional 2050 palace night gatekeeper uniform inspired by Korean Empire officials' Western-style ceremonial dress: plain unpatterned dark navy wool frock coat, high standing collar and cuffs with only narrow silver plum-blossom embroidery bands, one row of plain silver buttons, a short navy cape over the left shoulder, narrow black belt, silver ID card on a black lanyard, a short navy peaked ceremonial cap with a small silver plum-blossom badge. Not royal, no gold, no dragons, no floral fabric.
Dogyeom: strikingly beautiful Korean man about 30, pale skin, long narrow eyes with a faint red flush at the corners, clear blue human eyes, tiny mole at the outer end of his LEFT eyebrow, glossy black hair parted 7:3. He glances over his shoulder with a serious, protective look.
Far back in the crowd, one white faceless paper mask in a faded white robe walks against the rhythm of the parade, its shadow stretching the opposite way.
Festive and beautiful, quietly eerie.
```

### 9. 본모습 (비밀 이미지)

파일명: `본모습_여우불_밤.png` · 그룹: 본모습 · **갤러리에서 비밀로 켜기 · 해금 비용 50틱 · 최소 해금 조건 100회**

```
Vertical 2:3, Korean manhwa romance-fantasy illustration, semi-realistic painterly digital art, soft airbrushed shading, delicate fine line art, dramatic night lighting with blue glow and soft bloom, not photorealistic, no text, all-ages.
Night on a stone-paved hanok alley outside the palace's north wall, a gas-lamp flickering. Baek Dogyeom in his plain dark navy Korean Empire style gatekeeper uniform — high standing collar with a narrow silver plum-blossom band, short cape torn back by the wind — the collar scorched with blue soot, his peaked cap fallen on the stones.
Both eyes are fox eyes: irises glowing blue with thin silver vertical slit pupils. Human ears — no fox ears, no fangs, no claws. Strikingly beautiful face, faint red flush at the eye corners, tiny mole at the outer end of his LEFT eyebrow, glossy black hair blown by the wind.
Exactly NINE fluffy pure snow-white fox tails, white to the very tip, fan out behind his waist as if growing from his shadow, spread wide like a protective fence between the crowd and the danger; all nine clearly countable.
Blue-white foxfire swirls around the nine white tails and his body in long spiraling ribbons, then spreads low across the stones without burning anyone, revealing a white faceless paper mask that is hollow inside.
A faint deep navy glow shows through the center of his chest. Festival-goers in paper masks step back in the background.
Overwhelming, beautiful, protective — awe rather than horror.
```

---

## 공통 네거티브 프롬프트

```
photorealistic, photo, 3d render, chinese architecture, pagoda, hanfu, wuxia, xianxia, text, letters, hangul, watermark, logo, signature, extra fingers, deformed hands, gat, traditional horsehair hat, hat string, fox ears, fangs, claws, dragon, phoenix, gold embroidery, floral fabric pattern, brocade, flower brooch, braided cord, aiguillette, fringed epaulettes, crown, ikseongwan, red royal robe, yellow royal robe, nudity, blood, gore, wounds, chibi, sketch
```

이미지별로 추가할 네거티브는 다음과 같습니다.

| 이미지 | 추가할 네거티브 |
|---|---|
| 1 대표 | `grey fur, black fur, fur collar, fur trim, both eyes slit pupils, golden eyes, brown eyes` |
| 2, 5~8 일상·프로필 | `fox tails, slit pupils, glowing eyes, golden eyes, brown eyes` |
| 9 본모습 | `fewer than nine tails, more than nine tails, grey tails, black tails, golden eyes` |

## 업로드할 때

- 파일명은 위 이름으로 바꿔 올리세요. AI가 배경을 고를 때 참고합니다.
- 이미지 설명은 `dist/tikita_register.md`의 04 갤러리 표에 있는 문장을 넣으세요.
- 스토리 소개에 넣을 이미지 주소는 `src/images.json`에 넣고 `build.py`를 다시 실행하세요. 붙여 넣은 뒤 **외부 이미지 가져오기**를 누르면 발행됩니다.
- 세부 외형 기준은 `../characters.md`에 있습니다.
