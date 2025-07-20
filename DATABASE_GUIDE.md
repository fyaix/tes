# 💾 DATABASE LOCAL - PANDUAN LENGKAP

## 🎯 **OVERVIEW**

Aplikasi VortexVPN menggunakan **SQLite database lokal** (`vortexvpn.db`) untuk menyimpan:

1. **🔑 GitHub Configuration** - Token, owner, repo (auto-saved)
2. **📊 Test Session Results** - Hasil testing VPN accounts
3. **⚙️ Application Settings** - Konfigurasi aplikasi lainnya

## 📂 **FILE DATABASE**

```
vortexvpn.db  ← SQLite database file (auto-created)
```

**Location:** Di folder yang sama dengan `app.py`

## 🗃️ **STRUKTUR DATABASE**

### **1. Table: `settings`**
```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,           -- Nama setting (misal: 'github_config')
    value TEXT NOT NULL,            -- Value JSON atau string
    created_at TIMESTAMP,           -- Waktu dibuat
    updated_at TIMESTAMP            -- Waktu diupdate
);
```

### **2. Table: `test_sessions`**
```sql
CREATE TABLE test_sessions (
    id INTEGER PRIMARY KEY,         -- Auto increment ID
    session_data TEXT NOT NULL,     -- JSON hasil testing
    created_at TIMESTAMP            -- Waktu testing
);
```

## 🚀 **CARA MENGGUNAKAN DATABASE**

### **💻 OTOMATIS (Recommended)**

Database bekerja **sepenuhnya otomatis**:

#### **1. GitHub Token - Auto Save/Load**
```
✅ PERTAMA KALI:
1. Setup GitHub → Masukkan token, owner, repo
2. Klik "Save Configuration" 
   → Otomatis tersimpan ke database

✅ SELANJUTNYA:
1. Buka aplikasi → Token auto-loaded dari database
2. Tidak perlu input token lagi!
```

#### **2. Test Results - Auto Save**
```
✅ SETIAP TESTING:
1. Test VPN accounts → Hasil otomatis tersimpan
2. Bisa dilihat history test sessions
3. Data tidak hilang meskipun restart aplikasi
```

### **📱 MELALUI WEB UI**

#### **GitHub Configuration:**

1. **Pertama kali setup:**
   ```
   Section: "GitHub Integration"
   → Input: Token, Owner, Repo
   → Click: "Save Configuration"
   → ✅ Tersimpan ke database
   ```

2. **Next time:**
   ```
   Buka aplikasi → GitHub config auto-loaded
   Status: "GitHub: ✅ Configured"
   ```

#### **Test Sessions:**

```
Section: "Live Testing Progress"
→ Test VPN accounts 
→ Hasil otomatis tersimpan ke database
→ Bisa dilihat di history (jika ada UI history)
```

### **🔧 MANUAL PROGRAMMING (Advanced)**

Jika mau akses database secara manual:

#### **Setup:**
```python
from database import *

# Database auto-initialized
```

#### **GitHub Config:**
```python
# Simpan GitHub config
save_github_config(
    token="ghp_xxxxxxxxxxxx",
    owner="username", 
    repo="configs"
)

# Load GitHub config
config = get_github_config()
print(config)  # {'token': '...', 'owner': '...', 'repo': '...'}
```

#### **Test Sessions:**
```python
# Simpan hasil testing
results_data = {
    'results': [...],       # Array hasil testing
    'successful': 45,       # Jumlah sukses
    'total': 50,           # Total accounts
    'timestamp': '...'      # Waktu testing
}
session_id = save_test_session(results_data)

# Load session terakhir
latest = get_latest_test_session()
print(latest)  # Data session terakhir
```

#### **General Settings:**
```python
# Simpan setting apapun
save_setting('max_concurrent', 10)
save_setting('user_preference', {'theme': 'dark'})

# Load setting
max_conc = get_setting('max_concurrent', 5)  # Default: 5
pref = get_setting('user_preference', {})    # Default: {}
```

## 🛠️ **DATABASE TOOLS**

### **Lihat Database Content:**

```bash
# Install sqlite3 (jika belum ada)
sudo apt install sqlite3

# Buka database
sqlite3 vortexvpn.db

# Command di sqlite3:
.tables                    # Lihat semua table
.schema settings          # Lihat struktur table
SELECT * FROM settings;   # Lihat semua settings
SELECT * FROM test_sessions ORDER BY created_at DESC LIMIT 5;  # 5 session terakhir
.quit                     # Keluar
```

### **Backup Database:**
```bash
# Backup
cp vortexvpn.db vortexvpn_backup.db

# Restore
cp vortexvpn_backup.db vortexvpn.db
```

### **Reset Database:**
```bash
# Hapus database (hati-hati!)
rm vortexvpn.db

# Restart aplikasi → Database auto-recreated
python3 run.py
```

## 📊 **DATA YANG TERSIMPAN**

### **1. GitHub Configuration Example:**
```json
{
  "key": "github_config",
  "value": {
    "token": "ghp_xxxxxxxxxxxxxxxxxxxx",
    "owner": "yourusername", 
    "repo": "vpn-configs"
  }
}
```

### **2. Test Session Example:**
```json
{
  "id": 1,
  "session_data": {
    "results": [
      {
        "Status": "✅",
        "VpnType": "trojan",
        "Country": "🇩🇪",
        "Provider": "AWS",
        "Latency": 45,
        "Tested IP": "1.2.3.4"
      }
    ],
    "successful": 45,
    "total": 50,
    "timestamp": "2024-01-01T12:00:00"
  },
  "created_at": "2024-01-01 12:00:00"
}
```

## ✅ **KEUNTUNGAN DATABASE LOKAL**

### **🔒 Privacy & Security:**
- ✅ **Data tersimpan lokal** - tidak ke cloud/server
- ✅ **GitHub token aman** - tidak perlu input ulang
- ✅ **No internet required** - untuk baca data lokal

### **💾 Persistence:**
- ✅ **Data tidak hilang** saat restart aplikasi
- ✅ **History testing** tersimpan
- ✅ **Configuration persistent** - sekali setup, selalu loaded

### **⚡ Performance:**
- ✅ **Instant load** - no API calls
- ✅ **Offline access** - baca data tanpa internet
- ✅ **Fast queries** - SQLite sangat cepat

## 🆘 **TROUBLESHOOTING**

### **Database tidak terbuat:**
```bash
# Check permission
ls -la vortexvpn.db

# Create manual
python3 -c "from database import init_db; init_db()"
```

### **GitHub config tidak tersimpan:**
```python
# Test manual
from database import save_github_config, get_github_config
save_github_config("test", "user", "repo")
print(get_github_config())  # Should print: {'token': 'test', ...}
```

### **Data corrupted:**
```bash
# Check database integrity
sqlite3 vortexvpn.db "PRAGMA integrity_check;"

# Jika corrupt, reset database
rm vortexvpn.db
python3 run.py  # Auto recreate
```

---

## 🎉 **SUMMARY**

**Database sudah terintegrasi dan bekerja otomatis!**

- ✅ **GitHub token** auto-save/load
- ✅ **Test results** auto-save setiap testing  
- ✅ **No manual intervention** needed
- ✅ **Data persistent** across app restarts

**Anda tidak perlu melakukan apa-apa khusus - database bekerja di background!** 🚀