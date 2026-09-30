# Team H 6th Stage「目撃者」/ Mokugekisha — setlist note

Researched 2026-09-29 (CEST / Europe/Rome) for subtitler stage-template JSON. **No ASR used. No invented order.**

## Stage name (confirmed)

- **Official JP (setlist page):** チームH「目撃者」公演
- **Official schedule wording:** `12:30　チームH「目撃者」公演` (e.g. 2025-05-10)
- **Locked EN (pipeline):** Mokugekisha / Team H 6th Stage (HKT **H6**)
- **48pedia title:** チームH 6th Stage「目撃者」
- **48plus:** Team H 6th Stage (H6); revival of AKB48 Team A 6th Stage「目撃者」
- **Official setlist path:** `hkt48.jp/setlist/teamh07` / Mobile `group=teamh&type=007`
- **Period:** 2023-02-11〜 (still running as of research date; later H7「一年後の僕たちはどんな恋をしているのだろう」begins 2025-11-24 on official index)
- **Show example:** H6 LOD 2025-05-10 12:30 (`HKT48 250510 H6 LOD 1230 1080p DMM`)

### H6 naming (CONFIRMED)

**Yes — H6 = Team H 6th Stage「目撃者」.**

| Source | Label |
|--------|--------|
| 48pedia | チームH **6th Stage**「目撃者」; sidebar **H6th**「目撃者」 |
| 48plus | Team H **6th Stage (H6)** |
| Fan/DMM title style | `H6 LOD` in user filename |
| Official setlist path | `teamh07` — **not** a contradiction: official index lists 博多レジェンド as an extra Team H billing between H1「手をつなぎながら」and H2「青春ガールズ」, so the **7th listed** page is still the **6th numbered** stage |

Numbered Team H stages (fan/48pedia): H1 手をつなぎながら → H2 青春ガールズ → H3 最終ベルが鳴る → H4 シアターの女神 → H5 RESET → **H6 目撃者** → H7 一年後の…

## Ordered setlist (Z01 + M00 + M01–M16)

Aligned with official HKT setlist + Mobile + 48pedia + Wikipedia parent. Song **order identical** for the parent-stage core; HKT uses **overture (HKT48 ver.)**.

| # | JP | EN/romaji | type |
|---|----|-----------|------|
| Z01 | ミニスカートの妖精 | Miniskirt no Yosei | **zenza** (前座ガールズ, typically 3) — **optional** |
| M00 | overture (HKT48 ver.) | overture | instrumental |
| M01 | 目撃者 | Mokugekisha | all |
| M02 | 前人未踏 | Zenjin Mitou | all |
| M03 | いびつな真珠 | Ibitsu na Shinju | all |
| M04 | 憧れのポップスター | Akogare no Popstar | all |
| M05 | 腕を組んで | Ude wo Kunde | **unit** (3) |
| M06 | 炎上路線 | Enjou Rosen | **unit** (2) |
| M07 | 愛しさのアクセル | Itoshisa no Accel | **solo** (1) |
| M08 | ☆の向こう側 | Hoshi no Mukougawa | **unit** (4) |
| M09 | サボテンとゴールドラッシュ | Saboten to Gold Rush | **unit** (6) |
| M10 | 美しき者 | Utsukushiki Mono | all |
| M11 | アイヲクレ | Ai wo Kure | all |
| M12 | 摩天楼の距離 | Matenrou no Kyori | all |
| M13 | 命の意味 | Inochi no Imi | all |
| **ENCORE** | | | |
| M14 | I'm crying | I'm crying | all (encore) |
| M15 | ずっと ずっと | Zutto Zutto | all (encore) |
| M15b | 青春フルスロットル | Seishun Full Throttle | all (encore) — **HKT insert; optional/verify** |
| M16 | Pioneer | Pioneer | all (encore finale) |

### Orthography / discrepancy notes (do not invent variants as separate songs)

- Official HKT title spacing: `ずっと ずっと` (space); treat as one song.
- `I'm crying` / uta-net sometimes `I'm crying.` — same song.
- `☆の向こう側` — keep star glyph in JA; romaji `Hoshi no Mukougawa`.
- Official desktop setlist page once omitted the **#### 命の意味** heading visually (composer 羽場仁志 line still present); **Mobile + 48pedia + Wikipedia confirm M13** — do not drop it (same class of omission as Saka Agari エンドロール).
- **青春フルスロットル** — see dedicated section below. Not on parent AKB A6; not on official HKT setlist HTML; documented as HKT standing encore by 48pedia/48plus/Nishispo.

### Typical shonichi / default unit casts (48pedia HKT + Wikipedia parent; understudies rotate)

