# QBTranslator

Windows için masaüstü çeviri uygulaması. Herhangi bir programda seçtiğiniz metni global bir kısayolla çevirir, imlecin yanında gösterir; ayrıca **ekrandan OCR ile bölge seçerek** çeviri yapabilir.

> Bu proje, Mouse Tooltip Translator tarayıcı eklentisinin masaüstü karşılığıdır. Eklentinin kendisi `../tarayıcı/` klasöründedir.

---

## Özellikler

- **Global kısayol** (varsayılan `Ctrl+Alt+T`): seçili metni kopyalar, çevirir ve imleç yanında gösterir
- **OCR (ekrandan çeviri)**: ayrı bir kısayolla (varsayılan `Ctrl+Alt+O`) ekran bölgesi seçin; seçim dışı kararır, bölge okunur ve aynı balonda çevrilir
- **Aranabilir dil seçici**: balondaki "Hedef dil" düğmesi; Türkçe/İngilizce adlarla ve Türkçe karakter yazmadan arar
- **⇄ Takas**: çeviri çıktısını kaynak yapıp önceki kaynak dile geri çevirir (ileri-geri kontrol)
- **Kısayol yakalama**: Ayarlar'da "Yakala…" ile klavyeden istediğiniz kombinasyonu atayın (elle de yazılabilir)
- **Windows açılışında otomatik başlatma**: oturum açılışında **sistem tepsisinde** başlar, kısayolları dinler
- **Sistem tepsisi + arka plan**: X düğmesi uygulamayı kapatmaz; tepsiye küçültür. Tamamen kapatmak için tepsi menüsünden **Çıkış** veya Ayarlar'daki büyük kırmızı düğme kullanılır
- **Tek örnek**: ikinci kez açılırsa mevcut pencere öne getirilir; `--quit` ile arka plandaki uygulama düzgünce kapatılabilir
- **iOS tarzı anahtarlar**: Ayarlar'daki seçenekler gradyanlı açma/kapama anahtarlarıyla yönetilir
- **Pano izleme** (isteğe bağlı): kopyalanan metni otomatik çevirir
- **Geçmiş + kayıtlı kelimeler**: arama, kart modu, CSV dışa aktarma
- **Sesli okuma (TTS)**: Windows SAPI; uygulama kapanınca konuşma kesin olarak durur
- **Çoklu motor**: Google Translate (varsayılan), MyMemory, LibreTranslate, Lingva, LLM (Ollama / LM Studio / OpenAI)
- **Yalnızca standart kütüphane**: geliştirme sürümünde `pip install` gerekmez

---

## Gereksinimler

- **Windows 10 / 11**
- **Python 3.9+** (yalnızca kaynak koddan çalıştırırken; `tkinter` ile birlikte gelir)
- İnternet (çeviri için)
- **OCR için**: Windows OCR dili/dil paketi (Ayarlar → Zaman ve Dil → Dil). Windows OCR motoru yoksa, kuruluysa **Tesseract CLI** yedeği kullanılır.
- TTS için PowerShell (Windows ile gelir)

---

## Çalıştırma

| Yöntem | Açıklama |
|---|---|
| `baslat.bat` | Konsol açmadan başlatır (`pythonw`) |
| `baslat_konsol.bat` | Hataları görmek için konsollu başlatır |
| `python main.py` | Terminalden çalıştırma |
| `python main.py --background` | Doğrudan sistem tepsisinde/arka planda başlat |
| `python main.py --quit` | Arka planda çalışan QBTranslator'u düzgünce kapat |

İlk açılışta `data/` dizini oluşturulur.

---

## Kullanım

### 1. Seçili metni çevirme

1. Herhangi bir uygulamada metni seçin
2. **Ctrl+Alt+T**
3. Çeviri, imlecin yanındaki balonda görünür

Balondaki düğmeler: **Kopyala • Oku • Kelime Kaydet • Kapat**. Balon sürüklenebilir; `Esc`, sağ tık, X veya otomatik süre ile kapanır.

### Arka plan / sistem tepsisi

