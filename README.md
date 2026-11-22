# SonOyuncu Auto Message Bot

Windows üzerinde çalışan, **CustomTkinter** ile geliştirilmiş modern koyu temalı **Minecraft Java Edition (SonOyuncu Skyblock)** otomatik sohbet mesajı gönderme uygulaması.

## Özellikler

### Kontrol Paneli
- **Başlat / Duraklat / Devam Et / Durdur** kontrolleri
- Anlık durum göstergesi, sonraki mesaj geri sayım sayacı ve ilerleme çubuğu
- Gönderilen toplam mesaj ve sıradaki mesaj takibi
- **F8 Acil Durdurma**: Oyun penceresi odaktayken bile global `F8` tuşuyla anında güvenli durdurma

### Mesaj Yönetimi
- Birden fazla reklam/duyuru mesajı ekleme, düzenleme ve silme
- Mesajları tek tek aktif/pasif yapabilme
- Yukarı/Aşağı (`↑` / `↓`) butonları ile mesajları **belirlenen sırayla** gönderme
- Karakter sayacı (Minecraft `256` ve SonOyuncu 1.8.9 `100` karakter uyarısı)

### Zamanlama
- Varsayılan **120 saniye** gönderim aralığı
- Hızlı seçim butonları (`60`, `120`, `180`, `300` sn) veya özel süre girişi
- Başlatıldığında ilk mesajı 3 sn hazırlık sonrası gönderme veya tam aralık bekleme seçeneği

### Minecraft Bağlantısı ve Güvenlik
- Açık **Minecraft Java Edition / SonOyuncu** pencerelerini otomatik algılama
- Pencere durumu göstergesi (*Bağlı ve Odakta*, *Arka Planda*, *Simge Durumunda*, *Bulunamadı*)
- **Otomatik Duraklatma**: Minecraft penceresi kapatıldığında veya kaybolduğunda işlemi güvenli şekilde duraklatır
- Türkçe karakterler (`ğ, ü, ş, ı, İ, ö, ç`) için pano tabanlı (`Ctrl+V`) ve alternatif doğrudan yazma desteği
- **Çoklu İş Parçacığı (Threading)**: Arayüz hiçbir zaman donmaz; program kapatılırken tüm iş parçacıkları güvenli şekilde sonlandırılır
- **Anti-cheat / CAPTCHA aşımı içermez**: Yalnızca standart işletim sistemi klavye girişi kullanır

### Kalıcı Ayarlar (JSON)
- Tüm mesajlar, zamanlama tercihleri, pencere ve güvenlik ayarları otomatik olarak `data/settings.json` dosyasında saklanır.

---

## Proje Klasör Yapısı

```text
otobot/
├── main.py                      # Uygulama giriş noktası
├── requirements.txt             # Python bağımlılıkları
├── SonOyuncuAutoMessage.spec    # PyInstaller EXE derleme yapılandırması
├── build_exe.bat                # Tek tıkla Windows EXE oluşturma betiği
├── README.md                    # Proje dokümantasyonu
├── app/
│   ├── __init__.py
│   ├── constants.py             # Sabitler, durum enumları, kural metinleri
│   ├── utils.py                 # Yol çözümleme, loglama, süre formatlama
│   ├── config_manager.py        # JSON ayar ve mesaj yönetimi
│   ├── window_manager.py        # PyGetWindow ile Minecraft pencere algılama/odaklama
│   ├── chat_sender.py           # PyAutoGUI / Pano ile sohbet mesajı gönderimi
│   ├── hotkey_manager.py        # Global F8 acil durdurma dinleyicisi
│   ├── bot_engine.py            # Thread-safe durum makinesi ve zamanlayıcı motor
│   └── ui/
│       ├── __init__.py
│       ├── theme.py             # Koyu tema renk paleti ve font ayarları
│       ├── main_window.py       # Ana pencere ve olay kuyruğu yönetimi
│       ├── control_panel.py     # Kontrol Paneli bileşeni
│       ├── message_panel.py     # Mesaj Yönetimi bileşeni
│       ├── timing_panel.py      # Zamanlama bileşeni
│       ├── minecraft_panel.py   # Minecraft Bağlantısı ve kural onayı bileşeni
│       └── dialogs.py           # Mesaj ekleme/düzenleme ve uyarı pencereleri
└── tests/
    ├── test_config_manager.py
    ├── test_window_manager.py
    ├── test_chat_sender.py
    └── test_bot_engine.py
```

---

## Kurulum ve Çalıştırma (Windows)

### Gereksinimler
- Windows 10 veya Windows 11
- Python 3.10+ (kurulumda **Add Python to PATH** seçili olmalıdır)

### 1. Bağımlılıkları Yükleyin
```bat
python -m pip install -r requirements.txt
```

### 2. Uygulamayı Başlatın
```bat
python main.py
```

---

## Windows İçin EXE Oluşturma (PyInstaller)

Projeyi tek bir çalıştırılabilir `.exe` dosyasına dönüştürmek için:

### Yöntem 1: Hazır Betik ile
`build_exe.bat` dosyasına çift tıklayın veya komut satırında çalıştırın:
```bat
build_exe.bat
```

### Yöntem 2: Manuel PyInstaller Komutu
```bat
python -m pip install pyinstaller
pyinstaller --clean --noconfirm SonOyuncuAutoMessage.spec
```

Derleme tamamlandığında çalıştırılabilir dosya `dist\SonOyuncuAutoMessageBot.exe` konumunda oluşturulur. Ayarlar (`data\settings.json`) ve günlükler (`logs\otobot.log`) EXE'nin bulunduğu klasörde (veya yazma izni yoksa `%APPDATA%\SonOyuncuAutoMessageBot` altında) saklanır.

---

## Testleri Çalıştırma

```bat
python -m unittest discover -s tests -v
```

---

## Kullanım ve Kurallar Uyarısı

- Bu uygulama CAPTCHA veya anti-cheat sistemlerini aşmaya yönelik hiçbir mekanizma içermez.
- SonOyuncu sunucusunun reklam bekleme süresi ve sohbet kurallarına uygun aralıklar (varsayılan **120 saniye**) kullanmanız önerilir.
- İstenmeyen bir durumda klavyeden **`F8`** tuşuna basarak veya fare imlecini ekranın sol üst köşesine getirerek (`PyAutoGUI FailSafe`) gönderimi anında durdurabilirsiniz.