| Slot | Song | Default unit (shonichi-era) | size |
|------|------|-----------------------------|------|
| M05 | Ude wo Kunde | 山内祐奈, 運上弘菜, 伊藤優絵瑠 | 3 |
| M06 | Enjou Rosen | 矢吹奈子, 最上奈那華 | 2 |
| M07 | Itoshisa no Accel | 豊永阿紀 | 1 (solo) |
| M08 | Hoshi no Mukougawa | 渡部愛加里, 市村愛里, 栗原紗英, 堺萌香 | 4 |
| M09 | Saboten to Gold Rush | 石橋颯, 小田彩加, 川平聖, 伊藤優絵瑠, 坂本りの, 荒巻美咲 | 6 |

**Do not hardcode cast into the stage template** — understudy/grad/birthday formats shuffle heavily (48pedia lists dozens of alternates per seat). Parent AKB Accel = solo; Okabe AKB revival used duo — **HKT remains solo-pattern** unless a specific show documents otherwise.

## Typical talk / MC placement (48pedia HKT + parent A markers)

1. **Z01 前座** ミニスカートの妖精 (optional; kenkyuusei) — **skip** translating (song).
2. **M00–M04** opening song cluster (all). No monthly opening コント (unlike Himawarigumi「逆上がり」).
3. **MC1／自己紹介** after M04 — photo hush + member intros / catchcopies (**translate**).
4. **M05–M09** unit block (3 → 2 → solo → 4 → 6). Short post-song bits possible between units (ad-lib; optional).
5. **MC2** after M09 (**translate**).
6. **M10–M12** mid all-group block.
7. **MC3** after M12 (**translate**).
8. **M13** 命の意味.
9. **Encore call** (audience) — **skip** translating; detect so it is not merged into MC.
10. **M14–M15** encore songs (I'm crying → ずっと ずっと).
11. **M15b** 青春フルスロットル — HKT insert; **verify per LOD** (see below).
12. **MC4** after M15 / M15b, before Pioneer (**translate**). Birthday/grad shows may expand or rewrite this window.
13. **M16** Pioneer (finale).
14. **End greetings / arigatou** — **skip** translating; still detect after M16.
15. **Outro** (optional final speech) — **translate** if present.

## 青春フルスロットル (M15b) — confidence split

| Claim | Confidence | Basis |
|-------|------------|-------|
| Performed on HKT shonichi (2023-02-11) as encore before Pioneer | **HIGH** | Nishispo; official YouTube「初披露」; fan reports day-2 |
| Listed as standing encore #3 on 48pedia / 48plus | **HIGH** (wiki documentation) | 48pedia main setlist (not only grad specials) |
| Present on official hkt48.jp / Mobile setlist pages | **ABSENT** | teamh07 + Mobile type=007 list Pioneer immediately after ずっと ずっと |
| Present on official digest timestamps | **ABSENT / skipped** | digest jumps ずっと ずっと → Pioneer |
| Present on **2025-05-10 12:30** LOD specifically | **UNDOCUMENTED** | no setlist report found for that LOD — mark **PROVISIONAL**; do not invent |

**Template rule:** include M15b as `optional: true`. Prefer detecting Pioneer after either M15 or M15b. Do not fail song-order match solely because Seishun is missing.

## Show-specific caveats — 2025-05-10 12:30 LOD

Documented from official schedule `sche_id=19574` + cast-change news:

- **Stage:** `12:30　チームH「目撃者」公演` — **CONFIRMED H6** (not Ramune; Ramune that day was **17:00** 江浦優香生誕祭).
- **Birthday on this LOD?** **NO.** Same-day birthday was the evening KKS5 Ramune show.
- **Cast (final / under-adjusted):** 生野莉奈・石橋颯・石松結菜・市村愛里・北川陽彩・栗原紗英・坂本りの・豊永阿紀・藤野心葉・梁瀬鈴雅・井澤美優・猪原絆愛・大内梨果・福井可憐・森﨑冴彩・龍頭綺音
- **休演:** 山内祐奈（体調不良）→ **福井可憐** 出演（official news 2025-05-09）
- **48pedia note:** 龍頭綺音 first Mokugekisha under appearance dated **2025-05-10**
- Song **order** presumed standard (no source reports a special rewrite for this midday LOD). Seishun presence **unverified** for this date.

## Short lyric / title fingerprints (sparse ASR probes)

Public first lines from uta-net AKB48 Team A 6th Stage studio album pages (titles + 1–2 distinctive short phrases only; **not** full lyrics). Use titles alone if probe needs to stay minimal.

| Slot | Title fingerprint | Distinctive short phrases (public) |
|------|-------------------|-------------------------------------|
| Z01 | ミニスカートの妖精 | 望遠鏡　そっと覗いた夜空に / ビーズのような星の光よ |
| M01 | 目撃者 | テレビのニュースで繰り返し伝えてた / 一発の銃弾が正義　奪ったこと |
| M02 | 前人未踏 | ブンブンしてる室外機が / 夏の夜に息を吐くよ |
| M03 | いびつな真珠 | 大事なものは / 隠しておこう |
| M04 | 憧れのポップスター | 夢の中で / 私だけのために… |
| M05 | 腕を組んで | 夕暮れのポプラ並木は / 枯葉の音で寂しくなる |
| M06 | 炎上路線 | 遠巻きに見てた　あなたのこと / 大好き過ぎて… |
| M07 | 愛しさのアクセル | そんなやさしい眼差しで / 見つめないで　私のことを… |
| M08 | ☆の向こう側 | 心のどこかに / 1つ ☆がある |
| M09 | サボテンとゴールドラッシュ | Go working day and Night / Everybody got a sweat and tear |
| M10 | 美しき者 | 爪を立てて　躊躇しないで / 跡をつけて　柔らかな肌 |
| M11 | アイヲクレ | 彼氏がいると言えずに / ここまで来てしまった |
| M12 | 摩天楼の距離 | 走る長距離バス / 目指すニューヨークシティ |
| M13 | 命の意味 | 生まれた朝を　覚えていない / 最初の記憶は母の笑顔 |
| M14 | I'm crying | 爪に光るバラバラの色が / きっと　大人は理解しない |
| M15 | ずっと ずっと | 何がきっかけだっけ? / 覚えてない |
| M15b | 青春フルスロットル | (title probe; HKT original — use title primarily) |
| M16 | Pioneer | 都会の片隅 / 蜃気楼みたいに |

uta-net refs (AKB48 A6 album consecutive IDs): ミニスカートの妖精 `/song/119654/` … Pioneer `/song/119670/`.

## Common deviations (low-confidence flags)

- Unit understudies / seat reshuffles — never assume shonichi cast on a random LOD.
- Zenza may be omitted in some periods (48pedia notes gaps, e.g. early 2024).
- 青春フルスロットル may be present or absent depending on era/show — verify.
- Graduation shows rewrite post-encore heavily (48pedia documents many special blocks) — **do not** use grad LOD as grade_anchor.
- LOD may trim MC length vs theater; song order for core M01–M16 stable when Seishun is treated as optional.
- Parent AKB staging notes (Berlin Wall footage on 目撃者, saber on Accel, rose throw on I'm crying) may be adapted on HKT — do not invent HKT-specific staging text into the template.

## Confidence summary

| Item | Confidence | Basis |
|------|------------|-------|
| Stage official JP name | **HIGH** | hkt48.jp/setlist/teamh07 |
| H6 / Team H 6th Stage label | **HIGH** | 48pedia + 48plus + schedule「チームH「目撃者」」 |
| Song order M00–M15 + M16 Pioneer | **HIGH** | official + Mobile + 48pedia + Wikipedia (≥4 independent) |
| M13 命の意味 present | **HIGH** | Mobile + 48pedia + Wikipedia (despite desktop heading omission) |
| MC1–MC4 placement | **HIGH** | 48pedia HKT (same markers as parent A) |
| Unit sizes 3/2/1/4/6 | **HIGH** | Wikipedia parent + 48pedia HKT shonichi seats |
| Default unit casts | **MED** | 48pedia shonichi; heavy understudy overrides |
| Zenza optional | **HIGH** | official + 48pedia 前座 section; periods of absence noted |
| Seishun as HKT encore insert (exists) | **HIGH** | Nishispo + 48pedia + 48plus + shonichi video |
| Seishun on every 2025 LOD | **PROVISIONAL** | official pages omit; no 2025-05-10 confirmation |
| 2025-05-10 = H6 not birthday | **HIGH** | official schedule 19574 + cast-change news |
| Fingerprint first lines | **HIGH** (public uta-net) | titles always safe; phrases for sparse probes only |
| Talk dur_s estimates | **PROVISIONAL** | no grade_anchor_show yet for Mokugekisha; soft hints only in JSON |

## Primary citations

1. HKT official setlist: https://www.hkt48.jp/setlist/teamh07
2. HKT Mobile setlist: https://sp.hkt48.jp/qtheater_setlist_detail?group=teamh&type=007
3. 48pedia HKT H6: https://48pedia.org/チームH_6th_Stage「目撃者」
4. 48plus H6: https://48plus.org/wiki/Team_H_6th_Stage
5. Wikipedia (parent + HKT section): https://ja.wikipedia.org/wiki/チームA_6th_Stage「目撃者」
6. Official schedule 2025-05-10 12:30: https://www.hkt48.jp/schedule/2025/05/19574
7. Mobile schedule: https://sp.hkt48.jp/qschedule_detail?sche_id=19574
8. Cast change (Yamauchi → Fukui): https://www.hkt48.jp/news/2025/05/10553
9. Nishispo shonichi (Seishun + Pioneer): https://www.nishinippon.co.jp/item/1052841/
10. Official digest timestamps: https://akb.48lover.com/log/223976
11. Fingerprint lyrics (public): https://www.uta-net.com/song/119654/ … `/song/119670/`
12. Quality-bar siblings: `assets/hkt48/sources/saka-agari-setlist.md`, `ramune-no-nomikata-setlist.md`
