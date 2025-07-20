# VortexVPN Manager - Web Interface

A modern, minimalist, dark-themed web interface for managing VPN configurations, testing connections, and integrating with GitHub. Optimized for mobile devices and Android.

## Features

### 🌟 Core Functionality
- **VPN Configuration Management**: Support for VLESS, Trojan, and Shadowsocks protocols
- **Real-time Connection Testing**: Test latency, jitter, and connectivity with live progress updates
- **GitHub Integration**: Load configurations from and upload results to GitHub repositories
- **Configuration Generation**: Generate sing-box compatible configuration files
- **Mobile Optimized**: Responsive design optimized for Android devices

### 🎨 Design Features
- **Dark Theme**: Modern dark theme optimized for mobile viewing
- **Minimalist UI**: Clean, elegant interface focused on functionality
- **Interactive Elements**: Smooth animations and real-time feedback
- **Progressive Web App**: Installable on Android devices
- **Touch Optimized**: Designed for touch interactions

### 🔧 Technical Features
- **Real-time Updates**: Live testing progress via WebSocket connections
- **Asynchronous Testing**: Concurrent VPN testing for faster results
- **Priority Sorting**: Automatic prioritization by country and performance
- **Account Deduplication**: Intelligent duplicate removal
- **Error Handling**: Comprehensive error handling and user feedback

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Quick Setup

1. **Clone or download the project files**
   ```bash
   # If you have all the files in a directory, navigate to it
   cd /path/to/vortexvpn-web
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables (optional)**
   ```bash
   # Create a .env file for default GitHub token
   echo "GITHUB_TOKEN=your_github_token_here" > .env
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the web interface**
   - Open your browser and navigate to `http://localhost:5000`
   - For mobile testing, use your computer's IP address: `http://your-ip:5000`

## Usage Guide

### 1. Initial Setup

#### GitHub Integration (Optional)
1. Navigate to the **Setup** section
2. Enter your GitHub token, repository owner, and repository name
3. Click **Configure GitHub**

#### Load Configuration
1. Choose between **Local Template** or **GitHub Repository**
2. Click **Load Configuration** to initialize

### 2. Adding VPN Accounts

1. Go to the **Accounts** section
2. Paste your VPN links in the text area (supports multiple links)
3. Click **Parse Links** to add them to your collection

**Supported Link Formats:**
- `vless://...`
- `trojan://...`
- `ss://...` (Shadowsocks)

### 3. Testing VPN Connections

1. Navigate to the **Testing** section
2. Review the accounts to be tested
3. Click **Start Testing** to begin
4. Monitor real-time progress and results

**Testing Features:**
- Concurrent testing (up to 5 simultaneous tests)
- Automatic retries (up to 3 attempts)
- Latency and connectivity testing
- Country and provider detection

### 4. Viewing Results

1. Go to the **Results** section
2. View summary statistics
3. Filter results by status (All/Successful/Failed)
4. Review detailed connection information

### 5. Exporting Configuration

1. Navigate to the **Export** section
2. Click **Generate Config** to create the final configuration
3. Choose your export option:
   - **Download Config**: Download as JSON file
   - **Upload to GitHub**: Push to your GitHub repository

## Mobile Installation (Android)

### Install as PWA
1. Open the web interface in Chrome on your Android device
2. Tap the menu (three dots) and select "Add to Home screen"
3. Confirm installation
4. The app will be available as a native app icon

### Features on Mobile
- Offline caching for better performance
- Native app-like experience
- Optimized touch interactions
- Portrait-oriented layout

## Configuration

### Environment Variables
Create a `.env` file in the project root:

```env
GITHUB_TOKEN=your_github_personal_access_token
```

### GitHub Token Setup
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate a new token with `repo` permissions
3. Copy the token and add it to your `.env` file or enter it in the web interface

## File Structure

```
vortexvpn-web/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── template.json         # Base configuration template
├── README.md            # This file
├── .env                 # Environment variables (optional)
├── core.py              # Core VPN management functions
├── tester.py            # VPN testing functionality
├── converter.py         # VPN link parsing and conversion
├── extractor.py         # Configuration extraction
├── utils.py             # Utility functions
├── github_client.py     # GitHub API integration
├── templates/
│   └── index.html       # Main web interface
└── static/
    ├── css/
    │   └── style.css    # Stylesheets
    ├── js/
    │   └── app.js       # JavaScript application
    ├── manifest.json    # PWA manifest
    └── sw.js           # Service worker
```

## API Endpoints

### Setup
- `POST /api/setup-github` - Configure GitHub integration
- `GET /api/list-github-files` - List GitHub repository files
- `POST /api/load-config` - Load configuration from local or GitHub

### Account Management
- `POST /api/parse-links` - Parse VPN links
- `GET /api/get-results` - Get current results and statistics

### Testing
- WebSocket: `start_testing` - Begin VPN testing
- WebSocket: `testing_update` - Real-time testing progress
- WebSocket: `testing_complete` - Testing completion notification

### Export
- `POST /api/generate-config` - Generate final configuration
- `GET /api/download-config` - Download configuration file
- `POST /api/upload-to-github` - Upload to GitHub repository

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Change the port in app.py
   socketio.run(app, debug=True, host='0.0.0.0', port=5001)
   ```

2. **GitHub authentication fails**
   - Verify your GitHub token has correct permissions
   - Check repository owner and name are correct

3. **Testing fails**
   - Ensure you have network connectivity
   - Check that VPN links are valid
   - Verify firewall settings allow outbound connections

4. **Mobile installation issues**
   - Use Chrome browser on Android
   - Ensure you're accessing via HTTPS (for production)
   - Check that manifest.json is accessible

### Performance Tips

1. **For better mobile performance:**
   - Use WiFi connection for initial setup
   - Close other browser tabs
   - Enable airplane mode briefly and re-enable to refresh network

2. **For faster testing:**
   - Use a VPS or cloud server for hosting
   - Ensure good network connectivity
   - Consider reducing concurrent test limit for slower networks

## Development

### Running in Development Mode
```bash
# Enable debug mode
export FLASK_ENV=development
python app.py
```

### Customization
- Modify `static/css/style.css` for styling changes
- Update `static/js/app.js` for functionality changes
- Edit `templates/index.html` for layout modifications

## Security Notes

- Never commit GitHub tokens to version control
- Use HTTPS in production environments
- Consider using environment variables for sensitive configuration
- Regularly rotate GitHub tokens

## License

This project is provided as-is for educational and personal use.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Verify all dependencies are installed correctly
3. Check browser console for JavaScript errors
4. Ensure all required files are present

---

**Made with ❤️ for VPN enthusiasts**