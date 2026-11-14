# X11 masaüstü araçları — derinlik notları

Bu dosya `bot-screen-control` için ara sıra gereken ayrıntıları taşır. Varsayılan yol her zaman
görsel + koordinattır; buradakiler koordinatlar kırılganlaştığında veya bir GUI aracını bu ekrana
yönlendirmek gerektiğinde devreye girer.

## 1. Oturum env hijyeni (Hermes'ten GUI aracı başlatırken)

Gateway kullanıcının GNOME/Wayland oturumunda çalışır; çocuk süreçlere `XDG_SESSION_TYPE=wayland`
ve `WAYLAND_DISPLAY=wayland-0` sızar. Bot ekranı ise X11 (`:20`, Xvnc). Bu karışım yüzünden bir araç
"Wayland oturumu + DISPLAY=:20" der, x11 backend'lerini kapatır ve "klavye girdisi yok" raporlar.

Aracı başlatmadan önce:

```bash
set -a; . ~/.hermes/bot-desktop/env; set +a
unset WAYLAND_DISPLAY
export XDG_SESSION_TYPE=x11 XDG_CURRENT_DESKTOP=XFCE GDK_BACKEND=x11 QT_QPA_PLATFORM=xcb
```

Belirti: araç `xdg_session_type=wayland` görürken `display=:20` görüyorsa env düzeltilmemiştir.
`DBUS_SESSION_BUS_ADDRESS` bot env'inden gelmeli; kullanıcının oturum veriyoluna bağlanmak AT-SPI'yi
başka bir masaüstünün ağacına götürür.

## 2. İsteğe bağlı: sayfa içeriğini semantik okuma

Chrome, sayfa erişilebilirlik ağacını yalnız `--force-renderer-accessibility` ile açar. Bayraksız
AT-SPI ağacı sadece pencere kromunu verir (~3 düğüm: uygulama + çerçeve). Bayrakla aynı sayfa
`combo box "Kaynak metin"`, `page tab "Türkçe"`, `button "Çeviri"` gibi adlandırılmış düğümlere
ayrılır → koordinat yerine **ada göre tıklama** mümkün olur.

- Bayrak açılışa özeldir, kalıcı ayar değildir; normal menü açılışında etkisi yoktur.
- Her gezinmeden sonra ağaç yeniden okunmalı: snapshot indeksleri geçersizleşir.
- Ağaç boyutu büyük (yüzlerce düğüm) ve çoğu zaman sayfalanır; okuma sırasında "kaç düğüm geldi,
  kaç tanesi ham" diye say, eksik sayfayı "bulamadım" sanma.

Karar: koordinat + `wait-change` yeterince sağlamsa bu yola hiç girme; kırılırsa yukarıdaki bayrakla
geçici olarak semantik okumaya düş.

## 3. wmctrl olmadan pencere işleri

```bash
xdotool search --onlyvisible --name ""          # id listesi (boş desen = hepsi)
xdotool getwindowname <id>
xdotool getwindowgeometry --shell <id>           # X/Y/WIDTH/HEIGHT
xdotool windowactivate <id>                      # odak
xdotool windowmove <id> X Y
xdotool windowsize <id> W H
```

Bu dörtlü listeleme/odak/taşıma/boyutlandırma için yeterlidir. wmctrl'in eklediği tek şey çalışma
alanı, sticky/pin ve EWMH meta verisi — bu iş için gerekmedi.

## 4. ImageMagick'siz ekran görüntüsü

```bash
ffmpeg -loglevel error -f x11grab -video_size 1440x900 -i :20 -frames:v 1 -y out.png
# kırpma / ölçekleme
-vf "crop=635:115:75:330"        # w:h:x:y
-vf "scale=iw*2:ih*2:flags=lanczos"
```

`XAUTHORITY` set edilmiş olmalı. `import`, `scrot`, `gnome-screenshot`, `xwd` gerekmez.
Kırpma + 2x büyütme, küçük UI yazısını okunur kılar ve tek görüntüde yakınlaştırmadan daha az
bağlam harcar.

## 5. Kullanıcının ekranda yaptıklarını kaydetme

```bash
ffmpeg -loglevel error -f x11grab -framerate 1 -video_size 1440x900 -i :20 -t 900 \
  -y ~/.hermes/cache/scratch/watch/f%04d.png
```

Ardından ilginç anları bulmak için kareleri küçültüp karşılaştır:

```bash
ffmpeg -i f%04d.png -vf "scale=32:20,format=gray" -f rawvideo -y sigs.raw
```

