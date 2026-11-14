---
name: bot-screen-control
description: "Drive the bot screen GUI: real mouse/keyboard on X11."
version: 1.1.0
author: Hermes Agent + Salih
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [computer-use, desktop, x11, xdotool, screenshots, bot-screen, gui-automation]
---

# Bot Screen Control (X11, görsel + koordinat)

Bot ekranını (headless Xfce, VNC üstünde Xvnc) **gerçek fare/klavye olaylarıyla** sürmek için.
AT-SPI, OCR, MCP yok — ekran görüntüsüne bak, koordinata tıkla, sonucu görüntüyle doğrula.

`scripts/screen.py` tek dosya; komut başına tek satır JSON basar (`--human` ile okunur metin).

## Ne zaman kullan

- `computer_use` ekranı yakalayamıyorsa (capture boş ya da X11 görüntü hatasıyla dönerse) bu skill'e geç:
sürücü tarafı düzeldiğinde yine önce onu dene.
- `browser_exec` "A human has taken over this desktop" diyorsa (kullanıcı ekranı tutuyor) ama yine de tıklama gerekiyorsa — `lease` yalnız `browser_exec`/ekran yakalamayı kilitler, `xdotool` çalışmaya devam eder.
- Sayfa içeriği DOM'dan okunamıyorsa (SPA, login duvarı) ya da masaüstü uygulamaları sürülecekse.

DOM erişimi varken `browser_exec` daha hızlı ve sağlamdır; onu tercih et.

Derinlik gerektiğinde:

- `references/x11-desktop-tooling.md` — oturum env hijyeni, isteğe bağlı AT-SPI yolu, wmctrl'süz
  pencere işleri, ekran kaydı + kare farkı, **hangi Chrome profili/oturumu** teşhisi, üçüncü taraf
  yığını sudo'suz deneme.
- `references/reading-dense-web-pages.md` — kesik (ellipsis) metni tam okuma, sayfa içi PDF/dokümanı
  indirip yerel metne çevirme, SPA rota tuhaflıkları, N kareyi tek vizyon çağrısında okuma;
  `scripts/stack_crops.py` bu dosyadaki kompozit yöntemi uygular.

## Çalışma tarzı (bu kullanıcı)

- **Ekranı bir kullanıcı gibi kullan.** Uygulamayı sol üst menüden aç, yer imine tıkla, sekmeyi tıkla.
  Profil kopyalama, ayrı `--user-data-dir`, DOM/API kestirmesi gibi "hile"leri ancak kullanıcı
  isterse yap; istemediğinde "misafir/boş oturum" görüntüsü verir ve iş boşa gider.
  "Normal şekilde aç" / "menüden tıklayarak aç" dediğinde birebir o yolu izle.
- **Tıklamadan önce imleci kaydır.** Işınlanma yok: 20-25 ara nokta, ~0,5 s, smoothstep,
  sonra ~250 ms hover, sonra tıkla. `click` bunu zaten varsayılan yapar; elle `mousemove X Y`
  + anında `click` yazma.
- **"Sadece fare + klavye + ekran görüntüsü"** dendiğinde başka araç kullanma: DOM/CDP, AT-SPI,
  MCP yok. Kullanıcı "ekranda yapacaklarımı izle" derse saniyede 1 kare kaydet, sonra incele
  (yöntem `references/x11-desktop-tooling.md` içinde).
- **MCP'ye sarılmasını istemedi.** Aracı CLI/script olarak tut; başka ajanlarla paylaşım gerekirse
  aynı script'i ince bir sarmalayıcıyla açmak yeterli.
- **Üçüncü taraf yığın denemesi geçicidir.** "Deneyelim, sonucuna göre karar veririz" dediğinde
  scratch'e kur, gerçek bir görevle dene, karar verilince **tamamen** kaldır: kurulum dizini,
  sistem ikilisi yerine çıkardığın kopyalar ve varsa profil kopyaları. Denemeyi kalıcı kurulum
  gibi bırakma; kullanıcı "bunu kaldıralım" dediğinde geride iz kalmasın.
  Tarifi: `references/x11-desktop-tooling.md` §7–8.
- **Profil kopyaları kullanıcının cookie'lerini taşır.** Bir tarayıcı profilini kopyalayıp
  denediysen iş bitince sil (yüzlerce MB tutar); silmeden önce kullanıcıya sor.
