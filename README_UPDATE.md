# DynamicSpeed v43.2 — Render Free memory guard

Bu bir kapasite çözümü değil, güvenli çalışma yamasıdır. 512 MB üzerinde çöken 30 dakikalık simülasyonlar ücretsiz servis için kapalıdır. 10–15 dakika izinli; 15 dakika başarı garantisi yoktur.

## GitHub'a yükle
ZIP'i aç. `DynamicSpeed-live` deposunun **ana dizinine** yalnızca `main.py`, `simulation.py`, `simulator.html`, `Dockerfile` dosyalarını yükle. `Commit changes` yap; Render son deploy Live olduğunda `/api/health` adresini kontrol et. `max_duration_minutes:15` görünmeli. 600 araç/saat, kuru, 10 dakika, Static ve Rule-Based ile doğrula. Daha sonra 1200/10; en son 600/15 test et.

## Neler değişti?
- Linux cgroup v2 `memory.current` ve `memory.max` üzerinden bellek izleme (varsa).
- 512 MB ortamda belleğin %83'üne yaklaşınca kontrollü hata; zorunlu OOM önlenmeye çalışılır, garanti edilmez.
- Ücretsiz Render 30 dakika API ve UI üzerinden reddedilir; daha güçlü sunucuda `DS_MAX_DURATION_MINUTES=90` ile açılabilir, yine ölçüm gerekir.
- Health yanıtında `memory_used_mb`, `memory_limit_mb`, `max_duration_minutes` alanları.
- `MALLOC_ARENA_MAX=2` ayarı olası glibc arena parçalanmasını sınırlamaya yardımcı olabilir.

**Model uyarısı:** 300 saniye teleport ayarı önceki hafif sürümden korunuyor. Bu koşular eski 90 dakikalık araştırma çalışmalarıyla doğrudan karşılaştırılmamalı.
