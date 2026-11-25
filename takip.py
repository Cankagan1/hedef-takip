"""
Hedef Takip Simülasyonu
=======================
Gürültülü sensör (radar) ölçümlerinden hareket eden bir hedefin konumunu
tahmin etmeye çalışıyoruz. Üç yöntemi aynı veri üzerinde karşılaştırıyoruz:

    1. Ham ölçüm         -> hiçbir şey yapmadan sensörün verdiği değer
    2. Hareketli ortalama -> son N ölçümün ortalaması
    3. Kalman filtresi    -> konum + hızı birlikte tahmin eden filtre

Karşılaştırma ölçütü: RMSE (gerçek konumdan ortalama sapma, küçük = iyi).
"""

import sys

import numpy as np
import matplotlib.pyplot as plt

# Windows terminalinde Türkçe karakterler bozuk çıkmasın diye.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# 1) SİMÜLASYON: gerçek yol ve gürültülü ölçümler
# ---------------------------------------------------------------------------

# Seed sabit: her çalıştırmada aynı "rastgele" sayılar çıkar, böylece
# sonuçlar tekrarlanabilir ve yöntemleri adil karşılaştırabiliriz.
np.random.seed(42)

n = 100            # ölçüm sayısı
t = np.arange(n)   # zaman adımları: 0, 1, 2, ... 99

# Hedef sabit hızla düz gidiyor: x'te 2 birim/adım, y'de 1 birim/adım.
# Gerçek hız = sqrt(2^2 + 1^2) ≈ 2.24 birim/adım.
true_x = 5 + 2.0 * t
true_y = 10 + 1.0 * t

# Radar ölçümü = gerçek konum + rastgele gürültü (normal dağılım).
noise = 8.0        # gürültünün standart sapması
meas_x = true_x + np.random.normal(0, noise, n)
meas_y = true_y + np.random.normal(0, noise, n)

# ---------------------------------------------------------------------------
# 2) HAREKETLİ ORTALAMA
# ---------------------------------------------------------------------------


def hareketli_ortalama(veri, pencere):
    """Her noktayı, kendisi dahil son `pencere` ölçümün ortalamasıyla değiştirir.

    Gürültü rastgele olduğu için ortalamada büyük ölçüde birbirini götürür.
    Ama sadece GEÇMİŞ ölçümlere baktığımız için, hedef ilerlerken çıktı
    sürekli geride kalır (gecikme). Ortalama gecikme ≈ (pencere - 1) / 2 adım.
    """
    sonuc = []
    for i in range(len(veri)):
        baslangic = max(0, i - pencere + 1)
        sonuc.append(np.mean(veri[baslangic:i + 1]))
    return np.array(sonuc)


pencere = 10
ma_x = hareketli_ortalama(meas_x, pencere)
ma_y = hareketli_ortalama(meas_y, pencere)

# ---------------------------------------------------------------------------
# 3) KALMAN FİLTRESİ
# ---------------------------------------------------------------------------


