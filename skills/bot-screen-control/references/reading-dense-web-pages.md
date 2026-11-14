# Yoğun sayfalardan okuma (kesik metin, çoklu kare, SPA rotaları)

## When to Use

Ekran görüntüsü + tıklama ile **metin çıkarmak** gerektiğinde: liste/geçmiş sayfaları, kart ızgaraları,
detay panelleri; "son izlediklerimi listele" gibi tek sayfadan çok satır okuyan işler. Kısaca: metin
`…` ile kesikse, derin rota 404 veriyorsa ya da art arda çok kare okuman gerekiyorsa bu dosya devreye
girer. Tıklama tarifi SKILL.md'de; burası "okumayı ucuzlatma" tarafı.

## 1. CSS `ellipsis` ile kesilen metin görüntüde YOKTUR

`"S1 • B22 - The ..."` gibi kesik bir etikette eksik kısım DOM'da/CSS'te durur, pikselde durmaz.
Bu yüzden şunların hiçbiri işe yaramaz: `shot --crop` ile yakınlaştırma, `ctrl+-` ile uzaklaştırma,
sütun genişliğini beklemek, hover tooltip'i ummak. Kesik gördüğün an tek çıkış: **hedefi açmak**.

Ekran görüntüsü yakınlaştırması yalnız *küçük ama tam* yazılmış* metinde işe yarar (ince font, uzak
rozetler). Karar kuralı: metin `…` ile bitiyorsa yakınlaştırma değil gezinme gerekir.

## 2. Tam metni detay görünümünden oku, listeyi kaybetme

- Kartı `click X Y --mods ctrl` ile aç → arka planda sekme açılır, liste sekmesi durur.
- Yeni sekmede başlık genelde iki yerde tam yazılıdır: sayfa `h1`'i ve sağ detay panelinin başlığı
  (`<dizi> / S2 • B11 - <bölüm adı>`). Panel varsa `h1`'i aramana gerek yok, panel daha küçük alanda.
- Okuma bittiğinde listeye sekmeye tıklayarak dön; geri tuşuyla gezinmek kaydırma konumunu bozar.
- Liste sayfasında kalıcı bir şey değiştirme: sıralama, filtre ya da "izlendi" işareti kullanıcının
  görünümünü bozar, geri almak ekstra turdur.

## 3. SPA rota tuhaflıkları: derin rota 404 ise query param dene

Tek sayfa uygulamalarında `/kaynak/<slug>/seasons/2` gibi derin rotalar 404 dönerken aynı içerik
`/kaynak/<slug>?season=2` ile açılır; bölüm detayı da `?view=episode&season=2&episode=5` gibi
query ile gelir. Rota 404 verdiğinde adresi uydurmaya devam etme: bir üst rotaya dön, hangi query
parametresini kullandığını gördüğün çalışan adresten kopyala (adres çubuğu bunu zaten gösterir).

Aynı mantıkla, "+8 böl" benzeri bir kutu tüm listeyi açmayabilir; sadece ilk öğeyi açar. Tam listeyi
görmenin güvenilir yolu tek tek detay açmak ya da başlık sayfasının bölüm şeridini yatay kaydırmaktır.

## 4. N kare → 1 vizyon çağrısı (kompozit kırpma)

Her ekran görüntüsü için ayrı vizyon çağrısı yapmak en pahalı yol. Aynı bölgeyi N karede okuyacaksan:

```bash
S=~/.hermes/skills/bot-screen-control/scripts/screen.py
for id in 9 10 11 12 13; do
  python3 $S key "ctrl+l" >/dev/null
  python3 $S type "<adres>&episode=$id" >/dev/null
  python3 $S key "Return" >/dev/null
  sleep 4
  python3 $S shot --out /tmp/ep$id.png >/dev/null
done
python3 ~/.hermes/skills/bot-screen-control/scripts/stack_crops.py \
  --box 940,160,1440,205 --scale 2 --out /tmp/titles.png /tmp/ep9.png /tmp/ep10.png /tmp/ep13.png
```

Sonra `titles.png` tek seferde okunur. Kutu (x1,y1,x2,y2) tüm karelerde aynı yerde olmalı: hedef
öğe sabit konumdaysa (sağ panel başlığı, sekme çubuğu, tablo sütunu) bu yöntem sorunsuzdur.

Kareler arasında en az ~4 s bekle; yavaş yüklenen bir karede başlık henüz yazılmamış olur ve
kompozitte boş satır görürsün (tek başına yeniden çek, tüm seriyi değil).

## 5. Çoklu ctrl+tık sayısını doğrula

Aynı koordinata art arda `--mods ctrl` tıklamak her seferinde yeni sekme açmaz: sayfa kaydıysa ya da
tıklama aynı bağlantıya denk geldiyse sekme çoğalmaz. Tıklama serisinden sonra **sekme çubuğunun
görüntüsünü al ve say**; beklediğinden az sekme varsa eksik öğeleri tek tek aç.

## 6. Yakınlaştırmayı geri al

Okuma için `ctrl+-` / `ctrl+0` kullandıysan iş bitince `key "ctrl+0"` ile %100'e dön; kullanıcının
penceresini küçük fontla bırakmak bir sonraki turda yanlış koordinat üretir.

## 7. Sticky göstergeler `Page_Down`'ı yer

Tarih/kaydırma göstergesi (sticky scrubber) olan sayfalarda `key Page_Down` gerçek kaydırma değil,
göstergeye olay gönderir: tarih atlar, üstte kalıcı bir panel açık kalır ve `Escape`/`Home` bunu
kapatmaz. Kaydırma her zaman `scroll down --amount N --at X,Y` ile yapılır (`--at` imleci içerik
alanına koyar, göstergenin üstüne değil).

## 8. Sayfa içi PDF / doküman görüntüleyici: ekrandan değil dosyadan oku

Sayfaya gömülü doküman görüntüleyiciler (guideline, sözleşme, ders notu, 10+ sayfalık her şey)
genelde %40-50 yakınlaştırmayla açılır; onlarca sayfayı `shot` + vizyon ile okumak yavaş ve hatalıdır.
Doğru yol dokümanı indirip metni yerel olarak okumak:

1. Görüntüleyici araç çubuğundaki indirme/yazdırma simgesine tıkla (genelde en sağdaki ok/yazıcı).
   Chrome'un "Yazdır" penceresi açılır, hedef zaten "PDF olarak kaydet" olur; "Sayfalar: Tümü" kalsın.
   → `Kaydet`.
2. Dosya adı penceresi gelir (klasör `~/Downloads`). Aynı adda eski bir dosya varsa adı değiştir:
   ad alanına tıkla, `key "ctrl+a"`, `type "YeniAd.pdf"`, sonra `Kaydet`. Üzerine yazma — eski kopya
   başka bir dokümandır ve geri getirilemez.
3. `ls -lt ~/Downloads | head -3` ile dosyanın indiğini doğrula, sonra `read_file` ile oku: PDF'te
   metin katmanı varsa `extracted_document: true` döner ve tablolar `|` satırları olarak gelir;
   aradığın cümleyi `search_files` ile bulabilirsin.
4. İndirilen dosya kullanıcının `~/Downloads` klasörüne düşer: raporunda adını söyle, kendi başına
   silme.

Neden: bu yolda tüm kurallar tek seferde okunur ve cevaplar tahmin yerine metinden alıntılanır.
Ekrandan okumaya yalnız görüntüleyicide metin katmanı yoksa (taranmış belge) dön — o zaman da
sayfa sayfa `shot --crop` + kompozit yöntemi (bkz. bölüm 4) kullanılır.
