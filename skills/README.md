# skills: kursun ve benim skill'lerim, tam hâlleriyle

Bu klasördeki her skill benim yazdığım skill'in tam hâlidir; kısaltılmış kopya yok. Başkalarının
skill'lerini buraya koymadım; bağlantıları aşağıda.

## Görevlerde kullanılanlar

| Klasör | Ne yapar | Görev |
|---|---|---|
| `istatistik/` | Kursun istatistik skill'i: altı kural (önce veriyi tanı, planı sonuca bakmadan yaz, testi gerekçesiyle seç, sayı koddan). Ayrıntı için aşağıdaki skill'lere ve K-Dense'e yönlendirir. | 2, 3 |
| `sekil-stili/` | Kursun şekil skill'i: on kural ve beğendiğim örnek şekiller (`begendiklerim/`). Kuralların tam hâli `dataviz-principles/`'tadır. | 4 |
| `citation-verifier/` | Kaynakçayı PubMed, Crossref ve OpenAlex'e, atıflı her iddiayı tam metne karşı denetler; PDF sayfası ve birebir alıntı ister. Sürüm 1.4.1; kendi testleri `tests/` altında. | 6 |

## Günlük işte kullandığım öbür skill'ler

| Klasör | Ne yapar | Kursta nerede geçti |
|---|---|---|
| `dataviz-principles/` | Şekli Tufte'nin ve Knaflic'in (Storytelling with Data) ilkeleriyle denetler ve düzeltir. | Ders 1: "Bir kitaptan nasıl skill çıkarılır?" |
| `figure-pipeline/` | Projedeki bütün şekilleri tek komutla yeniden üretir; üst üste binen yazıyı, kesik etiketi, boş paneli, Türkçe karakteri ve çözünürlüğü denetler. | |
| `clinical-algorithm-figures/` | Tanı ve tedavi algoritması akış şemalarını vektör PDF olarak çizer. | |
| `manuscript-linter/` | LaTeX taslağında abartıyı, tanım gereği olan ilişkiyi, yapay zekâ kalıplarını ve uydurma atıf örüntülerini işaretler. | Ders 2: "İddianız verinin sınırını aşıyor mu?" |
| `data-integrity-check/` | Makaledeki sayıların kod çıktılarıyla, şekillerin güncel dosyalarla tuttuğunu denetler. | Ders 2: gönderim listesinin ilk maddesi |

## Nasıl kurulur

Görevlerde kurmanız gerekmez: ajan skill'i bu klasörden okur. Kendi projenize almak için ajana şunu yazın
(klasör adını değiştirerek):

```
skills/dataviz-principles klasöründeki skill'i oku, ne yaptığını üç cümleyle özetle;
sonra bu projede kullanılacak biçimde kur.
```

Elle kurmak isterseniz klasörü olduğu gibi kopyalayın. Claude Code'da yeri `~/.claude/skills/` (bütün projeler için)
ya da projenin içinde `.claude/skills/` klasörüdür. Skill'lerin çoğunun dili İngilizcedir; ajan sizinle Türkçe çalışır.

## Kurmadan önce

- Skill bir yöntem kâğıdıdır; içinde bilgisayarınızda çalışan kod da olabilir (`citation-verifier/scripts/`).
  Başkasının skill'ini, benimkiler de içinde, önce ajana özetletin ve sahte verili bir klasörde deneyin.
- Bu skill'ler benim işime göre yazıldı: LaTeX ile yazım, çocuk endokrinolojisi. İşinize uymayan kuralı silin,
  kendi kuralınızı ekleyin.
- Hiçbiri hasta verisine dokunmayı gerektirmez. Kendi verinizle çalışma yolu: [`../KENDI-VERINIZLE.md`](../KENDI-VERINIZLE.md).
- `citation-verifier`'ın kendi bilgisayarımdaki kopyasından tek farkı: kimlik ön denetimi K-Dense'in
  `citation-management` skill'ini kullanır; o skill kurulu değilse ön denetim atlanır, öbür denetimler yapılır.

## Kursta adı geçen, başkalarının yazdığı skill'ler

Bunları buraya kopyalamadım; kaynağından alın.

- İstatistik: K-Dense, Scientific Agent Skills, `statistical-analysis` (MIT). Derste gösterilen sürüm:
  <https://github.com/K-Dense-AI/scientific-agent-skills/tree/593377bb048752abb0152deab9fbb1083a6087df/skills/statistical-analysis>
  Bütün koleksiyon (veri tabanları, literatür, `citation-management` de içinde): <https://github.com/K-Dense-AI/scientific-agent-skills>
- Makale yazımı, dergi biçimi, hakem yanıtı: Kalaris Labs, Research Agent Skills:
  <https://github.com/KalarisLabs/research-agent-skills>
- Yazım kalıpları: Conor Bronsdon, `avoid-ai-writing` (MIT): <https://github.com/conorbronsdon/avoid-ai-writing>
- Makale şekli için başka bir stil: Chen Liu, figures4papers (CC BY-NC 4.0, ticari olmayan kullanım):
  <https://github.com/ChenLiu-1996/figures4papers>

## Lisans

Bu klasördeki skill'ler MIT lisanslıdır (`LICENSE`). `dataviz-principles` içindeki kodlama
[gnurio/tufte-vdqi-plugin](https://github.com/gnurio/tufte-vdqi-plugin)'den (MIT) uyarlandı.
