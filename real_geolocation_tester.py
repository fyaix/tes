#!/usr/bin/env python3
"""
Real Geolocation Tester - based on user's working method
Menggunakan metode yang sudah proven untuk mendapatkan ISP asli
"""

import json
import subprocess
import time
import tempfile
import os
import re
from utils import geoip_lookup

class RealGeolocationTester:
    """Test VPN dengan actual connection untuk mendapatkan ISP asli"""
    
    def __init__(self):
        self.local_http_port = 10809
        self.test_url = 'https://www.google.com'
        self.geo_api_url = 'http://ip-api.com/json'
        self.timeout_seconds = 15
        self.xray_path = './xray'  # Adjust path as needed
        
    def extract_real_ip_from_path(self, path):
        """Extract IP dari path seperti metode user"""
        if not path:
            return None
        ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', path)
        return ip_match.group(0) if ip_match else None
    
    def get_lookup_target(self, account):
        """
        Implement user's priority logic:
        1. IP dari path (highest priority)
        2. SNI (jika berbeda dari server)
        3. Host (jika berbeda dari server)
        4. JANGAN PERNAH test server field
        """
        server = account.get('server', '')
        
        # 🎯 PRIORITY #1: Check IP dari path
        path_str = account.get("_ss_path") or account.get("_ws_path") or ""
        if not path_str:
            # Check dari transport path
            transport = account.get('transport', {})
            if isinstance(transport, dict):
                path_str = transport.get('path', '')
        
        real_ip_from_path = self.extract_real_ip_from_path(path_str)
        if real_ip_from_path:
            print(f"🎯 Found real IP in path: {real_ip_from_path}")
            return real_ip_from_path, "path IP"
        
        # Get SNI dan Host
        sni = None
        host = None
        
        # Get SNI from TLS config
        tls_config = account.get('tls', {})
        if isinstance(tls_config, dict):
            sni = tls_config.get('sni') or tls_config.get('server_name')
        
        # Get host from transport headers
        transport = account.get('transport', {})
        if isinstance(transport, dict):
            headers = transport.get('headers', {})
            if isinstance(headers, dict):
                host = headers.get('Host')
        
        # 🎯 PRIORITY #2: SNI (jika berbeda dari server)
        if sni and sni != server:
            print(f"🎯 Using SNI for lookup: {sni}")
            return sni, "SNI"
        
        # 🎯 PRIORITY #3: Host (jika berbeda dari server)
        if host and host != server:
            print(f"🎯 Using Host for lookup: {host}")
            return host, "Host"
        
        # JANGAN test server field - return None untuk fallback ke proxy method
        print("⚠️  No valid lookup target found, will use proxy method")
        return None, "proxy"
    
    def create_xray_config(self, account):
        """Create Xray config untuk testing - adapted dari user's method"""
        protocol = account.get('type', '')
        
        # Build outbound berdasarkan protokol
        if protocol == 'vless':
            outbound = {
                "protocol": "vless",
                "settings": {
                    "vnext": [{
                        "address": account.get('server', ''),
                        "port": int(account.get('server_port', 443)),
                        "users": [{
                            "id": account.get('uuid', ''),
                            "encryption": account.get('encryption', 'none')
                        }]
                    }]
                }
            }
        elif protocol == 'vmess':
            outbound = {
                "protocol": "vmess",
                "settings": {
                    "vnext": [{
                        "address": account.get('server', ''),
                        "port": int(account.get('server_port', 443)),
                        "users": [{
                            "id": account.get('uuid', ''),
                            "alterId": account.get('alter_id', 0)
                        }]
                    }]
                }
            }
        elif protocol == 'trojan':
            outbound = {
                "protocol": "trojan",
                "settings": {
                    "servers": [{
                        "address": account.get('server', ''),
                        "port": int(account.get('server_port', 443)),
                        "password": account.get('password', '')
                    }]
                }
            }
        elif protocol == 'shadowsocks':
            outbound = {
                "protocol": "shadowsocks",
                "settings": {
                    "servers": [{
                        "address": account.get('server', ''),
                        "port": int(account.get('server_port', 443)),
                        "method": account.get('method', 'aes-256-gcm'),
                        "password": account.get('password', '')
                    }]
                }
            }
        else:
            return None
        
        # Add stream settings jika ada
        transport = account.get('transport', {})
        tls_config = account.get('tls', {})
        
        if transport or tls_config:
            stream_settings = {}
            
            # Network type
            if transport.get('type') == 'ws':
                stream_settings['network'] = 'ws'
                stream_settings['wsSettings'] = {
                    'path': transport.get('path', '/'),
                    'headers': transport.get('headers', {})
                }
            
            # TLS settings
            if tls_config.get('enabled'):
                stream_settings['security'] = 'tls'
                stream_settings['tlsSettings'] = {
                    'serverName': tls_config.get('sni') or tls_config.get('server_name', '')
                }
            
            if stream_settings:
                outbound['streamSettings'] = stream_settings
        
        return {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "port": self.local_http_port,
                "protocol": "http",
                "settings": {}
            }],
            "outbounds": [outbound]
        }
    
    def test_real_location(self, account):
        """
        Test VPN connection dan dapatkan real geolocation
        Menggunakan metode user yang sudah proven working
        """
        try:
            # Get lookup target berdasarkan priority user
            lookup_target, method = self.get_lookup_target(account)
            
            # Jika ada lookup target (IP/SNI/Host), test langsung
            if lookup_target and method != "proxy":
                print(f"🔍 Direct lookup using {method}: {lookup_target}")
                geo_data = self._get_geo_data(lookup_target)
                if geo_data and geo_data.get('status') == 'success':
                    return {
                        'success': True,
                        'country': geo_data.get('countryCode', 'N/A'),
                        'country_name': geo_data.get('country', 'N/A'),
                        'isp': geo_data.get('isp', 'N/A'),
                        'org': geo_data.get('org', 'N/A'),
                        'ip': geo_data.get('query', lookup_target),
                        'method': f"Direct {method}",
                        'latency': 0  # No connection test needed
                    }
            
            # Fallback: Test dengan actual VPN connection (user's method)
            print("🔍 Testing with actual VPN connection...")
            return self._test_with_proxy(account)
            
        except Exception as e:
            print(f"❌ Real location test error: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': 'failed'
            }
    
    def _get_geo_data(self, target):
        """Get geolocation data untuk target IP/domain"""
        try:
            result = subprocess.run(
                ['curl', '-s', f"{self.geo_api_url}/{target}"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception:
            pass
        return None
    
    def _test_with_proxy(self, account):
        """Test dengan actual VPN connection seperti metode user"""
        if not os.path.exists(self.xray_path):
            print(f"⚠️  Xray not found at {self.xray_path}, skipping proxy test")
            return {'success': False, 'error': 'Xray not available', 'method': 'proxy'}
        
        try:
            # Create Xray config
            config = self.create_xray_config(account)
            if not config:
                return {'success': False, 'error': 'Config creation failed', 'method': 'proxy'}
            
            # Write temp config
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(config, f)
                temp_config = f.name
            
            try:
                # Start Xray process
                xray_process = subprocess.Popen(
                    [self.xray_path, '-c', temp_config],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                time.sleep(2)  # Wait for startup
                
                # Test connection
                proxy_arg = f"http://127.0.0.1:{self.local_http_port}"
                start_time = time.monotonic()
                
                subprocess.run(
                    ['curl', '-s', '-I', self.test_url, '--proxy', proxy_arg, 
                     '--connect-timeout', str(self.timeout_seconds)],
                    check=True, capture_output=True, timeout=self.timeout_seconds + 2
                )
                
                end_time = time.monotonic()
                latency_ms = (end_time - start_time) * 1000
                
                # Get real IP via proxy
                geo_result = subprocess.run(
                    ['curl', '-s', self.geo_api_url, '--proxy', proxy_arg],
                    capture_output=True, text=True, timeout=10
                )
                
                if geo_result.returncode == 0:
                    geo_data = json.loads(geo_result.stdout)
                    return {
                        'success': True,
                        'country': geo_data.get('countryCode', 'N/A'),
                        'country_name': geo_data.get('country', 'N/A'),
                        'isp': geo_data.get('isp', 'N/A'),
                        'org': geo_data.get('org', 'N/A'),
                        'ip': geo_data.get('query', 'N/A'),
                        'method': 'VPN Proxy',
                        'latency': latency_ms
                    }
                
            finally:
                # Cleanup
                if 'xray_process' in locals():
                    xray_process.kill()
                os.unlink(temp_config)
                
        except Exception as e:
            return {'success': False, 'error': str(e), 'method': 'proxy'}
        
        return {'success': False, 'error': 'Connection failed', 'method': 'proxy'}

# Integration function untuk existing tester
def get_real_geolocation(account):
    """
    Integration function yang bisa dipanggil dari tester.py
    Implements user's proven method untuk real ISP detection
    """
    tester = RealGeolocationTester()
    result = tester.test_real_location(account)
    
    if result.get('success'):
        # Convert ke format yang compatible dengan existing system
        from utils import get_flag_emoji
        
        country_code = result.get('country', 'N/A')
        country_flag = get_flag_emoji(country_code) if country_code != 'N/A' else '❓'
        
        return {
            "Country": country_flag,
            "Provider": result.get('isp', result.get('org', '-')),
            "Tested IP": result.get('ip', '-'),
            "Resolution Method": result.get('method', 'Real Geo'),
            "Real Location": True,
            "Latency": result.get('latency', 0)
        }
    
    return None  # Fallback ke method lain

if __name__ == "__main__":
    # Test dengan sample account
    test_account = {
        'type': 'trojan',
        'server': 'cdn.cloudflare.com',
        'server_port': 443,
        'password': 'test',
        'transport': {
            'type': 'ws',
            'path': '/path/159.89.15.20-443/ws',
            'headers': {'Host': 'sg.real.server.com'}
        },
        'tls': {
            'enabled': True,
            'sni': 'sg.digitalocean.server.com'
        }
    }
    
    tester = RealGeolocationTester()
    result = tester.test_real_location(test_account)
    print(f"Test result: {result}")