def kalman(olcumler, noise):
    """Sabit hız modelli 2 boyutlu Kalman filtresi.

    Durum vektörü: x = [konum_x, konum_y, hız_x, hız_y]
    Filtre her adımda iki iş yapar:
        (a) TAHMİN   : "Hedef bu hızla gidiyordu, şimdi şurada olmalı."
        (b) DÜZELTME : Yeni ölçümü tahminle karşılaştırır ve ikisi arasında
                       güvenilirliklerine göre bir ağırlıkla birleştirir.
    Hızı ölçmüyoruz, filtre onu konum değişiminden kendisi öğreniyor.
    """
    dt = 1.0

    # F: durum geçiş matrisi. "Yeni konum = eski konum + hız * dt, hız aynı kalır."
    F = np.array([[1, 0, dt, 0],
                  [0, 1, 0, dt],
                  [0, 0, 1, 0],
                  [0, 0, 0, 1]])

    # H: ölçüm matrisi. Sensör sadece konumu (x, y) ölçüyor, hızı değil.
    H = np.array([[1, 0, 0, 0],
                  [0, 1, 0, 0]])

    # Q: model belirsizliği. Küçük = "hedef gerçekten sabit hızla gidiyor, modele güven".
    # Büyükse filtre modele daha az, ölçüme daha çok güvenir (daha çok titrer).
    Q = np.eye(4) * 0.01

    # R: ölçüm gürültüsü kovaryansı. Sensörün ne kadar güvenilmez olduğunu söyler.
    R = np.eye(2) * noise ** 2

    # Başlangıç: ilk ölçümü konum kabul ediyoruz, hızı bilmiyoruz (0).
    x = np.array([olcumler[0][0], olcumler[0][1], 0.0, 0.0])

    # P: tahminin belirsizliği. Başta çok yüksek (100) çünkü hızı hiç bilmiyoruz.
    # Bu yüzden ilk adımlarda filtre ölçüme çok güvenir ve hatası büyüktür.
    P = np.eye(4) * 100

    sonuc = []
    for z in olcumler:
        # --- (a) Tahmin: modeli bir adım ileri sür ---
        x = F @ x
        P = F @ P @ F.T + Q

        # --- (b) Düzeltme: ölçümle birleştir ---
        y = z - H @ x                    # yenilik: ölçüm ile tahmin arasındaki fark
        S = H @ P @ H.T + R              # yeniliğin toplam belirsizliği
        K = P @ H.T @ np.linalg.inv(S)   # Kalman kazancı: ölçüme ne kadar güvenelim?
        x = x + K @ y                    # tahmini ölçüme doğru kaydır
        P = (np.eye(4) - K @ H) @ P      # ölçüm sonrası belirsizlik azalır

        sonuc.append(x[:2].copy())       # sadece konumu (x, y) kaydet
    return np.array(sonuc)


olcumler = np.column_stack([meas_x, meas_y])
kf = kalman(olcumler, noise)

# ---------------------------------------------------------------------------
# 4) HATA KARŞILAŞTIRMASI (RMSE)
# ---------------------------------------------------------------------------


def hata_hesapla(tahmin_x, tahmin_y):
    """Her adımdaki konum hatasını ve toplam RMSE'yi döndürür.

    Konum hatası = tahmin ile gerçek konum arasındaki öklid uzaklığı.
    RMSE         = bu hataların karelerinin ortalamasının karekökü.
    """
    hata = np.sqrt((tahmin_x - true_x) ** 2 + (tahmin_y - true_y) ** 2)
    rmse = np.sqrt(np.mean(hata ** 2))
    return hata, rmse


h_olc, r_olc = hata_hesapla(meas_x, meas_y)
h_ma, r_ma = hata_hesapla(ma_x, ma_y)
h_kf, r_kf = hata_hesapla(kf[:, 0], kf[:, 1])

print(f"Ham ölçüm RMSE:        {r_olc:.2f}")
print(f"Hareketli ortalama:    {r_ma:.2f}")
print(f"Kalman filtresi:       {r_kf:.2f}")

# ---------------------------------------------------------------------------
# 5) GRAFİKLER
# ---------------------------------------------------------------------------

# Grafik 1: hedefin yolu ve üç yöntemin tahmini
plt.figure()
plt.plot(true_x, true_y, label="Gerçek yol")
plt.scatter(meas_x, meas_y, s=10, c="red", label="Ölçümler")
plt.plot(ma_x, ma_y, c="green", label=f"Hareketli ortalama ({pencere})")
plt.plot(kf[:, 0], kf[:, 1], c="blue", label="Kalman filtresi")
plt.legend()
plt.axis("equal")
plt.title("Hedef takibi")
plt.savefig("yol.png", dpi=150)

# Grafik 2: zamana göre konum hatası
plt.figure()
plt.plot(t, h_olc, c="red", alpha=0.5, label="Ham ölçüm")
plt.plot(t, h_ma, c="green", label="Hareketli ortalama")
plt.plot(t, h_kf, c="blue", label="Kalman filtresi")
plt.xlabel("Zaman adımı")
plt.ylabel("Konum hatası")
plt.legend()
plt.title("Hata karşılaştırması")
plt.savefig("hata.png", dpi=150)

plt.show()
