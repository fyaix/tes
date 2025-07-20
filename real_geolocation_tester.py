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
    
    def clean_domain_from_server_for_testing(self, domain, server):
        """
        Clean domain dari server part HANYA UNTUK TESTING
        
        Examples:
        1. server="example.com", domain="sg.example.com" → return "sg" (suffix)
        2. server="quiz.int.vidio.com", domain="quiz.int.vidio.com.admin.site" → return "admin.site" (prefix)
        3. server="example.com", domain="example.com" → return None (sama persis)
        
        PENTING: Ini hanya untuk testing, original domain akan di-restore untuk config final
        """
        if not domain or not server:
            return domain
            
        # Jika sama persis, tetap test (user request: jangan skip)
        if domain == server:
            print(f"🔧 Testing: Same domain {domain} - will test as-is (user preference)")
            return domain
            
        # Case 1: Domain mengandung server sebagai PREFIX (user's example)
        # quiz.int.vidio.com.admin.ari-andika2.site → admin.ari-andika2.site
        if domain.startswith(server + '.'):
            # Extract suffix setelah server domain
            suffix = domain[len(server + '.'):]
            print(f"🔧 Testing: Clean {domain} → {suffix} (removed prefix {server})")
            return suffix
            
        # Case 2: Domain mengandung server sebagai SUFFIX  
        # sg.example.com → sg (original logic)
        if domain.endswith('.' + server):
            # Extract prefix sebelum server domain
            prefix = domain[:-len('.' + server)]
            print(f"🔧 Testing: Clean {domain} → {prefix} (removed suffix {server})")
            return prefix
        
        # Jika berbeda total, return as-is  
        print(f"🔧 Testing: Use {domain} as-is (different from server)")
        return domain
    
    def restore_original_domain_for_config(self, account):
        """
        Restore original domain values untuk config final
        Kembalikan SNI/Host ke nilai asli setelah testing
        """
        # Get original values (yang belum di-clean)
        original_sni = None
        original_host = None
        
        # Get original SNI from TLS config
        tls_config = account.get('tls', {})
        if isinstance(tls_config, dict):
            original_sni = tls_config.get('sni') or tls_config.get('server_name')
        
        # Get original host from transport headers
        transport = account.get('transport', {})
        if isinstance(transport, dict):
            headers = transport.get('headers', {})
            if isinstance(headers, dict):
                original_host = headers.get('Host')
        
        print(f"🔄 Config: Restored original SNI={original_sni}, Host={original_host}")
        return original_sni, original_host
    
    def get_lookup_target(self, account):
        """
        USER PREFERENCE: Use actual VPN proxy method (lebih akurat)
        
        Priority logic:
        1. IP dari path (direct geolocation - tetap prioritas tinggi)
        2. Semua lainnya → actual VPN proxy method (user preference)
        
        JANGAN PERNAH test server field
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
        
        print(f"🔍 Raw values - Server: {server}, SNI: {sni}, Host: {host}")
        
        # 🎯 USER PREFERENCE: Pakai actual VPN proxy method saja (lebih akurat)
        print("🎯 Using actual VPN proxy method (user preference: test actuall vpn lebih akurat)")
        return None, "actual VPN proxy method"
    
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
    
    def _resolve_domain_to_best_ip(self, domain):
        """Resolve domain ke IP dan pilih yang terbaik (avoid CDN)"""
        try:
            import socket
            
            # Get all IPs untuk domain
            all_ips = []
            try:
                # Standard resolution
                ip = socket.gethostbyname(domain)
                all_ips.append(ip)
            except:
                pass
            
            # Try with different DNS (if dig available)
            try:
                result = subprocess.run(
                    ['dig', '+short', domain], 
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        line = line.strip()
                        if line and self._is_valid_ip(line):
                            all_ips.append(line)
            except:
                pass
            
            # Remove duplicates
            unique_ips = list(set(all_ips))
            
            if not unique_ips:
                return None
            
            # Jika cuma 1 IP, return langsung
            if len(unique_ips) == 1:
                return unique_ips[0]
            
            # Jika banyak IP, pilih yang terbaik (avoid CDN)
            best_ip = None
            best_score = -999
            
            for ip in unique_ips:
                geo_data = self._get_geo_data_direct(ip)
                if geo_data and geo_data.get('status') == 'success':
                    provider = geo_data.get('isp', '').lower()
                    score = 0
                    
                    # Penalize CDN providers
                    if any(cdn in provider for cdn in ['cloudflare', 'amazon', 'aws', 'google']):
                        score -= 50
                    
                    # Reward VPS providers
                    if any(vps in provider for vps in ['digitalocean', 'linode', 'vultr', 'hetzner', 'ovh']):
                        score += 30
                    
                    if score > best_score:
                        best_score = score
                        best_ip = ip
            
            print(f"🎯 Resolved {domain} to {len(unique_ips)} IPs, selected: {best_ip} (score: {best_score})")
            return best_ip or unique_ips[0]  # Fallback ke IP pertama
            
        except Exception as e:
            print(f"❌ Domain resolution error: {e}")
            return None
    
    def _is_valid_ip(self, ip_str):
        """Check if string is valid IP"""
        try:
            import socket
            socket.inet_aton(ip_str)
            return True
        except:
            return False
    
    def _get_geo_data_direct(self, ip):
        """Get geolocation data untuk specific IP"""
        try:
            result = subprocess.run(
                ['curl', '-s', f"{self.geo_api_url}/{ip}"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception:
            pass
        return None
    
    def _get_geo_data(self, target):
        """Enhanced geolocation dengan IP resolution untuk domain"""
        # Jika target adalah IP, langsung query
        if self._is_valid_ip(target):
            print(f"🔍 Direct IP lookup: {target}")
            return self._get_geo_data_direct(target)
        
        # Jika target adalah domain, resolve ke best IP dulu
        print(f"🔍 Domain lookup: {target}")
        best_ip = self._resolve_domain_to_best_ip(target)
        
        if best_ip:
            print(f"🎯 Resolved domain {target} → {best_ip}")
            return self._get_geo_data_direct(best_ip)
        else:
            print(f"❌ Failed to resolve domain: {target}")
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