- **Akışın kendi onayı geldiğinde dur.** Son adım yeşil "bitti/thank you" ekranı, "This is correct"
  bannerı ya da dashboard'a yönlenme ile kapandıysa, başarıyı yeniden doğrulamak için sekme sekme
  gezinmeye devam etme — kullanıcı ekranı izliyor ve bu gezinti "ne yapıyor bu" gibi görünüyor.
  Son durumun tek bir `shot`'ını al, özeti ver, şüphe varsa sözlü olarak belirt.

## Hızlı başlangıç

```bash
S=~/.hermes/skills/bot-screen-control/scripts/screen.py

python3 $S check                    # HAZIR/EKSİK: eksik araç + ekran erişimi + klavye düzeni
python3 $S info                     # ekran, klavye düzeni, lease sahibi, pencereler
python3 $S shot --out /tmp/s.png    # ekran görüntüsü (ffmpeg x11grab)
python3 $S click 390 415            # yumuşak kaydır + 250 ms bekle + tıkla
python3 $S click 88 128 --mods ctrl # ctrl+tık = yeni sekmede aç
python3 $S type "Merhaba dünya"     # ASCII dışı varsa panoyla yapıştırır
python3 $S key "ctrl+l"             # kısayol
python3 $S wait-change --timeout 20 # "sayfa yüklendi mi" beklemesi
python3 $S scroll down --amount 5 --at 800,600   # tekerlek; Page_Down yerine bunu kullan
python3 $S drag 300 400 900 400 --steps 30       # sürükle-bırak (smoothstep)
python3 $S diff /tmp/a.png /tmp/b.png            # iki kare arası fark oranı
python3 $S win list                 # pencere listesi (wmctrl gerekmez)
python3 $S log --tail 10            # eylem günlüğü
```

`--help` yok (`bilinmeyen komut: --help`). Komut listesi: `check info shot move click drag scroll type
key win wait-change diff log`; ayrıntı için script'in altındaki `elif cmd ==` bloklarına bak.

## Taşınabilirlik (başka makineler)

Script makineye bağımlı değil; çözünürlük sırası:

1. **DISPLAY / XAUTHORITY**: ortamda varsa o → `$HERMES_HOME/bot-desktop/env` → `~/.hermes/bot-desktop/env` → `:0` + `~/.Xauthority`.
2. **ffmpeg**: `SCREEN_FFMPEG` → `PATH` → `$HERMES_HOME/tools/ffmpeg*/bin/ffmpeg` → `~/.hermes/tools/…`.
3. **Yazma yolları**: `$HERMES_HOME/cache/screen-actions.jsonl` ve `…/screen-shots/` (profil başına ayrı).
4. **İsteğe bağlılar**: `xclip` yoksa pano yöntemi devre dışı → `type` gerçek tuş basımına düşer;
   `setxkbmap` yoksa düzen değişemez (ASCII metin yine yazılır). Zorunlu ikili: `ffmpeg` + `xdotool`.
5. **Wayland**: XWayland pencereleri çalışır; saf Wayland pencereleri için `wayland-desktop-control`.

Yeni ortamda ilk komut `check` olmalı; ekrana özel ölçümler `references/this-screen.md` içinde ve
çözünürlük/tema değişince yeniden ölçülür.

## Ortam gerçekleri (bu makine)

- Ekran `:20`, 1440x900, X11 (Xvnc + Xfce). `XAUTHORITY=~/.hermes/bot-desktop/Xauthority`.
  Script bunları `~/.hermes/bot-desktop/env` dosyasından kendisi okur; elle `export` gerekmez.
- Ekran koordinatı == görüntü koordinatı. Ölçekleme yok (`scale=1.0`), çarpan hesaplamayın.
- `lease.json` → `holder: human` iken `browser_exec` reddeder; `xdotool` etkilenmez.
- Gerekli: `ffmpeg` (Hermes tools altında), `xdotool`. Faydalı: `xclip` (pano yöntemi), PIL (fark hesabı).
  `wmctrl`, `tesseract`, `numpy`, ImageMagick `import` varsa da kullanılabilir ama **gerekmez**:
  pencere işleri `xdotool`, fark hesabı `ImageChops`, ekran görüntüsü `ffmpeg` ile yapılır.
  Yeni bir araç kurmadan önce bu üçünün yetmediğini göster.
