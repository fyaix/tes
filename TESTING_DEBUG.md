# VortexVPN Web - Testing & Debug Guide

## 🐛 Table Display Issue - Debugging Steps

### 1. **Manual Table Test**
Setelah aplikasi running dan buka di browser:

1. Buka Developer Console (F12)
2. Ketik: `testTableDisplay()`
3. Lihat apakah table terisi dengan sample data

### 2. **Check Console Logs**
Monitor console untuk melihat:
- Socket.IO connection status
- Data yang diterima dari server
- Error messages

### 3. **Backend Debugging**
Server akan print logs seperti:
```
Emitting update: 1/3 completed
```

### 4. **Step-by-Step Testing**

#### A. **Basic Setup Test**
```bash
python3 run.py
# Buka http://localhost:5000
# Pastikan "Template loaded" di status
```

#### B. **Table Structure Test**
1. Go to **Testing** section
2. Check bahwa table headers ada
3. Jalankan `testTableDisplay()` di console

#### C. **Real Testing Flow**
1. **Add Links & Test** section
2. Paste demo links:
```
vless://demo-uuid@demo.example.com:443?type=ws&path=/demo&host=demo.example.com&security=tls#Demo%20VLESS
trojan://demo-password@demo.example.com:443?type=ws&path=/trojan&host=demo.example.com&security=tls#Demo%20Trojan
ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTpkZW1vLXBhc3N3b3Jk@demo.example.com:443?plugin=v2ray-plugin&plugin-opts=tls;host%3Ddemo.example.com;path%3D/ss#Demo%20Shadowsocks
```
3. Click **🚀 Add Links & Start Testing**
4. Watch console logs dan table updates

## ✅ **Fixes Implemented**

### 1. **Database Integration**
- ✅ SQLite local storage untuk GitHub token
- ✅ Auto-load GitHub config on startup
- ✅ Persistent session storage

### 2. **Simplified Workflow** 
- ✅ Single button "Add Links & Start Testing"
- ✅ Auto-parse VPN links
- ✅ Auto-generate config after testing
- ✅ Direct navigation to testing section

### 3. **Table Improvements**
- ✅ Proper HTML table structure
- ✅ Real-time updates via Socket.IO
- ✅ Mobile responsive design
- ✅ Fallback data handling
- ✅ Debug functions

### 4. **Backend Updates**
- ✅ Periodic update emissions
- ✅ Better data structure
- ✅ Error handling
- ✅ Live results tracking

## 🔧 **If Table Still Not Working**

### Check 1: HTML Structure
```javascript
// In console, check if table exists
document.getElementById('testing-table-body')
```

### Check 2: Data Reception
```javascript
// Monitor Socket.IO events
socket.on('testing_update', function(data) {
    console.log('Raw data:', data);
});
```

### Check 3: Manual Update
```javascript
// Force update with test data
testTableDisplay();
```

### Check 4: Backend Data
Lihat terminal/console untuk backend logs:
```
Emitting update: X/Y completed
Testing progress update: {data}
```

## 📱 **Mobile Testing**

1. **Local Network Access**
   ```bash
   # Find your IP
   ip addr show
   # Access from phone: http://YOUR_IP:5000
   ```

2. **PWA Installation**
   - Chrome menu → "Add to Home screen"
   - Test table responsiveness

## 🚨 **Common Issues & Solutions**

| Issue | Solution |
|-------|----------|
| Table empty | Run `testTableDisplay()` |
| No socket updates | Check console for connection |
| Data not parsing | Test with `python3 simple_test.py` |
| Mobile layout broken | Check CSS media queries |
| GitHub not saving | Check database permissions |

## 📞 **Need Help?**

1. **Check browser console** for errors
2. **Check terminal** for backend logs  
3. **Run manual test** with `testTableDisplay()`
4. **Test parsing** with `python3 simple_test.py`

---

**The table SHOULD work now. If not, run the debug steps above!** ✨