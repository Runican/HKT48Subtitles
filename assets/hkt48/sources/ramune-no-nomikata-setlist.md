# 研究生「ラムネの飲み方」/ Ramune no Nomikata — setlist note

Researched 2026-09-28 (CEST) for subtitler stage-template JSON. **No ASR used. No invented order.**

## Stage name (confirmed)

- **Official JP (setlist page):** 研究生「ラムネの飲み方」公演
- **Official schedule wording (common):** `HKT48 7期研究生「ラムネの飲み方」公演` (e.g. shonichi / birthday listings)
- **Locked EN (pipeline):** Ramune no Nomikata / Kenkyuusei 5th Stage (HKT KKS5)
- **Fandom:** HKT48 Kenkyuusei 5th Stage (HKT KKS5); revival of SKE48 Team KII 3rd Stage「ラムネの飲み方」
- **Period:** 2024-08-11〜2025-07-31 (official setlist + 48pedia + fandom + Wikipedia HKT section)
- **Show example:** KKS5 LOD 2025-05-10（江浦優香生誕祭）— intro catch locks in `q-20260927-001-ramune-intro-catches.md`

Do **not** invent a monthly opening コント for this stage (unlike Himawarigumi「逆上がり」). No source documents a pre-overture sketch block for HKT KKS5.

## Ordered setlist (M00 + M01–M16)

Aligned with official HKT setlist + Mobile + 48pedia + fandom + Wikipedia (parent KII3 + HKT section). Song **order identical** across all five; HKT uses **overture (HKT48 ver.)**.

| # | JP | EN/romaji | type |
|---|----|-----------|------|
| M00 | overture (HKT48 ver.) | overture | instrumental |
| M01 | 兆し | Kizashi | all |
| M02 | 校庭の仔犬 | Koutei no Koinu | all |
| M03 | ディスコ保健室 | Disco Hokenshitsu | all |
| M04 | お待たせSet list | Omatase Set list | all |
| M05 | クロス | Cross | **unit** (3) |
| M06 | フィンランド・ミラクル | Finland Miracle | **unit** (3) |
| M07 | 眼差しサヨナラ | Manazashi Sayonara | **unit** (2) |
| M08 | 嘘つきなダチョウ | Usotsuki na Dachou | **unit** (3) |
| M09 | Nice to meet you ! | Nice to meet you! | **unit** (5) |
| M10 | 孤独なバレリーナ | Kodoku na Ballerina | all |
| M11 | 今 君といられること | Ima Kimi to Irareru Koto | all |
| M12 | ウイニングボール | Winning Ball | all |
| M13 | 握手の愛 | Akushu no Ai | all |
| **ENCORE** | | | |
| M14 | ボウリング願望 | Bowling Ganbou | all (encore) |
| M15 | １６色の夢クレヨン / 16色の夢クレヨン | 16iro no Yume Crayon | all (encore) |
| M16 | ラムネの飲み方 | Ramune no Nomikata | all (encore finale) |

### Orthography notes (do not invent variants as separate songs)

- Official HKT: `ウイニングボール` (ウ); some fan pages write `ウィニングボール` — **prefer official ウ**.
- Official HKT title for M09: `Nice to meet you !` (space before !); fandom/48pedia often drop the space — treat as same song.
- Official M15 heading uses fullwidth `１６色`; common halfwidth `16色` is fine in JSON romaji key `16iro no Yume Crayon`.
- Fandom EN for M07 sometimes `Manazashi, Sayonara` (comma) — prefer `Manazashi Sayonara`.

### Typical shonichi / default unit casts (Wikipedia HKT + fandom; understudies rotate)

| Slot | Song | Default unit (shonichi-era) | size |
|------|------|-----------------------------|------|
| M05 | Cross | Nagano Rara, Ryuto Ayane, Matsumoto Moka | 3 |
| M06 | Finland Miracle | Eura Yuka, Yoshida Mei, Yamakawa Maria | 3 |
| M07 | Manazashi Sayonara | Katahira Sara, Nakano Minami | 2 |
| M08 | Usotsuki na Dachou | Ishikawa Amiyu, Ijima Riria, Tsurukawa Nachi | 3 |
| M09 | Nice to meet you! | Aoki Hinako, Ishii Ayane, Kure Yuna, Tsutsumi Fuka, Matsunaga Yui | 5 |