- Bot ekranında **iki ayrı Chrome profili** var:
  - `~/.hermes/bot-desktop/xdg/google-chrome` → menüden/terminalden açılan normal Chrome. Kullanıcının oturumları (Trakt, Google) burada. **Varsayılan olarak bunu kullan.**
  - `~/.hermes/bot-desktop/browser-profile` → ajanın `browser_exec` profili; dock'taki Browser ikonu bunu açar. İçinde genelde giriş yoktur.

## Tarifler

**Menüden uygulama açma** (doğal yol). Koordinatlar bu ekranda ölçüldü, ayrıntı `references/this-screen.md`:
```bash
python3 $S click 15 15     # sol üst menü
python3 $S click 100 124   # "İnternet Tarayıcısı" (menünün en üstü) → Chrome
python3 $S wait-change --timeout 20
```
Menü sıralaması temaya göre değişir; `shot` ile doğrulamadan koordinatı ezberden kullanma.

**Yeni sekmede bağlantı açma:** yer imi çubuğu görünür değilse `key "ctrl+shift+b"`, sonra
`click <x> 128 --mods ctrl`.

**Türkçe metin yazma:** `type` varsayılan olarak ASCII dışı karakter görürse panoyla yapıştırır
(`--method auto`). Gerçek tuş basımı isteyen `--method keys` kullanır: `tr` düzenine geçer,
yazar, düzeni geri alır. Her iki yol da bugün doğrulandı.

**Form / anket / quiz sayfaları:** bu sayfalar tek ekranda bitmez; her sorunun kendi
`Submit Answer` düğmesi olabilir ve sayfa altındaki `Continue` hepsi gönderilene kadar pasif kalır.
Sıra: radyo/seçeneğe tıkla → ~1 s → `Submit Answer` → `shot` ile geri bildirimi oku (yeşil
"This is correct" / kırmızı uyarı) → sonraki soruya geç. `Attempts remaining: N` sayacı durumu söyler:
0 = bu soru gönderilmiş, >0 = hâlâ açık. `Continue` pasif görünüyorsa sayfada gönderilmemiş soru var:
`scroll down` ile tüm sayfayı tara, eksikleri tamamla, sonra `Continue`.
Seçmek ile göndermek iki ayrı adımdır; geri bildirim bannerını görmeden "cevapladım" deme.

**Giriş istiyor / "misafir" görünüyor:** önce hangi profilin açık olduğunu kanıtla, tahmin etme
(`references/x11-desktop-tooling.md` §7): `/proc/<pid>/cmdline`'da `--user-data-dir` yoksa pencere
XDG profilidir; cookie DB'sinde hedef alan adı yoksa o jar'da hiç giriş yapılmamıştır. Doğru pencereyi
menüden aç, orada bir kez giriş yap — kalıcı profil budur.

## Tuzaklar (hepsi bu makinede bizzat yaşandı)

1. **`pkill -f <desen>` kendini öldürür.** Desen, komutu çalıştıran `bash -c` satırında da geçer.
   Süreç öldürmek için önce `pgrep -af` ile PID bul, sonra `kill <pid>`.
2. **`us` düzeniyle büyük Türkçe harfler bozulur:** `İstanbul` → `Istanbul`, `Çiçekler` → `çiçekler`.
   Küçük harfler (ü ş ğ ı ö ç) sorunsuz. Çözüm: pano ile yapıştırma (varsayılan) ya da `tr` düzeni.
3. **Düzen değişiminden hemen sonra ilk karakter kaybolabilir.** `setxkbmap tr` sonrası en az
   ~0.6 s bekle (script yapıyor); yetmezse pano yöntemine düş.
4. **`wait-change` olmadan `sleep` ile beklemek** yavaş ve kırılgan: 8 s bekleyip boş sayfa
   görüntülemek yerine değişim eşiğini bekle.
5. **Chrome'daki "Profil hatası" / "düzgün kapatılmadı" balonu** hesap kaybı değil: ekran
   kapanırken Chrome SIGTERM/SIGKILL alıyor. Kalıcı cookie'ler durur.
6. **Kesik kart metnini yakınlaştırmak kurtarmaz.** CSS `text-overflow: ellipsis` ile kesilen kısım
   pikselde yoktur: `shot --crop`, `ctrl+-`, hover tooltip hepsi boşa gider. Tam metin için hedefi
   `--mods ctrl` ile tıkla, açılan sekmedeki detay başlığından/panelinden oku (yöntem:
   `references/reading-dense-web-pages.md`). DOM erişimi varsa DOM'u tercih et.
