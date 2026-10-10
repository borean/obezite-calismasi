# obezite-calismasi

Akademik çalışmalarda uygulamalı yapay zekâ kursu · 4. Ankara Pediatri Kongresi, 19 Kasım 2026 ·
Uygulama istasyonu 1: Veriden sonuca

Bir yapay zekâ ajanına verilmek için hazırlanmış küçük bir çalışma klasörü: proje tanıtımı,
sentetik veri ve skill dosyaları.

> **Veri sentetiktir.** `veri/poliklinik_ham.csv` gerçek hasta verisi değildir. Kodla üretildi ve
> içine bilerek veri girişi hataları kondu. Onları bulmak işin parçası.

## Nasıl başlanır

**Ajanla (Codex, Claude Code):** ajana şunu yazın:

```
Bu linkteki klasörü indir ve PROJE.md'yi oku: https://github.com/borean/obezite-calismasi
```

Codex'in giriş dosyası `AGENTS.md`, Claude Code'unki `CLAUDE.md`'dir. Bu kitte `AGENTS.md`,
`PROJE.md`'yi okumayı ister; `CLAUDE.md` aynı dosyayı `@PROJE.md` ile içeri alır.

**Sohbette (ChatGPT, Claude):** yeşil **Code** düğmesi → **Download ZIP**. `PROJE.md`, ilgili
`SKILL.md` dosyasını ve `veri/poliklinik_ham.csv`'yi sohbete yükleyin.

## İçinde ne var

| Yol | Ne |
|---|---|
| `AGENTS.md` | Codex'in yönerge girişi; `PROJE.md`'yi okumaya yönlendirir. |
| `CLAUDE.md` | Claude Code'un yönerge girişi; `@PROJE.md` ile proje bağlamını içeri alır. |
| `PROJE.md` | Projenin sorusu, verisi ve çalışma kuralları. |
| `veri/poliklinik_ham.csv` | 270 çocuk, ham hâliyle. Değişkenler `veri/SOZLUK.md`'de. |
| `skills/istatistik/` | Analiz kuralları ve test gerekçesinin beklenen biçimi. |
| `skills/sekil-stili/` | Dergi şekli kuralları ve beğenilen iki örnek şekil. |
| `skills/citation-verifier/` | Kaynakçadaki DOI'leri ve atıflı iddiaları tam metne karşı denetler (MIT). |
| `kaynak-denetimi/` | Görev 6: altı atıflı cümle, kaynakça ve açık lisanslı iki PDF. Ayrıntı içindeki README'de. |
| `is-karti/` | İki denetim listesi: sayı makaleye girmeden önce (`a-sayi.txt`) ve makaleyi göndermeden önce (`b-gonderim.txt`). Ajana da verebilirsiniz. |

Skill = know-how + örnek dosyalar. Kendi skill'inizi aynı biçimde yazabilirsiniz: bir `SKILL.md`
(adı, ne zaman kullanılacağı, kuralları) ve yanında örnekler.

Dr. Hasan Bora Ulukapı · AYBÜ Yenimahalle EAH Çocuk Endokrinoloji Kliniği · ÇEDD Çocuk Endokrinolojisinde Yapay Zeka Çalışma Grubu (ÇEYAZ)
