# hermes-skills

Hermes Agent için kişisel skill koleksiyonu. Her skill `skills/<ad>/SKILL.md` düzeninde durur;
bu repo hem **tap** (kaynak) hem de tek tek kurulum için kullanılabilir.

## İçindekiler

| Skill | Ne yapar |
|---|---|
| [`bot-screen-control`](skills/bot-screen-control/SKILL.md) | X11 masaüstünü gerçek fare/klavye olaylarıyla sürer: ekran görüntüsü, yumuşak imleç kaydırma, tıklama, sürükleme, kaydırma, Unicode metin yazma, pencere işleri, "değişti mi" beklemesi. AT-SPI/OCR/MCP gerektirmez. |

## Kurulum

**Tap olarak ekle (repodaki tüm skill'ler görünür):**

```bash
hermes skills tap add Salih800/hermes-skills
hermes skills search bot-screen      # artık listede
hermes skills install Salih800/hermes-skills/bot-screen-control
```

**Tap eklemeden tek skill:**

```bash
hermes skills install Salih800/hermes-skills/bot-screen-control
```

**Elle:** `skills/bot-screen-control/` klasörünü `~/.hermes/skills/` içine kopyala.

Kurduktan sonra ilk komut **öz-denetim** olmalı:

```bash
python3 ~/.hermes/skills/bot-screen-control/scripts/screen.py check
```

## Gereksinimler

- Linux, **X11** oturumu (XWayland pencereleri de çalışır; saf Wayland pencereleri çalışmaz)
- `ffmpeg` ve `xdotool` (zorunlu), `xclip` (pano ile yazma için önerilir), `setxkbmap` (klavye düzeni değişimi için)
- Python 3.10+ , PIL (kare farkı için)

## bu repoyu kendi kullanımın için

`skills/` altına yeni klasör ekle, `SKILL.md` yaz, commit et. Tap kullanan makineler
`hermes skills check` / `hermes skills update` ile güncellemeyi alır.

## Lisans

MIT — bkz. [LICENSE](LICENSE)