**Do not hardcode cast into the stage template** — birthday/understudy/12-member formats shuffle. Wikipedia also notes day roles: 仔犬 (often Eura), プリマ in 孤独なバレリーナ (Yoshida Mei), バッター in ウイニングボール (Nakano Minami) — treat as show-specific.

## Typical talk / MC placement (48pedia + fandom MC markers)

1. **M00–M04** opening song cluster (all). No documented opening コント.
2. **MC1／自己紹介** after M04 — photo hush + member intros / catchcopies (**translate**). Birthday shows may overlay catchphrase variants (see q-20260927-001).
3. **M05–M09** unit block (3 → 3 → 2 → 3 → 5). Short post-song bits possible between units (ad-lib; optional).
4. **MC2** after M09 (**translate**).
5. **M10–M12** mid all-group block.
6. **MC3** after M12 (**translate**).
7. **M13** 握手の愛 — parent-stage staging often includes audience handshake; LOD may shorten talk around it.
8. **Encore call** (audience) — **skip** translating; detect so it is not merged into MC.
9. **M14–M15** encore songs.
10. **MC4** after M15, before title (**translate**). **Birthday shows expand this slot** (see below).
11. **M16** ラムネの飲み方 (finale).
12. **End greetings / arigatou** — **skip** translating; still detect after M16.
13. **Outro** (optional final speech) — **translate** if present.

## Birthday-show caveats (Eura Yuka 2025-05-10 style)

Documented for `17:00　HKT48 7期研究生「ラムネの飲み方」公演　江浦優香 生誕祭` (Mobile schedule sche_id=19575; 14 members — 堤楓夏休演).

Typical birthday **insert expands MC4** (after M14–M15, before M16), not a song-order rewrite:

1. Host / 仕切り (this show: 長野らら)
2. Birthday song / celebration
3. Group photo (生誕祭 Ver.)
4. Letter from a nominated member (this show: 石井彩音 → 江浦優香)
5. Birthday speech (~3–4 min; full transcripts on memo + polyhedra)
6. Then **M16 ラムネの飲み方** as usual

Additional birthday risks (mark provisional / show-specific — do **not** bake into default template):

- **Unit shuffle:** polyhedra reports Eura's birthday as first 7th-gen Ramune birthday with a **non-default unit** (Eura + Rara + Ishii on 嘘つきなダチョウ instead of Eura's usual Finland Miracle seat). Default unit map above is shonichi/typical only.
- **Intro catch overlays:** birthday-flavored catchphrase swaps during MC1 (see q-20260927-001; several remain provisional).
- **Cast size:** 16 default; 12-member format also used mid-run; absences announced on schedule.
- Song **order** on birthday LOD still matches the table above (sources do not report song swaps for 2025-05-10 beyond unit cast).

## Short lyric / title fingerprints (sparse ASR probes)

Public first lines from uta-net SKE48 Team KII studio album pages (titles + 1–2 distinctive short phrases only; **not** full lyrics). Use titles alone if probe needs to stay minimal.

| Slot | Title fingerprint | Distinctive short phrases (public) |
|------|-------------------|-------------------------------------|
| M01 | 兆し / Kizashi | 今　僕たちは校舎の屋上に集まり / 夜明けが来るのを一緒に待ってた |
| M02 | 校庭の仔犬 | 校庭の片隅 / 一匹の仔犬が |
| M03 | ディスコ保健室 | 最後のチャイムが鳴ったら / そろそろ始めようか？ |
| M04 | お待たせSet list | ずっと　羨ましかった / 先輩たちのステージ |
| M05 | クロス / Cross | クロス　その胸の / 愛の十字架は |
| M06 | フィンランド・ミラクル | フィンランドの湖には / 恋が叶う |
| M07 | 眼差しサヨナラ | 小雨が降る街は / 無口だね |
| M08 | 嘘つきなダチョウ | 嘘つきなダチョウは / おっとり歩いたり |
| M09 | Nice to meet you! | Nice to meet you! / あなたと出会えて　ホントに嬉しいよ |
| M10 | 孤独なバレリーナ | 孤独に踊って / 愛のバレリーナ |
| M11 | 今 君といられること | ススキが風に揺れて / 黄金の波が寄せる |
| M12 | ウイニングボール | 一番　嬉しいニュースが飛び込む |
| M13 | 握手の愛 | こんなに大きな場所に / みんなが集まってくれる |
| M14 | ボウリング願望 | 仲のいい友達が / 週末に集まって |
| M15 | 16色の夢クレヨン | レッドにブルーにイエロー・ホワイト・ブラック |
| M16 | ラムネの飲み方 | 君が今日も休みだって / 誰かから聞いて心配になったんだ |

