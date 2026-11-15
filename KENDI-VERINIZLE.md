# Kendi verinizle çalışmak

Bu kitteki veri sentetiktir; ajan onu görebilir. Kendi hastalarınızın tablosunda durum farklıdır: ajanın okuduğu her
satır modelin sunucusuna gider ve adı silip kod vermek tabloyu anonim yapmaz. Sağlık Bakanlığı'nın 05.03.2020 tarihli
yazısına göre takma adlı ya da psödoanonim veri anonim veri sayılmaz.

Üç yol var. Üçünde de çalışmanın etik kurul onayı gerekir. Aşağıdakiler öneridir; kurumunuzun kuralı önce gelir.

| Yol | Hasta satırı | Gerekir | Zayıf yanı |
|---|---|---|---|
| 1. Anonim tablo, buluttaki ajan | buluta gider | gerçek anonimlik, kurumun yazılı izni | kanıtlaması zor |
| 2. Gerçek tablo, yerel model | bilgisayarda kalır | en az 32 GB bellek, kurum izni | küçük model arada hata yapar |
| 3. Sahte tablo, buluttaki ajan | hastanede kalır | veri sözlüğü | kodu siz çalıştırırsınız |

Çoğumuz için en kolayı üçüncüsüdür.

## Üçüncü yol, adım adım

1. **Veri sözlüğünü yazın.** Her sütun için ad, birim ve kodlar; örneği `veri/SOZLUK.md`. İçinde hasta yoktur.
   Gerçek tabloda bildiğiniz kirleri de yazın: virgülle yazılmış sayı, boş hücre, farklı yazılmış cinsiyet.
2. **Ajana sahte tabloyu ürettirin.**

   ```
   veri/SOZLUK.md'deki sütun adları ve kodlarla 200 satırlık uydurma bir tablo üret:
   veri/sahte.csv. Hiçbir gerçek satır kullanma. Sözlükte yazan kirleri birkaç satıra koy.
   ```

   Sahte tablo sözlükten üretilir. Gerçek satırları karıştırarak ya da biraz değiştirerek üretilmez; o hâlâ hasta verisidir.
3. **Analizi sahte tabloda yazdırın.** Görev 1–4'ün istemleri aynen geçerlidir. Çıktı olarak menü adımı değil,
   çalıştırılabilir bir dosya isteyin: R ya da Python kodu, SPSS için sözdizimi (`.sps`). Çalıştırdığınız şeyin kaydı kalır.
4. **Kodu gerçek tabloda siz çalıştırın.** Gerçek tablo hastanedeki bilgisayarda, ajanın klasörünün dışında durur.
   Orada yalnız SPSS varsa sözdizimini File › New › Syntax ile açar, Run › All ile çalıştırırsınız.
5. **Kod takılırsa** ajana yalnız hata iletisini verin. İletide bir hücrenin değeri geçiyorsa (bir ad, bir tarih,
   bir ölçüm) onu silin.
6. **Sonuç tablosunu vermeden önce bakın.** Ajana dönebilecek tek şey özet tablodur. İçinde beşten az çocuğun
   kaldığı hücre, en küçük ve en büyük değer, tarih ya da serbest metin olmasın. Beş bir yasa sınırı değil, öneridir.
7. **Kullanımı kaydedin.** Hangi araç, hangi sürüm, hangi tarih, hangi iş, neyi denetlediniz. Beyan o kayıttan
   yazılır; örneği `is-karti/beyan-iyi.txt`.

## Öbür iki yol

- **Anonim tablo.** Adı, protokol numarasını ve tarihleri silmek yetmez: nadir bir tanı, kesin yaş ve uç bir ölçüm
  tek çocuğu gösterir. Tablonun anonim olduğuna ve dışarı verilebileceğine siz değil, verinin sahibi olan kurum
  karar verir; kararı yazılı isteyin.
- **Yerel model.** Model kendi bilgisayarınızda çalışır; satır hiçbir şirkete gitmez. Adı `:cloud` ile biten model
  yerel değildir. Verinin o bilgisayarda durmasına yine kurum izin verir. Küçük model daha çok hata yapar: sayıyı
  hazır fonksiyondan aldırın, önemli sonucu ikinci kez çalıştırın.

## Olgu sunumu

Olgu sunumunda metnin kendisi hastayı tanıtabilir: tanı, yaş, tarih ve merkez bir araya gelince çocuk bulunur.
Buluttaki modele yalnız tanıtıcı ayrıntısı çıkarılmış metni verin.

## Hakemlik

Hakemlik için size gelen makaleyi modele yüklemeyin; emin değilseniz editöre sorun.
