# 🏃‍♀️ Spor Takip Projem

Bu proje, bireylerin egzersiz esnasındaki hareketlerini gerçek zamanlı olarak analiz etmek, saymak ve performans verilerini toplamak amacıyla geliştirilmiş bir görüntü işleme uygulamasıdır. Sistem, bir kameradan gelen canlı görüntüleri analiz ederek, kullanıcıların belirli hareketleri doğru yapıp yapmadığını ölçer ve sonuçları kaydeder.

---

## 🎯 Proje Amacı

- Sporu düzenli yapan bireylerin antrenmanlarını dijital olarak izlemek
- Yapay zeka desteğiyle yanlış egzersizleri tespit edebilmek
- Spor salonlarında eğitmen yardımına ihtiyaç duymadan doğru hareketleri öğretmek
- Aktivite takibi ve performans geçmişi sunmak

---

## 🧩 Özellikler

- ✅ Gerçek zamanlı kamera görüntüsü üzerinden hareket analizi
- ✅ Egzersiz (squat, push-up, jumping jack vb.) tespiti ve sayımı
- ✅ Vücut duruş (pose) noktaları takibi
- ✅ Egzersiz geçmişi kaydı ve grafiksel gösterimi
- ✅ Hatalı duruşlara uyarı verme (geliştirilebilir)
- ✅ Basit grafiksel arayüz (Tkinter / Pygame)
- ✅ Taşınabilir ve bağımsız çalışabilir Python script yapısı

---

## 🧠 Kullanılan Teknolojiler

| Teknoloji     | Açıklama                                        |
|---------------|-------------------------------------------------|
| Python        | Ana programlama dili                            |
| OpenCV        | Görüntü işleme ve video akışı yönetimi          |
| Mediapipe     | İnsan vücudu anahtar noktalarının tespiti       |
| NumPy         | Sayısal işlemler ve matris manipülasyonu        |
| Matplotlib    | Grafik çizimi                                   |
| Pandas        | Egzersiz kayıtlarının CSV dosyasında tutulması  |
| Tkinter / Pygame | Kullanıcı arayüzü ve görsel geribildirim      |

---

## 🖼️ Örnek Ekran Görüntüleri

> (Buraya istersen `.png` veya `.gif` görseller eklersin.)

- Vücut noktalarının çizimi
- Sayım ekranı
- Grafiksel analiz çıktısı

---

## 📁 Proje Dosya Yapısı

```text
SporTakipProjem/
├── main.py                   # Ana Python dosyası
├── tracker.py               # Pose tespit ve egzersiz sayımı
├── data/
│   └── records.csv          # Kullanıcı performans verileri
├── utils/
│   ├── draw_utils.py        # Grafik çizim fonksiyonları
│   └── timer.py             # Zaman yönetimi
├── README.md                # Proje dokümantasyonu
├── requirements.txt         # Gereken Python kütüphaneleri
└── images/
    └── screenshot.png       # Örnek ekran görüntüsü