uta-net refs (SKE48): 兆し `/song/126783/` … ラムネの飲み方 `/song/126768/` (consecutive album IDs).

## Common deviations (low-confidence flags)

- Unit understudies / birthday shuffles — never assume shonichi cast on a random LOD.
- 12-member vs 16-member formats (from 2024-10 onward).
- Day roles (仔犬 / プリマ / バッター) rotate; Wikipedia lists one common assignment only.
- LOD may trim MC length vs theater; song order stable.
- Parent KII staging notes (握手降下, お立ち台, ボール投げ) may be adapted or shortened on HKT LOD — do not invent HKT-specific staging text.

## Confidence summary

| Item | Confidence | Basis |
|------|------------|-------|
| Stage official JP name | **HIGH** | hkt48.jp/setlist/kenkyusei05 |
| Schedule 「7期研究生」 wording | **HIGH** | official schedule pages |
| KKS5 / Kenkyuusei 5th fan label | **HIGH** | fandom wiki title |
| Song order M00–M16 | **HIGH** | official + Mobile + 48pedia + fandom + Wikipedia (≥4 independent) |
| MC1–MC4 placement | **HIGH** | 48pedia + fandom (same markers) |
| Unit sizes 3/3/2/3/5 | **HIGH** | Wikipedia HKT + fandom + parent KII |
| Default unit casts | **MED** | Wikipedia/fandom shonichi; birthday/understudy overrides |
| No opening コント | **MED–HIGH** | absent from all HKT setlist sources; contrast with documented Saka Agari コント |
| Birthday = expanded MC4 | **HIGH** for Eura 2025-05-10 | polyhedra + memo flow; treat other birthdays as same *pattern* provisional |
| Birthday unit shuffle frequency | **PROVISIONAL** | one documented case (Eura); do not generalize as always |
| Fingerprint first lines | **HIGH** (public uta-net) | titles always safe; phrases for sparse probes only |
| Talk dur_s estimates | **PROVISIONAL** | no grade_anchor_show yet for Ramune; soft hints only in JSON |

## Primary citations

1. HKT official setlist: https://www.hkt48.jp/setlist/kenkyusei05
2. HKT Mobile setlist: https://sp.hkt48.jp/qtheater_setlist_detail?group=kenkyu&type=005
3. 48pedia HKT: https://48pedia.org/HKT48_研究生「ラムネの飲み方」
4. AKB48 Fandom HKT KKS5: https://akb48.fandom.com/wiki/HKT48_Kenkyuusei_5th_Stage
5. Wikipedia (parent + HKT section): https://ja.wikipedia.org/wiki/チームKII_3rd_Stage「ラムネの飲み方」
6. Official schedule examples: https://www.hkt48.jp/schedule/2024/08/18661 ; Mobile birthday: https://sp.hkt48.jp/qschedule_detail?sche_id=19575
7. Birthday flow (Eura 2025-05-10): https://akb48memo.com/eurayuka-14-seitansai/ ; https://polyhedra.blog.jp/archives/32035044.html
8. Fingerprint lyrics (public): https://www.uta-net.com/song/126768/ (title) and sibling `/song/126769/`–`/song/126783/`
9. Prior intro locks: `assets/hkt48/sources/q-20260927-001-ramune-intro-catches.md`
10. Quality-bar sibling: `assets/hkt48/sources/saka-agari-setlist.md`
