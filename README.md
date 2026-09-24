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
https://github.com/borean/obezite-calismasi reposunu klonla ve PROJE.md'yi oku.
```

**Sohbette (ChatGPT, Claude):** yeşil **Code** düğmesi → **Download ZIP**. `PROJE.md`, ilgili
`SKILL.md` dosyasını ve `veri/poliklinik_ham.csv`'yi sohbete yükleyin.

## İçinde ne var

| Yol | Ne |
|---|---|
| `PROJE.md` | Soru ve çalışma kuralları. Ajan önce bunu okur. |
| `veri/poliklinik_ham.csv` | 270 çocuk, ham hâliyle. Değişkenler `veri/SOZLUK.md`'de. |
| `skills/istatistik/` | Analiz kuralları ve test gerekçesinin beklenen biçimi. |
| `skills/sekil-stili/` | Dergi şekli kuralları ve beğenilen iki örnek şekil. |
| `skills/citation-verifier/` | Kaynakçadaki DOI'leri ve atıflı iddiaları tam metne karşı denetler (MIT). |

Skill = know-how + örnek dosyalar. Kendi skill'inizi aynı biçimde yazabilirsiniz: bir `SKILL.md`
(adı, ne zaman kullanılacağı, kuralları) ve yanında örnekler.

Dr. H. Bora Ulukapı · AYBÜ Yenimahalle EAH · ÇEYAZ Çocuk Endokrinolojisinde Yapay Zeka Çalışma Grubu
