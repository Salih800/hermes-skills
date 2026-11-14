# Örnek ölçümler (1440x900, Xfce) — kendi makinende yeniden ölç

> Bu dosya **bir makinede alınmış örnektir**, taşınabilir bir harita değil. Tema/panel/çözünürlük
> değişince geçersiz olur (yazarken bile menü sırası değişti). `check` + `shot` ile yeniden ölç.

Koordinatlar **ekrana** aittir, ekran görüntüsüne değil (ölçek 1:1). Tema, panel düzeni veya
çözünürlük değişince yeniden ölçülür: `screen.py shot --out /tmp/s.png` → görüntüyü oku →
hedefin merkezini yaz.

## Panel / menü

| Hedef | Koordinat | Not |
|---|---|---|
| Uygulama menüsü (sol üst ikon) | `15 15` | menü açılır, kategoriler listelenir |
| "İnternet Tarayıcısı" (menü en üstü) | `100 124` | doğrudan Chrome açar — **en kısa yol** |
| Menü: "İnternet" kategorisi | `63 275` | alt menü sağa açılır (eski temada `119`) |
| Menü: "Donatılar" | `63 197` | eski temada `Yardımcı Programlar` |

> Not: menü sıralaması temaya göre değişiyor; `15 15` + `shot` ile her zaman doğrula.

## Chrome

| Hedef | Koordinat | Not |
|---|---|---|
| Yer imi çubuğu satırı | `y=128` | `ctrl+shift+b` ile açılır |
| "Çeviri" yer imi | `88 128` | ctrl+tık = yeni sekmede aç |
| Adres çubuğu | `ctrl+l` | koordinat yerine kısayol tercih et |
| Sekme şeridi | `y≈34` | sekmeler arası `ctrl+Tab` daha güvenli |

## Google Çeviri (translate.google.com.tr)

| Hedef | Koordinat | Not |
|---|---|---|
| Kaynak metin kutusu | `390 415` | tıkladıktan sonra `type` |
| Kaynak dil çipleri | `y=337` | "Dili algıla" ~80, "Türkçe" ~155 |
| Hedef dil çipleri | `y=337` | "İngilizce" ~744, "Türkçe" ~815 |

## Trakt (app.trakt.tv)

| Hedef | Koordinat | Not |
|---|---|---|
| Kenar çubuğu "Geçmiş" | `100 735` | `app.trakt.tv/history` |
| Tarih şeridi | üstte, `y≈200` | `Down`/`Up` tuşları odağı buraya kaydırır, URL'ye `?date=` ekler |