- **X düğmesi uygulamayı kapatmaz.** Pencere sistem tepsisine küçültülür; kısayollar dinlenmeye devam eder.
- Tepsideki **QBTranslator** simgesine **çift tıklayınca** ana pencere açılır.
- Simgeye **sağ tık → Çıkış** uygulamayı tamamen kapatır.
- Dilerseniz Ayarlar'daki büyük **UYGULAMADAN TAMAMEN ÇIKIŞ** düğmesini de kullanabilirsiniz.
- Otomatik başlatmada uygulama doğrudan **sistem tepsisinde** başlar; ana pencere açılmaz.
- Komut satırından kapatmak için: `QBTranslator.exe --quit`

### 2. OCR ile ekrandan çeviri

1. Ayarlar → **OCR modunu etkinleştir** işaretli olsun
2. **Ctrl+Alt+O** (veya atadığınız kısayol)
3. Fareyle çevrilecek alanı sürükleyerek seçin — seçim dışı kararır, seçim berrak kalır
4. Bölge Windows OCR ile okunur ve **aynı çeviri balonunda** gösterilir

`Esc` veya sağ tık seçimi iptal eder. OCR sırasında balon açılmaz; böylece ekran görüntüsü kirlenmez.

### 3. Balonda dil değiştirme / takas

- **Hedef dil** düğmesi → aranabilir dil seçici (Türkçe/İngilizce adlar, `ing`, `english`, `turkce`…)
- **⇄** → çeviri çıktısı yeni kaynak olur, hedef önceki kaynak dile döner; tekrar basınca yön geri döner
- Yapılan seçim ana uygulama, Ayarlar ve sonraki çevirilerle senkronlanır

### 4. Pano izleme

