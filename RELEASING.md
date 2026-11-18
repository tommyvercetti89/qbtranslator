# Sürüm ve Dağıtım Rehberi

Bu dosya QBTranslator için derleme, kod imzalama ve GitHub release adımlarını
özetler. Depoya hiçbir zaman `data/`, API anahtarı veya kullanıcı geçmişi
eklenmemelidir; bunlar `.gitignore` ile hariç tutulur.

## 1. Sürüm numarasını güncelle

Aşağıdaki yerlerde sürümü birlikte değiştirin:

- `appinfo.py` → `APP_VERSION`
- `build_tools/version_info.txt` → `filevers`, `prodvers`, metin alanları
- `build_tools/installer.iss` → `MyAppVersion`
- `README.md` (gerekirse)

## 2. Derle ve test et

```bat
powershell -ExecutionPolicy Bypass -File build_tools\build.ps1
```

Bu komut:

1. Simgeyi üretir,
2. PyInstaller **onedir** paketini oluşturur (`dist\QBTranslator`),
3. Tek dosyalık **portatif** exe'yi oluşturur (`portable\QBTranslator-Portable-<sürüm>.exe`),
4. Her iki pakette `--selftest` çalıştırır,
5. Inno Setup kurulumunu üretir (`installer\QBTranslator-Setup-<sürüm>.exe`).

Kurulumu temiz bir dizinde sessizce test edin:

```bat
QBTranslator-Setup-1.0.0.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR=%TEMP%\QBTranslatorTest
```

## 3. Kod imzalama (önerilir)

Windows SmartScreen için dağıtım öncesi imzalama önerilir. 2023'ten beri
kamuya açık CA'lar özel anahtarı **donanım token'ında veya bulut HSM'de**
tutmayı zorunlu kılar; `.pfx` dosyası kullanılmaz.

### Seçenekler

- **OV kod imzalama sertifikası** (DigiCert, Sectigo, GlobalSign, Certum…)
- **EV kod imzalama sertifikası** (SmartScreen itibarı daha hızlı)
- **Azure Trusted Signing** (bulut, CI dostu; uygunluk koşulları vardır)
- **SignPath.io** (açık kaynak projeler için ücretsiz bulut imzalama)

### SignTool ile imzalama

```bat
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a "dist\QBTranslator\QBTranslator.exe"
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a "installer\QBTranslator-Setup-1.0.0.exe"
signtool verify /pa /v "installer\QBTranslator-Setup-1.0.0.exe"
```

- `/tr` ve `/td`: RFC3161 zaman damgası (imza süresi dolsa bile geçerlilik sürer).
- Donanım token'ı PIN ister; CI'da bulut imzalama kullanın.

### Inno Setup entegrasyonu

`build_tools/installer.iss` içine:

```ini
[Setup]
SignTool=mysigner
SignedUninstaller=yes
```

Inno Setup IDE → Tools → Configure Sign Tools bölümünde `mysigner` komutunu
tanımlayın (`... signtool.exe sign /fd SHA256 /tr ... /td SHA256 $f`).

## 4. GitHub'a gönderim

```bat
git init
git add .
git commit -m "QBTranslator v1.0.0"
git branch -M main
git remote add origin https://github.com/<kullanici>/<repo>.git
git push -u origin main
```

- `data/`, `dist/`, `installer/`, `build/` `.gitignore` ile hariçtir.
- `git status` çıktısında bu klasörler görünmemelidir.
- GitHub Actions workflow'u (`build-release.yml`) tag push'unda derler.

## 5. Release

```bat
git tag v1.0.0
git push origin v1.0.0
```

Workflow `v*` etiketinde:

1. Temiz Windows runner'da derler (yerel kullanıcı yolu sızmaz),
2. `QBTranslator-Setup-1.0.0.exe` ve `QBTranslator-Portable-1.0.0.exe` dosyalarını üretir,
3. GitHub Release'e yükler.

İmzalama secrets'ları eklendiyse workflow'a imzalama adımı eklenmelidir.
İmzasız release'lerde SmartScreen uyarısı beklenir.

## 6. Release kontrol listesi

- [ ] Sürüm numaraları güncel
- [ ] `python -m py_compile` / testler geçti
- [ ] `data/` commit edilmedi
- [ ] `dist/` ve `installer/` commit edilmedi
- [ ] Kurulum temiz makinede test edildi
- [ ] İmza doğrulandı (`signtool verify /pa /v`)
- [ ] SHA-256 hash'i release notlarına eklendi
- [ ] Gizlilik: ekran görüntüsü/geçmiş/anahtar yok

```powershell
Get-FileHash .\installer\QBTranslator-Setup-1.0.0.exe -Algorithm SHA256
```
