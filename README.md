# obezite-calismasi

Akademik çalışmalarda uygulamalı yapay zekâ kursu · 4. Ankara Pediatri Kongresi, 19 Kasım 2026 ·
Uygulama istasyonu 1: Veriden sonuca

Bir yapay zekâ ajanına verilmek için hazırlanmış küçük bir çalışma klasörü: proje tanıtımı,
sentetik veri ve skill dosyaları.

> **Veri sentetiktir.** `veri/poliklinik_ham.csv` gerçek hasta verisi değildir. Kodla üretildi ve
> içine bilerek veri girişi hataları kondu. Onları bulmak işin parçası.

## Gelmeden önce

İstasyondan önce Codex ya da Claude Code'u kurup giriş yapın; olmazsa ChatGPT ya da Claude sohbeti de olur.
Codex ChatGPT masaüstü uygulamasında (menüden Codex; ücretsiz hesapta da açılabilir); Claude Code Pro veya üstü
plan ya da Console hesabı ister (kuruluysa önce `claude update`). Telefon doğrulamasını önceden bitirin.
Boş bir klasörde ajana şunu yazın:

```
git, Python, pandas, scipy, statsmodels, matplotlib ve pypdf kurulu mu? Eksikse kur; bitince hazır de.
```

Mac'te geliştirici araçları penceresi açılırsa Yükle'yi seçin.
Windows'ta Git ya da Python yoksa ajana “winget ile kur” deyin.

## Nasıl başlanır

**Ajanla (Codex, Claude Code):** önce uygulamada boş bir klasör açın, sonra ajana şunu yazın:

```
Bu klasörü indir ve PROJE.md'yi oku: https://github.com/borean/obezite-calismasi
```

İzin isterse: GitHub'dan indirme, Python ve Python paketleri için evet; LaTeX kurmak isterse hayır.

Codex'in giriş dosyası `AGENTS.md`, Claude Code'unki `CLAUDE.md`'dir. Bu kitte `AGENTS.md`,
`PROJE.md`'yi okumayı ister; `CLAUDE.md` aynı dosyayı `@PROJE.md` ile içeri alır.

**Sohbette (ChatGPT, Claude):** yeşil **Code** düğmesi → **Download ZIP**. Her görevde `PROJE.md`,
`veri/SOZLUK.md` ve `veri/poliklinik_ham.csv`'yi sohbete yükleyin; Görev 3'te ayrıca
`skills/istatistik/SKILL.md`'yi (Görev 2'deki kuralınızla), Görev 4'te `skills/sekil-stili/SKILL.md`'yi.
Görev 2'de kuralı `SKILL.md` kopyanıza Not Defteri ya da TextEdit ile kendiniz yazın. Görev 6 sohbette
çalışmaz (ağ ve skill'in script'leri gerekir); onu ajanla yapın.

CSV'yi Excel'de açıp kaydetmeyin; dosyayı olduğu gibi verin.

## Görevler

İstemler istasyon ekranındakiyle aynı; kutunun sağ üstündeki düğmeyle kopyalayın. Her görev kendi başına biter.

**Görev 1 · Veriyi tanıyın.**

```
Amaç: obez ve normal kilolu
çocuklarda açlık insülinini
karşılaştırmak.
Okur: pediatri dergisinin hakemi.
Önce yalnız veriyi tanı; test yapma;
ham dosyaya dokunma. Her sorun için
düzeltme öner; emin olmadıklarını
ayrı yaz ve onayımı bekle.
```

**Görev 2 · Skill'e kuralınızı yazın.**

```
skills/istatistik/SKILL.md'nin
sonuna # Kurallar başlığını ekle;
altına bu kuralı yaz ve git'e
kaydet (git varsa):
<Görev 1'de yakaladığınız kural>
```

**Görev 3 · Analizi skill'le yaptırın.**

```
skills/istatistik/SKILL.md'yi oku
ve kuralıyla uygula: obez ve normal
kilolu çocuklarda açlık insülini
için önce planı yaz, onayımı bekle;
sonra testi gerekçesiyle seç.
Her sayı koddan gelsin.
```

**Görev 4 · Dergi şeklini çizdirin.**

```
skills/sekil-stili/SKILL.md'ye göre
açlık insülinini kilo grubu ve
puberteye göre çiz: her çocuk bir
nokta, prepubertal gri, pubertal
vurgu rengi; panel harfi, her
hücrede n. Başlık bulguyu ilişki
diliyle söylesin.
```

**Görev 5 · Bulgular paragrafını yazdırın.**

```
Analiz çıktısından Türkçe bir
Bulgular paragrafı yaz. Her
sayının geldiği çıktıyı
parantezde belirt. Uzun tire
kullanma. Her karşılaştırmada
farkı ya da oranı %95 GA ile
yaz; p'yi tek başına yazma.
```

**Görev 6 · artı · Kaynakları denetletin.**

```
skills/citation-verifier/SKILL.md'ye
göre kaynak-denetimi/makale.tex'teki
atıfları denetle. Destekleyen
pasaj için PDF sayfası ve birebir
alıntı ver; bulamazsan yaz.
```

## İçinde ne var

| Yol | Ne |
|---|---|
| `AGENTS.md` | Codex'in yönerge girişi; `PROJE.md`'yi ve `DECISIONS.md`'yi okumaya yönlendirir. |
| `CLAUDE.md` | Claude Code'un yönerge girişi; `@AGENTS.md` ile aynı yönergeleri içeri alır. |
| `PROJE.md` | Projenin sorusu, verisi ve çalışma kuralları. |
| `DECISIONS.md` | Onayladığınız analiz kararları, tarih ve gerekçesiyle; ajan çalışma başında okur, yalnız onaylananı ekler. |
| `veri/poliklinik_ham.csv` | 270 çocuk, ham hâliyle. Değişkenler `veri/SOZLUK.md`'de. |
| `skills/istatistik/` | Analiz kuralları ve test gerekçesinin beklenen biçimi. |
| `skills/sekil-stili/` | Dergi şekli kuralları ve beğenilen iki örnek şekil. |
| `skills/citation-verifier/` | Kaynakçadaki DOI'leri ve atıflı iddiaları tam metne karşı denetler (MIT). |
| `kaynak-denetimi/` | Görev 6: altı atıflı cümle, kaynakça ve açık lisanslı iki PDF. Ayrıntı içindeki README'de. |
| `is-karti/` | İki denetim listesi: sayı makaleye girmeden önce (`a-sayi.txt`) ve makaleyi göndermeden önce (`b-gonderim.txt`); bir de yapay zekâ kullanım beyanı örneği (`beyan-iyi.txt`). Ajana da verebilirsiniz. |

Skill = know-how + örnek dosyalar. Kendi skill'inizi aynı biçimde yazabilirsiniz: bir `SKILL.md`
(adı, ne zaman kullanılacağı, kuralları) ve yanında örnekler.

Dr. Hasan Bora Ulukapı · AYBÜ Yenimahalle EAH Çocuk Endokrinoloji Kliniği · ÇEDD Çocuk Endokrinolojisinde Yapay Zeka Çalışma Grubu (ÇEYAZ)