Ayarlar → **Panoyu izle**. Kopyaladığınız metin (URL'ler hariç) otomatik çevrilir. Varsayılan kapalıdır.

---

## Ayarlar

### Kısayollar

- **Global kısayol** (seçili metin) ve **OCR kısayolu** ayrı ayrı ayarlanır
- Elle yazın: `ctrl+alt+t`, `ctrl+shift+f2`, `alt+space`
- veya **Yakala…** düğmesine basın, klavyeden kombinasyona basın, **Kaydet**
- En az bir değiştirici (Ctrl/Alt/Shift/Win) + harf/rakam/F1–F12/Space/Tab/Enter/Yön tuşları
- Yakalama sırasında global kısayollar geçici olarak durdurulur
- Win tuşu içeren kombinasyonları elle yazın (Windows tuşu Tk tarafından yakalanmayabilir)

### Otomatik başlatma / arka plan

- **Windows açılışında otomatik başlat** varsayılan olarak açıktır
- Ayarlar kaydedildiğinde `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` altına `QBTranslator` girdisi yazılır
- Oturum açılışında uygulama **simge durumunda** başlar, kısayolları dinlemeye devam eder
- Ana pencereyi veya Görev Yöneticisi'ni kullanarak kapatana kadar çalışır
- İkinci kez açılırsa mevcut pencere öne getirilir

### Görünüm / ses

- Balon otomatik kapanma süresi (0 = kapatma)
- TTS hızı (-10…10), geçmiş limiti
- Hedef dil, birincil motor, yedek motorlar

---

## OCR Ayrıntıları

- Ekran görüntüsü PowerShell + `System.Drawing` ile **DPI farkındalıklı** olarak alınır, OCR **Windows.Media.Ocr** ile yapılır
- OCR sırasında balon açılmaz; böylece yükleme penceresi seçilen bölgeyi kapatmaz
- OCR dili: seçilen dil → kullanıcı profili dilleri → `en-US`; ilk motor boş dönerse kurulu diğer OCR dilleri denenir
- İlk OCR boş dönerse görüntü otomatik olarak:
  - 2× (küçük bölgelerde 3×) büyütülür,
  - koyu tema algılanırsa renkleri ters çevrilir,
  - bu varyantlarla OCR yeniden denenir
- Windows OCR hâlâ başarısızsa ve `tesseract` PATH'te ise yedek olarak kullanılır
- Başarısız OCR'da son ekran görüntüsü `%TEMP%\QBTranslator_ocr_last.png` olarak saklanır ve hata balonunda yolu gösterilir; başarılı OCR'da veya uygulama kapanırken silinir
- Seçim katmanı tüm monitörleri kapsar; dış alan %35 karartılır, seçim bölgesi Windows bölge API'siyle “delinir”
- Çok küçük (12 px'den küçük) seçimler iptal sayılır

---

## Veri Saklama

| Mod | Veri dizini |
|---|---|
| Kaynak koddan çalıştırma | `translatordesktop/data/` |
| PyInstaller / kurulu sürüm | **exe'nin yanındaki `data/`** (istenen davranış) |
| exe dizini yazılamıyorsa (ör. Program Files) | `%LOCALAPPDATA%\QBTranslator\data\` |
| Geliştirme/test | `QB_DATA_DIR` ortam değişkeniyle özel dizin |

Dosyalar:

- `config.json` — ayarlar (kısayollar, dil, motor, LLM bilgileri)
- `history.json` — çeviri geçmişi
- `words.json` — kayıtlı kelimeler

> Inno Setup ile kurulum yaparken veri klasörünün yazılabilir olması için kullanıcı bazlı kurulum (LocalAppData) veya dizin izinleri önerilir. Uygulama yazılamayan dizinde otomatik olarak LocalAppData'ya geçer.

---

## Çeviri Motorları

| Motor | Not |
|---|---|
| **Google Translate** | Varsayılan; ücretsiz uç nokta, API anahtarı gerekmez |
| **MyMemory** | ~500 karakter/istek |
| **LibreTranslate** | Uç nokta + isteğe bağlı API anahtarı |
| **Lingva** | Kendi/çalışan bir örnek girilmeli |
| **LLM** | OpenAI uyumlu: Ollama `http://localhost:11434/v1`, LM Studio `http://localhost:1234/v1`, OpenAI vb. |

Yedek motor zinciri (isteğe bağlı): MyMemory → Lingva → LibreTranslate → Google.

---

## Gizlilik

- Çevrilen metin yalnızca seçtiğiniz çeviri motoruna gönderilir
- OCR ekran görüntüsü yalnızca yerel OCR için kullanılır; görüntü hiçbir yere gönderilmez
- Geçmiş/kelimeler yalnızca yerel `data/` klasöründe tutulur
- Analitik/telemetri yok
- Pano izleme varsayılan kapalı
- LLM API anahtarları `config.json` içinde düz metin saklanır; dosyayı paylaşmayın

---

## Sorun Giderme

| Sorun | Çözüm |
|---|---|
| **Kısayol kaydedilemedi** | Başka uygulama kullanıyor olabilir; farklı kombinasyon seçin. Yakalama sırasında kısayollar geçici durdurulur. |
| **Seçim yakalanamıyor** | Bazı uygulamalar Ctrl+C'yi engeller; pano izlemeyi veya Çeviri sekmesini kullanın. Hedef uygulama yönetici ise QBTranslator'u da yönetici çalıştırın. |
| **OCR metni tanımıyor** | Daha büyük/net bir alan seçin; Windows dil/OCR paketini kurun. Uygulama otomatik büyütme/renk çevirme ve diğer OCR dillerini dener. Hata balonundaki son görüntü yolunu (`%TEMP%\QBTranslator_ocr_last.png`) inceleyebilirsiniz. |
| **OCR kısayolu çalışmıyor** | OCR modu kapalı olabilir veya kısayol başka uygulamayla çakışıyordur. Ayarları kontrol edin. |
| **Google 429** | Yoğun kullanımda geçici; yedek motorları açın. |
| **Lingva 403/500** | Kendi sunucunuzu girin. |
| **Ses çıkmıyor** | Windows konuşma seslerini kontrol edin; kurumsal PowerShell kısıtlaması olabilir. |
| **Otomatik başlatma çalışmıyor** | Ayarlar'dan açıp kaydedin; registry `HKCU\...\Run\QBTranslator` girdisini kontrol edin. |
| **Uygulama açılmıyor** | `baslat_konsol.bat` ile çalıştırıp hatayı görün; tek örnek nedeniyle zaten açık olabilir. |

---

## Dosya Yapısı

```
translatordesktop/
├── main.py            # giriş: tek örnek, --background, DPI
├── appinfo.py         # QBTranslator adı/sürümü
├── mainwindow.py      # ana pencere, sekmeler, OCR/kısayol/otomasyon akışları
├── popup.py           # çeviri balonu (hedef dil + ⇄)
├── langpicker.py      # aranabilir dil seçici
├── hotkeydialog.py    # klavyeden kısayol yakalama
├── ocr.py             # ekran bölgesi seçimi + Windows OCR
├── translator.py      # çeviri motorları
├── win32util.py       # kısayol, pano, bölge/pencere API'leri
├── autostart.py       # Windows açılışında başlatma
├── storage.py         # yerel JSON depolama (kurulum dizini desteği)
├── tts.py             # Windows SAPI
├── langs.py           # diller + arama normalizasyonu
├── baslat.bat / baslat_konsol.bat
└── data/              # çalışma zamanında oluşur
```

---

## Derleme ve Paketleme

Gereksinimler (yalnızca geliştirme makinesinde):

- Python 3.9+
- PyInstaller 6.x (`python -m pip install pyinstaller`)
- Inno Setup 6 (`ISCC.exe`)

Tek komutla derleme + paketleme:

```bat
powershell -ExecutionPolicy Bypass -File build_tools\build.ps1
```

Yalnızca exe klasörünü üretmek için:

```bat
powershell -ExecutionPolicy Bypass -File build_tools\build.ps1 -SkipInstaller
```

Çıktılar:

| Çıktı | Yol |
|---|---|
| Taşınabilir sürüm (onedir) | `dist\QBTranslator\QBTranslator.exe` |
| Taşınabilir tek dosya | `portable\QBTranslator-Portable-1.0.0.exe` |
| Kurulum dosyası | `installer\QBTranslator-Setup-1.0.0.exe` |

### Boyut / performans tercihleri

- **onedir** (onefile değil): daha hızlı açılış, düşük RAM, geçici dizine çıkarma yok
- `optimize=2`: bytecode küçültme (docstring/assert temizliği)
- Kullanılmayan modüller (test, pip, sqlite3, numpy, PIL, asyncio, multiprocessing, lzma/bz2 vb.) hariç tutulur
- **UPX kapalı**: antivirüs yanlış pozitiflerini ve açılış CPU maliyetini önler
- Ölçülen değerler (bu makinede): paket **27,2 MB**, kurulum **10,0 MB**, açılış **~0,26 sn**, çalışma seti **~37 MB**, özel bellek **~22 MB**

### Kurulum davranışı

- Kullanıcı bazlı kurulum: `%LOCALAPPDATA%\Programs\QBTranslator` (yönetici gerekmez, veri klasörü yazılabilir)
- Veriler kurulum dizinindeki `data\` altında tutulur; kaldırma sırasında **silinmez** (kelimeler/geçmiş korunur)
- İlk çalıştırmada otomatik başlatma registry girdisi kurulu exe'yi gösterecek şekilde güncellenir
- `--selftest` ile paket doğrulaması yapılabilir (Tk, importlar, çeviri)

---

## GitHub ve Sürüm

- `.gitignore`: `data/`, `dist/`, `installer/`, `build/` ve önbellekler hariçtir; **kullanıcı geçmişi/ayarları asla commit edilmez.**
- `.github/workflows/build-release.yml`: `v*` etiketiyle temiz Windows runner'da derler ve GitHub Release oluşturur.
- `RELEASING.md`: sürüm, test, **kod imzalama** ve release adımları.
- `requirements-build.txt`: yalnızca derleme bağımlılığı (`pyinstaller`).
- Çalışma zamanında pip bağımlılığı yoktur.

> Release'i yerel makineden değil, GitHub Actions'tan üretmek önerilir; böylece derleme yollarında kullanıcı adı gibi bilgiler yer almaz.

## Lisans

- Proje kodu: **MIT** — `LICENSE`
- Simgeler: MouseTooltipTranslator (MIT) — ayrıntılar `THIRD_PARTY_NOTICES.md`
- Python / Tcl-Tk / OpenSSL / PyInstaller / Inno Setup bildirimleri aynı dosyadadır.
