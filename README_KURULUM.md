# DynamicSpeed — GitHub Actions uzun simülasyon

## Kurulum (DynamicSpeed-live deposu)

Yalnızca iki yeni dosyayı, **belirtilen klasörlerle** ekleyin:

- `.github/workflows/long_simulation.yml`
- `scripts/run_long_experiment.py`

Var olan `simulation.py`, `main.py`, `Dockerfile` veya Render ayarlarını değiştirmeyin. Render Auto-Deploy kapalı kalsın. Github web arayüzünde `Add file > Create new file` ile dosya adı olarak klasörlü tam yolu yazabilir, ardından dosya içeriğini kopyalayıp commit edebilirsiniz. Alternatif olarak iki klasörü zip'ten çıkartıp sürükleyerek yükleyin; GitHub dizinleri koruduğunu kontrol edin.

## İlk çalıştırma

GitHub'da **Actions → DynamicSpeed - Uzun SUMO deneyi → Run workflow**.

Seçimler: `demand=2600`, `duration=30`, `weather=dry`, `seed=314`, `policy_a=static`, `policy_b=rule`.

Yeşil tik varsa çalıştırmanın sayfasındaki **Artifacts** bölümünden ZIP'i indirin. Sonuçlar `summary.csv`, `result.json`, `run_manifest.json`; hata olursa `error.txt`. İlk test henüz doğrulanmış değildir.

## Önemli bilimsel ayrımlar

Bu workflow, GitHub deposunun **güncel `simulation.py` kodunu** kullanır, Render'daki rollback imajını değil. Mevcut kodda `--time-to-teleport 300` var; bu, araştırma notebook'larındaki farklı teleport ayarlı koşularla sonuçların birebir karşılaştırılmasını geçersiz kılabilir. Başka parametre ve model farklılıkları da olabilir. Sonuçlar yeni deney olarak raporlanmalıdır.

Bu iş akışı sadece depo yetkisi olan kişi tarafından manuel başlatılır. Web sitesindeki ziyaretçilerin kimlik doğrulamasız GitHub Actions tetiklemesi yoktur. Artifacts GitHub Actions sayfasından indirilir; şu aşamada sitede otomatik görüntülenmez.

GitHub-hosted runner kaynakları/kotaları plan ve depo görünürlüğüne bağlıdır; ücretsiz sınırsız kapasite değildir.
