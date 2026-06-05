# Gallipoli → Imoda XML Sync

Gallipoli Underwear (Ticimax) ürün feed'ini Imoda formatına dönüştürür ve `gallipoli.xml` dosyasını FTP'ye yükler.

## Nasıl çalışır?

1. `gallipoli_to_imoda.py` Gallipoli XML feed'ini indirir ve Imoda formatına çevirir.
2. `upload_ftp.py` oluşan `gallipoli.xml` dosyasını FTP sunucusuna yükler.
3. GitHub Actions bu işlemi **6 saatte bir** otomatik çalıştırır.

## Yerel çalıştırma

```bash
python gallipoli_to_imoda.py -o gallipoli.xml --only-active

set FTP_HOST=ftp.eterella.com
set FTP_USER=windamdx
set FTP_PASSWORD=your_password
set FTP_REMOTE_DIR=/public_html/yasinxml
python upload_ftp.py gallipoli.xml
```

## GitHub kurulumu

### 1. Repoyu oluştur

Bu klasörü GitHub'a yeni repo olarak yükleyin.

### 2. Secrets ekle

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret adı | Değer |
|---|---|
| `FTP_HOST` | `ftp.eterella.com` |
| `FTP_USER` | `windamdx` |
| `FTP_PASSWORD` | FTP şifreniz |
| `FTP_REMOTE_DIR` | `/public_html/yasinxml` |

### 3. İlk çalıştırma

Actions sekmesinden **Sync Gallipoli XML** workflow'unu seçip **Run workflow** ile manuel tetikleyebilirsiniz.

## Zamanlama

Workflow her 6 saatte bir çalışır (`0 */6 * * *` — UTC).
