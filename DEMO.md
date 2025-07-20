# VortexVPN Manager - Quick Demo Guide

## Quick Start (30 seconds!)

### 1. Start the Application
```bash
python run.py
```
or
```bash
python app.py
```

The web interface will open automatically at `http://localhost:5000`

### 2. Super Simple Demo Flow

#### Step 1: Just Paste & Test!
Go to **Add VPN Links & Test** section and paste demo links:

```
vless://demo-uuid@demo.example.com:443?type=ws&path=/demo&host=demo.example.com&security=tls#Demo%20VLESS
trojan://demo-password@demo.example.com:443?type=ws&path=/trojan&host=demo.example.com&security=tls#Demo%20Trojan
ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTpkZW1vLXBhc3N3b3Jk@demo.example.com:443?plugin=v2ray-plugin&plugin-opts=tls;host%3Ddemo.example.com;path%3D/ss#Demo%20Shadowsocks
```

Click **🚀 Add Links & Start Testing** - that's it!

#### Step 2: Watch the Magic ✨
- Automatically switches to **Live Testing** section
- See real-time table updates like the original CLI
- Watch progress bars and live statistics
- **Configuration auto-generates** when testing completes!

#### Step 3: Download Ready Config
- Go to **Download & Upload** section  
- Your config is already generated and ready!
- Click **⬇️ Download VPN Config** or **⬆️ Upload to GitHub**

## Mobile Demo (Android)

### Install as PWA
1. Open Chrome on your Android device
2. Navigate to `http://your-computer-ip:5000`
3. Tap menu → "Add to Home screen"
4. Use the app like a native Android application

### Features to Test
- Touch navigation between sections
- Responsive layout on different screen sizes
- Real-time updates during testing
- Smooth animations and transitions

## Features Showcase

### 🎨 Design Features
- **Dark Theme**: Modern dark interface optimized for mobile
- **Smooth Animations**: Loading screens, progress bars, transitions
- **Interactive Elements**: Hover effects, button states, real-time feedback
- **Mobile Optimized**: Touch-friendly controls and responsive layout

### ⚡ Functionality
- **Real-time Testing**: Live progress updates via WebSocket
- **GitHub Integration**: Load/save configurations from GitHub
- **VPN Protocol Support**: VLESS, Trojan, Shadowsocks parsing
- **Intelligent Testing**: Concurrent testing with automatic retries
- **Smart Results**: Country detection, latency measurement, priority sorting

### 📱 Mobile Features
- **PWA Support**: Installable as native app on Android
- **Offline Caching**: Works without internet for basic functionality
- **Touch Optimized**: Gesture support and mobile-friendly interface
- **Responsive Design**: Adapts to any screen size

## Sample Test Data

If you want to test with actual working VPN accounts, you'll need to:

1. Replace the demo links with real VPN subscription links
2. Ensure you have network connectivity
3. The testing will show real latency and connectivity results

## Troubleshooting Demo Issues

### Port Already in Use
```bash
# Use different port
python -c "from app import app, socketio; socketio.run(app, host='0.0.0.0', port=5001)"
```

### Dependencies Missing
```bash
pip install flask flask-socketio python-dotenv requests
```

### Mobile Access Issues
1. Ensure your computer and phone are on the same network
2. Use your computer's IP address instead of localhost
3. Disable firewall temporarily if needed

## Performance Notes

- Demo links will fail connection tests (they're not real servers)
- Real VPN links will show actual latency and connectivity
- Testing speed depends on your network connection
- Mobile performance is optimized for touch interactions

---

**Ready to explore? Run `python run.py` and start the demo!** 🚀