`32x20` gri imzaları Python'da bayt bayt karşılaştır, ortalama farkın birkaç katını eşik al.
**Dosya hash'i ile kare tekilleştirme yanıltır**: saat, imleç ve animasyon her kareyi değiştirir,
her kare "farklı" çıkar. Seçilen 6-8 kareyi tek görüntüde birleştirip (`xstack`) tek bakışta oku.

## 6. Fare/klavye incelikleri

- **ctrl+tık (yeni sekmede aç):** `keydown ctrl` → `click 1` → `keyup ctrl`. Sıra önemli; `keyup`
  tıklamadan önce giderse normal tıklama olur.
- **Tekerlek:** X11'de buton 4 = yukarı, 5 = aşağı; her `click 4/5` bir tık.
- **Sürükleme:** hedefe kaydır → `mousedown 1` → ara noktalarla ilerle → `mouseup 1`;
  tek adımda zıplamak seçim bırakmaz.
- **Odak:** tıklamadan önce pencereyi `windowactivate` ile öne almak yerine hedefe tıklamak
  çoğu zaman yeter; yine de kısayol göndereceksen (`ctrl+l` gibi) önce pencereyi etkinleştir.
- **Kaydırma sonrası durum:** `Down`/`PageDown` tuşları sayfayı kaydırırken odaklanmış bir tarih
  şeridi veya liste seçimini de değiştirebilir; kaydırma için tercihen tekerlek kullan ve
  URL/başlık değişimini doğrula.

## 7. Hangi Chrome profili / oturum açık? (kanıtla, tahmin etme)

"Giriş yapmıştım, yine istiyor" şikâyetinin iki nedeni var: yanlış profil açık, ya da o profilde
hiç giriş yapılmamış. İkisi de ölçülebilir; tahminle profil kopyalama yoluna girme.

```bash
# 1) pencerenin kullandığı user-data-dir (argüman yoksa XDG varsayılanı)
for p in $(pgrep -f 'opt/google/chrome/chrome'); do
  c=$(tr '\0' ' ' </proc/$p/cmdline)
  case "$c" in *--type=*) continue;; esac
  echo "$p :: $(echo "$c" | cut -c1-140)"
done

# 2) o profilin cookie'lerinde hedef alan adı var mı (kopyala, canlı DB'yi açma)
cp ~/.hermes/bot-desktop/xdg/google-chrome/Default/Cookies /tmp/ck.db
python3 -c "import sqlite3;c=sqlite3.connect('/tmp/ck.db');print(c.execute('select host_key,name from cookies where host_key like \"%trakt%\"').fetchall())"

# 3) profil hiç kullanılmış mı: History'deki URL sayısı + doğum zamanı
cp ~/.hermes/bot-desktop/xdg/google-chrome/Default/History /tmp/h.db
python3 -c "import sqlite3;print(sqlite3.connect('/tmp/h.db').execute('select count(*) from urls').fetchone())"
stat -c '%w' ~/.hermes/bot-desktop/xdg/google-chrome
```

Yorum: oturum cookie'si (`__Secure-…session_token`, `trakt-oidc-auth` gibi) yoksa o profilde giriş
yoktur; `History` 0 URL ise o pencere hiç gezinmemiştir (yani "eskiden giriş yapmıştım" başka bir
profile aittir). `bot-desktop/browser-profile` (ajan/dock) ile `xdg/google-chrome` (menü) ayrı
jar'lardır — kullanıcı hangisinde giriş yaptıysa kalıcı olan odur.

## 8. Üçüncü taraf bir GUI yığınını sudo'suz, kalıcı iz bırakmadan denemek

Kullanıcı "şu hazır skill'i/aracı deneyelim" dediğinde sistemi kirletmeden dene:

```bash
mkdir -p ~/.hermes/cache/scratch/trial && cd ~/.hermes/cache/scratch/trial
npm install --prefix . --no-audit --no-fund <paket>          # postinstall bloklu olabilir
node node_modules/<paket>/npm/install.js                     # ikiliyi elle indir

# sistem ikilisi eksikse (örn. wmctrl): sudo yerine .deb çıkar
apt-get download wmctrl && dpkg-deb -x wmctrl*.deb ./root
export PATH=$PWD/root/usr/bin:$PATH
```

- MCP'li araçlarda `npm/bin/*.js` bir shim'dir; gerçek ikiliyi (örn. `*-linux-x64`) doğrudan çağır,
  yoksa stdio el sıkışması zaman aşımına düşer.
- Araç "Wayland" sanıyorsa §1'deki env düzeltmesini uygula; yoksa pencere listesi ve klavye
  girdisini "yok" diye raporlar (suçlu araç değil, sızan env).
- Deneme bitince dizini, çıkardığın ikiliyi ve varsa profil kopyalarını sil; kararı kullanıcı verir,
  sen yalnızca ölçümü ve temizliği yaparsın.
