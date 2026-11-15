# skills-tam: kendi bilgisayarımda kullandığım tam skill'ler

`skills/` altındaki iki kısa skill (`istatistik`, `sekil-stili`) öğretmek için kısa tutuldu: bir sayfada okunur,
Görev 2'de kendi kuralınızı eklersiniz. Günlük işte kullandıklarım daha uzundur. Kendi yazdıklarımın tam hâli bu
klasörde. Görevlerde kullanılmaz; alıp kendi klasörünüze koyabilirsiniz.

| Klasör | Ne yapar | Kursta nerede geçti |
|---|---|---|
| `dataviz-principles/` | Şekli Tufte ve Knaflic'in ilkeleriyle denetler ve düzeltir. | Ders 1: "Bir kitaptan nasıl skill çıkarılır?" |
| `figure-pipeline/` | Projedeki bütün şekilleri tek komutla yeniden üretir; üst üste binen yazıyı, kesik etiketi, boş paneli ve çözünürlüğü denetler. | |
| `clinical-algorithm-figures/` | Tanı ve tedavi algoritması akış şemalarını vektör PDF olarak çizer. | |
| `citation-verifier/` | Kaynakçayı PubMed ve Crossref'e, atıflı her iddiayı tam metne karşı denetler. Güncel sürüm (1.4.1); `skills/citation-verifier/` Görev 6'da kullandığımız önceki sürümdür. | Ders 2: "Kaynak nasıl denetlenir?" |
| `manuscript-linter/` | LaTeX taslağında abartıyı, tanım gereği olan ilişkiyi, yapay zekâ kalıplarını ve uydurma atıf örüntülerini işaretler. | Ders 2: "İddianız verinin sınırını aşıyor mu?" |
| `data-integrity-check/` | Makaledeki sayıların kod çıktılarıyla, şekillerin güncel dosyalarla tuttuğunu denetler. | Ders 2: gönderim listesinin ilk maddesi |

## Nasıl kurulur

Ajana şunu yazın (klasör adını değiştirerek):

```
skills-tam/dataviz-principles klasöründeki skill'i oku, ne yaptığını üç cümleyle özetle;
sonra bu projede kullanılacak biçimde kur.
```

Elle kurmak isterseniz klasörü olduğu gibi kopyalayın. Claude Code'da yeri `~/.claude/skills/` (bütün projeler için)
ya da projenin içinde `.claude/skills/` klasörüdür. Skill'lerin dili İngilizcedir; ajan sizinle Türkçe çalışır.

## Kurmadan önce

- Skill bir yöntem kâğıdıdır; içinde bilgisayarınızda çalışan kod da olabilir (`citation-verifier/scripts/`).
  Başkasının skill'ini, benimkiler de içinde, önce ajana özetletin ve sahte verili bir klasörde deneyin.
- Bu skill'ler benim işime göre yazıldı: LaTeX ile yazım, çocuk endokrinolojisi. İşinize uymayan kuralı silin,
  kendi kuralınızı ekleyin.
- Hiçbiri hasta verisine dokunmayı gerektirmez. Kendi verinizle çalışma yolu: [`../KENDI-VERINIZLE.md`](../KENDI-VERINIZLE.md).

## Başkalarının yazdığı, kullandığım skill'ler

Bunları buraya kopyalamadım; kaynağından alın.

- İstatistik: K-Dense, `statistical-analysis` (MIT). Derste gösterilen sürüm:
  <https://github.com/K-Dense-AI/scientific-agent-skills/tree/593377bb048752abb0152deab9fbb1083a6087df/skills/statistical-analysis>
- Yazım kalıpları: Conor Bronsdon, `avoid-ai-writing` (MIT): <https://github.com/conorbronsdon/avoid-ai-writing>
- Makale yazımı, dergi biçimi, hakem yanıtı: Kalaris Labs, Research Agent Skills:
  <https://github.com/KalarisLabs/research-agent-skills>

## Lisans

Bu klasördeki skill'ler MIT lisanslıdır (`LICENSE`). `dataviz-principles` içindeki kodlama
[gnurio/tufte-vdqi-plugin](https://github.com/gnurio/tufte-vdqi-plugin)'den (MIT) uyarlandı.
