# Kaynak denetimi alıştırması (Görev 6)

Kahvaltı ve vücut ağırlığı üzerine altı atıflı cümle. Bazıları doğru, bazıları bilerek yanlış
kuruldu. Eğitim örneğidir; klinik öneri değildir.

| Dosya | Ne |
|---|---|
| `makale.tex` | Denetlenecek metin: altı atıflı cümle. |
| `kaynakca.bib` | Dört kaynak; en az biri sorunlu. |
| `kaynaklar/kaynaklar.csv` | Her kaynağın DOI'si, PMID'si ve açık erişim bağlantısı. |
| `kaynaklar/ober2021.pdf` | Ober ve ark. Nutrients. 2021;13(4):1351. Lisans: CC BY 4.0. |
| `kaynaklar/sievert2019.pdf` | Sievert ve ark. BMJ. 2019;364:l42. Lisans: CC BY-NC 4.0. |

Cole ve ark. (BMJ. 2000;320:1240) PDF'i lisansı dağıtmaya izin vermediği için kitte yok.
Ajan onu `kaynaklar.csv`'deki bağlantıdan (UCL açık arşivi) indirsin.

**Görev:** `citation-verifier` skill'iyle `makale.tex`'teki atıfları denetleyin. Ajandan şunu isteyin:
“Destekleyen pasaj için PDF sayfası ve birebir alıntı ver; bulamazsan yaz.”
