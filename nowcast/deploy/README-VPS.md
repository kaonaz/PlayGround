# Deploy G1 di VPS (Ubuntu/Debian) — tanpa trading

## 1. Upload & extract
```bash
scp btc-updown-nowcast-g1.zip root@IP_VPS:/opt/
ssh root@IP_VPS
cd /opt && unzip -o btc-updown-nowcast-g1.zip -d nowcast && cd nowcast
```

## 2. Install (sekali saja, ~3 menit)
```bash
bash nowcast/deploy/install.sh
```

## 3. Isi kredensial CLOB (read-only WS)
Buat key di Polymarket → profil → API credentials, lalu:
```bash
nano .env   # isi 3 baris, simpan. File sudah chmod 600.
```

## 4. Ambil 2 market resolved (contoh yang sudah terbukti ada)
```bash
./venv/bin/python -m nowcast.ingest.gamma --slug btc-updown-5m-1791378300 --out data/gamma
./venv/bin/python -m nowcast.ingest.gamma --slug btc-updown-5m-1791354900 --out data/gamma
```

## 5. Uji auth 20 menit dulu
```bash
./venv/bin/python -m nowcast.ingest.polybolt_ws --duration-sec 1200 --out data/raw
```
Harus muncul `[ws] authed ok`. Kalau `auth_invalid` → betulkan kredensial. Kalau error lain → simpan lognya untuk saya.

## 6. Rekam 48 jam (tmux, tahan SSH putus)
```bash
bash nowcast/deploy/run-record.sh 48
tmux attach -t nowcast-g1   # pantau; lepas dengan Ctrl-b lalu d
```

## 7. Matching + verdict G1
```bash
./venv/bin/python -m nowcast.eval.g1_match --raw data/raw --gamma data/gamma --out data/reports
cat data/reports/g1_match-*.md
```
Kirim file `.md` itu kembali ke saya untuk putusan PASS / investigasi.

## Alternatif systemd (auto-restart)
```bash
sudo cp nowcast/deploy/nowcast-g1.service /etc/systemd/system/
sudo nano /etc/systemd/system/nowcast-g1.service  # sesuaikan WorkingDirectory bila bukan /opt/nowcast
sudo systemctl daemon-reload && sudo systemctl enable --now nowcast-g1
journalctl -u nowcast-g1 -f
```

## Keamanan
- `.env` tidak pernah di-commit / di-upload ulang. Hak akses 600.
- Bot ini **tidak bisa order**: tidak ada kode trading di dalamnya (G1 = ukur saja).