7. **`browser_exec` ile aynı profili paylaşma:** o araç kendi profilini (`browser-profile`) açar;
   kullanıcının giriş yaptığı pencere `xdg` profilidir. Karıştırırsan "misafir" görünüm alırsın.
8. **`xdotool mousemove --sync` asılı kalabilir:** imleç hedefe varmazsa süresiz bekler ve ajan
   turunu kilitler. Düz `mousemove` kullan ve her `xdotool` çağrısını bir timeout ile sar
   (script 8 s kullanıyor). Uzun bir tur "takıldı" gibi görünüyorsa önce asılı `xdotool`
   çağrısını ara.
9. **İlk denemede "misafir" görünümü alırsan profil değil, açılış yolu yanlıştır.** Aynı sekmeyi
   menüden açılan Chrome'da tekrar dene; profili kopyalamak/taşımak sorunu çözmez.
10. **`key Page_Down` / `Page_Up` kaydırma değildir.** Sayfada sticky bir tarih/kaydırma göstergesi
    varsa bu tuşlar göstergeye gider: tarih atlar, üstte kalıcı bir panel açık kalır ve `Escape`/`Home`
    onu kapatmaz. Kaydırma her zaman `scroll down --amount N --at X,Y` ile yapılır.
11. **Aynı koordinata art arda `--mods ctrl` tıklamak her zaman yeni sekme açmaz** (sayfa kaymış ya da
    aynı bağlantıya denk gelmiş olabilir). Tıklama serisinden sonra sekme çubuğunu `shot` ile say;
    eksik kalanı tek tek aç.
12. **`--mods ctrl` yeni sekmeyi ARKA PLANDA açar ve sekme çubuğu her yeni sekmeyle sağa kayar.**
    Yeni sekme aktif olanın hemen sağında, en sonda durur; bir önceki turun sekme x koordinatı artık
    başka bir sekmeye denk gelir. Sekmeye geçmeden önce `shot` alıp konumu doğrula — yoksa eski
    koordinat yanlış sekmeyi (çoğu zaman az önce bıraktığın dokümanı) açar ve tur boşa gider.
13. **Bot ekranı boşta kendini kapatır** (`idle_stop_minutes`, varsayılan 30 dk). Kapanınca
    `bot-desktop/env` silinir, `xrandr` "Can't open display" der ve script `:0`a düşer. `check`
    bunu `display_reachable:false` + `bot_desktop_env:false` + `hint` ile söyler. Ekranı geri açmak:
    masaüstü uygulamasındaki ekran paneli, ya da
    `cd ~/.hermes/hermes-agent && python3 -c "from tools.bot_desktop import runtime; print(runtime.start(wait_seconds=25))"`.

## Paylaşım / dağıtım

Skill bir klasör — paylaşmak için ek bir biçim gerekmiyor:

```bash
# 1) başka makineye kopyala (hedefte ~/.hermes/skills/ içine taşı)
scp -r ~/.hermes/skills/bot-screen-control other:/tmp/

# 2) GitHub reposu + tap (repo kökünde skills/<ad>/SKILL.md düzeni)
hermes skills tap add <owner>/<repo>
hermes skills install <owner>/<repo>/bot-screen-control

# 3) tek skill'i tapsiz kurmak (herkese açık repo yeter)
hermes skills install <owner>/<repo>/bot-screen-control

# 4) kayıt defterine yayınla
hermes skills publish ~/.hermes/skills/bot-screen-control --to github --repo <owner>/<repo>
hermes skills publish ~/.hermes/skills/bot-screen-control --to clawhub
```

Kurulumdan sonra hedef makinede ilk iş `check` çalıştırmak: eksik `ffmpeg`/`xdotool` ya da
erişilemeyen ekran orada ortaya çıkar. `references/this-screen.md` koordinatları o makineye
taşınmaz — yeniden ölçülür.

## Doğrulama ilkesi

Her durum değiştiren eylemden sonra `shot` al ve görüntüyü oku; "tıkladım" != "oldu".
JSON çıktısındaki `ok: true` yalnız "olay gönderildi" demektir, sonucu doğrulamaz.
