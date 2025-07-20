import os
import json
import re
import asyncio
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import threading
import tempfile
import subprocess
from dotenv import load_dotenv

# Import existing modules
from github_client import GitHubClient
from core import (
    deduplicate_accounts, sort_priority, ensure_ws_path_field,
    build_final_accounts, load_template, test_all_accounts
)
from extractor import extract_accounts_from_config
from converter import parse_link, inject_outbounds_to_template
from database import save_github_config, get_github_config, save_test_session, get_latest_test_session

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global variables to store session data
session_data = {
    'github_client': None,
    'all_accounts': [],
    'test_results': [],
    'final_config': None,
    'github_path': None,
    'github_sha': None,
    'custom_servers': None  # Store custom servers untuk config generation
}

MAX_CONCURRENT_TESTS = 5
TEMPLATE_FILE = "template.json"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/setup-github', methods=['POST'])
def setup_github():
    data = request.json
    token = data.get('token')
    owner = data.get('owner')
    repo = data.get('repo')
    
    if token and owner and repo:
        # Save to local database
        save_github_config(token, owner, repo)
        session_data['github_client'] = GitHubClient(token, owner, repo)
        return jsonify({'success': True, 'message': 'GitHub configured and saved locally'})
    else:
        return jsonify({'success': False, 'message': 'All fields are required'})

@app.route('/api/get-github-config')
def get_github_config_api():
    config = get_github_config()
    if config:
        # Also set up the client if config exists
        session_data['github_client'] = GitHubClient(config['token'], config['owner'], config['repo'])
        return jsonify({'success': True, 'config': {
            'owner': config['owner'],
            'repo': config['repo'],
            'configured': True
        }})
    else:
        return jsonify({'success': False, 'configured': False})

@app.route('/api/list-github-files')
def list_github_files():
    if not session_data['github_client']:
        return jsonify({'success': False, 'message': 'GitHub not configured'})
    
    files = session_data['github_client'].list_files_in_repo()
    json_files = [f for f in files if f.get('type') == 'file' and f.get('name', '').endswith('.json')]
    return jsonify({'success': True, 'files': json_files})

@app.route('/api/load-config', methods=['POST'])
def load_config():
    data = request.json
    source = data.get('source')  # 'local' or 'github'
    
    try:
        if source == 'github':
            file_path = data.get('file_path')
            if not session_data['github_client'] or not file_path:
                return jsonify({'success': False, 'message': 'GitHub client not configured or file path missing'})
            
            content, sha = session_data['github_client'].get_file(file_path)
            if content:
                config_data = json.loads(content)
                session_data['github_path'] = file_path
                session_data['github_sha'] = sha
            else:
                return jsonify({'success': False, 'message': 'Failed to load file from GitHub'})
        else:
            # Load from local template
            with open(TEMPLATE_FILE, 'r') as f:
                config_data = json.load(f)
            session_data['github_path'] = None
            session_data['github_sha'] = None
        
        # Extract existing accounts
        existing_accounts = extract_accounts_from_config(config_data)
        existing_accounts = ensure_ws_path_field(existing_accounts)
        session_data['all_accounts'] = existing_accounts if isinstance(existing_accounts, list) else []
        
        return jsonify({
            'success': True, 
            'message': f'Loaded {len(session_data["all_accounts"])} existing accounts',
            'account_count': len(session_data['all_accounts'])
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error loading config: {str(e)}'})

@app.route('/api/add-links-and-test', methods=['POST'])
def add_links_and_test():
    data = request.json
    links_text = data.get('links', '')
    
    # Extract VPN links using regex
    vpn_pattern = r"(?:vless|vmess|trojan|ss)://[^\s]+"
    found_links = re.findall(vpn_pattern, links_text)
    
    if not found_links:
        return jsonify({'success': False, 'message': 'No valid VPN links found'})
    
    # Parse each link
    accounts_from_links = []
    invalid_links = []
    
    for link in found_links:
        parsed = parse_link(link)
        if parsed:
            accounts_from_links.append(parsed)
        else:
            invalid_links.append(link[:50] + "..." if len(link) > 50 else link)
    
    if not accounts_from_links:
        return jsonify({'success': False, 'message': 'No valid accounts could be parsed from the links'})
    
    # Combine with existing accounts and deduplicate
    if not isinstance(session_data['all_accounts'], list):
        session_data['all_accounts'] = []
    
    all_accounts = session_data['all_accounts'] + accounts_from_links
    session_data['all_accounts'] = deduplicate_accounts(all_accounts)
    session_data['all_accounts'] = ensure_ws_path_field(session_data['all_accounts'])
    
    return jsonify({
        'success': True,
        'message': f'Added {len(accounts_from_links)} accounts. Ready to test!',
        'new_accounts': len(accounts_from_links),
        'total_accounts': len(session_data['all_accounts']),
        'invalid_links': invalid_links,
        'ready_to_test': True
    })

@socketio.on('start_testing')
def handle_start_testing():
    if not session_data['all_accounts']:
        emit('testing_error', {'message': 'No accounts to test'})
        return
    
    def run_tests():
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Initialize test results with better structure
            live_results = []
            for i, acc in enumerate(session_data['all_accounts']):
                result = {
                    "index": i,
                    "OriginalTag": acc.get("tag", f"Account-{i+1}"),
                    "OriginalAccount": acc,
                    "VpnType": acc.get("type", "unknown"),
                    "type": acc.get("type", "unknown"),  # Backup field
                    "server": acc.get("server", "-"),   # For tested IP fallback
                    "Country": "❓",
                    "Provider": "-",
                    "Tested IP": "-",
                    "Latency": -1,
                    "Jitter": -1,
                    "ICMP": "N/A",
                    "Status": "WAIT",
                    "Retry": 0
                }
                live_results.append(result)
            
            session_data['test_results'] = live_results
            
            # Emit initial results
            initial_data = {
                'results': [dict(res) for res in live_results],
                'total': len(live_results),
                'completed': 0
            }
            print(f"Emitting initial data: {len(live_results)} accounts")
            socketio.emit('testing_update', initial_data)
            
            # Create semaphore and run tests
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_TESTS)
            
            # Create a background task to emit updates
            def emit_periodic_updates():
                import time
                import threading
                
                def update_loop():
                    while True:
                        time.sleep(1)  # Update every second
                        
                        # Better status detection - exclude only WAIT status
                        completed = len([res for res in live_results if res["Status"] not in ["WAIT", "🔄", "🔁"]])
                        
                        try:
                            data_to_send = {
                                'results': [dict(res) for res in live_results],
                                'total': len(live_results),
                                'completed': completed
                            }
                            print(f"Emitting periodic update: {completed}/{len(live_results)} completed")
                            socketio.emit('testing_update', data_to_send)
                        except Exception as e:
                            print(f"Update emit error: {e}")
                            break
                        
                        # Check if testing is done - but continue a bit more to ensure final states
                        if completed >= len(live_results):
                            time.sleep(2)  # Give extra time for final status updates
                            break
                
                thread = threading.Thread(target=update_loop, daemon=True)
                thread.start()
                return thread
            
            # Start periodic updates
            update_thread = emit_periodic_updates()
            
            # Main async function to run tests
            async def run_all_tests():
                await test_all_accounts(session_data['all_accounts'], semaphore, live_results)
                
                # Count successful accounts
                successful_accounts = [res for res in live_results if res["Status"] == "✅"]
                
                # Sort by priority
                successful_accounts.sort(key=sort_priority)
                
                # Save test session to database
                session_id = save_test_session({
                    'results': live_results,
                    'successful': len(successful_accounts),
                    'total': len(live_results),
                    'timestamp': datetime.now().isoformat()
                })
                
                # Auto-generate configuration if we have successful accounts
                if successful_accounts:
                    try:
                        # DEPRECATED: session_data custom_servers tidak digunakan lagi
                        # Sekarang custom servers akan diambil dari frontend saat download
                        print(f"🔄 Auto-generate: Using original servers (custom servers will be applied on download)")
                        final_accounts_to_inject = build_final_accounts(successful_accounts)
                        fresh_template_data = load_template(TEMPLATE_FILE)
                        final_config_data = inject_outbounds_to_template(fresh_template_data, final_accounts_to_inject)
                        final_config_str = json.dumps(final_config_data, indent=2, ensure_ascii=False)
                        session_data['final_config'] = final_config_str
                        
                        socketio.emit('config_generated', {
                            'success': True,
                            'account_count': len(final_accounts_to_inject)
                        })
                    except Exception as e:
                        socketio.emit('config_generated', {
                            'success': False,
                            'error': str(e)
                        })
                
                # Force final status update to ensure all accounts show final state
                print(f"Final status update: forcing all pending accounts to complete")
                for res in live_results:
                    if res["Status"] in ["🔄", "🔁", "WAIT"]:
                        # If still in testing state, mark as failed or timeout
                        res["Status"] = "❌"
                        res["Latency"] = "Timeout"
                        print(f"Forcing completion for account {res.get('index', 'unknown')}: {res.get('VpnType', 'unknown')}")
                
                # Emit one final update with corrected statuses
                final_completed = len([res for res in live_results if res["Status"] not in ["WAIT", "🔄", "🔁"]])
                final_data = {
                    'results': [dict(res) for res in live_results],
                    'total': len(live_results),
                    'completed': final_completed
                }
                print(f"Emitting final testing update: {final_completed}/{len(live_results)} completed")
                socketio.emit('testing_update', final_data)
                
                # Emit final results
                socketio.emit('testing_complete', {
                    'results': live_results,
                    'successful': len(successful_accounts),
                    'total': len(live_results),
                    'session_id': session_id
                })
            
            # Run the async test function
            loop.run_until_complete(run_all_tests())
            
        except Exception as e:
            socketio.emit('testing_error', {'message': f'Testing failed: {str(e)}'})
        finally:
            loop.close()
    
    # Start testing in a separate thread
    testing_thread = threading.Thread(target=run_tests)
    testing_thread.daemon = True
    testing_thread.start()

@app.route('/api/generate-config', methods=['POST'])
def generate_config():
    if not session_data['test_results']:
        return jsonify({'success': False, 'message': 'No test results available'})
    
    try:
        data = request.json or {}
        custom_servers_input = data.get('custom_servers', '').strip()
        
        # Get successful accounts
        successful_accounts = [res for res in session_data['test_results'] if res["Status"] == "●"]
        
        if not successful_accounts:
            return jsonify({'success': False, 'message': 'No successful accounts to generate config'})
        
        # Sort by priority
        successful_accounts.sort(key=sort_priority)
        
        # Parse custom servers dari frontend
        custom_servers = None
        if custom_servers_input:
            custom_servers = parse_servers_input(custom_servers_input)
            print(f"🔄 Generate-config: Using custom servers from frontend = {custom_servers}")
        else:
            print(f"🔄 Generate-config: No custom servers, using original servers")
        
        # Build final accounts dengan optional server replacement
        final_accounts_to_inject = build_final_accounts(successful_accounts, custom_servers)
        
        # Load fresh template
        fresh_template_data = load_template(TEMPLATE_FILE)
        
        # Inject accounts
        final_config_data = inject_outbounds_to_template(fresh_template_data, final_accounts_to_inject)
        final_config_str = json.dumps(final_config_data, indent=2, ensure_ascii=False)
        
        session_data['final_config'] = final_config_str
        
        return jsonify({
            'success': True,
            'message': f'Generated config with {len(final_accounts_to_inject)} accounts' + 
                      (f' using {len(custom_servers)} custom servers' if custom_servers else ''),
            'account_count': len(final_accounts_to_inject),
            'custom_servers_used': len(custom_servers) if custom_servers else 0
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error generating config: {str(e)}'})

@app.route('/api/download-config')
def download_config():
    if not session_data['final_config']:
        return jsonify({'success': False, 'message': 'No config available for download'})
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    filename = f"VortexVpn-{timestamp}.json"
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        f.write(session_data['final_config'])
        temp_path = f.name
    
    return send_file(temp_path, as_attachment=True, download_name=filename, mimetype='application/json')

@app.route('/api/upload-to-github', methods=['POST'])
def upload_to_github():
    if not session_data['final_config']:
        return jsonify({'success': False, 'message': 'No config available for upload'})
    
    if not session_data['github_client']:
        return jsonify({'success': False, 'message': 'GitHub not configured'})
    
    data = request.json
    commit_message = data.get('commit_message', 'Update VPN configuration')
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    upload_path = session_data['github_path'] if session_data['github_path'] else f"VortexVpn-{timestamp}.json"
    
    try:
        result = session_data['github_client'].update_or_create_file(
            upload_path, 
            session_data['final_config'], 
            commit_message, 
            session_data['github_sha']
        )
        
        if result:
            return jsonify({'success': True, 'message': f'Successfully uploaded to {upload_path}'})
        else:
            return jsonify({'success': False, 'message': 'Failed to upload to GitHub'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error uploading to GitHub: {str(e)}'})

@app.route('/api/get-results')
def get_results():
    return jsonify({
        'results': session_data['test_results'],
        'total_accounts': len(session_data['all_accounts']),
        'has_config': session_data['final_config'] is not None
    })

@app.route('/api/get-accounts')
def get_accounts():
    """Get all parsed VPN accounts for server replacement"""
    return jsonify({
        'success': True,
        'accounts': session_data['all_accounts'],
        'total': len(session_data['all_accounts'])
    })

@app.route('/api/preview-server-replacement', methods=['POST'])
def preview_server_replacement():
    """Preview server replacement distribution"""
    try:
        data = request.json
        servers_input = data.get('servers', '').strip()
        
        if not servers_input:
            return jsonify({'success': False, 'message': 'No servers provided'})
        
        if not session_data['all_accounts']:
            return jsonify({'success': False, 'message': 'No VPN accounts found'})
        
        # Parse servers (comma or line separated)
        servers = parse_servers_input(servers_input)
        
        # Generate random distribution
        import random
        accounts = session_data['all_accounts'].copy()
        random.shuffle(accounts)
        
        # Calculate distribution
        accounts_per_server = len(accounts) // len(servers)
        remainder = len(accounts) % len(servers)
        
        distribution = {}
        start_idx = 0
        
        for i, server in enumerate(servers):
            # Add extra account to first few servers if there's remainder
            count = accounts_per_server + (1 if i < remainder else 0)
            end_idx = start_idx + count
            
            distribution[server] = accounts[start_idx:end_idx]
            start_idx = end_idx
        
        return jsonify({
            'success': True,
            'distribution': distribution,
            'total_accounts': len(accounts),
            'total_servers': len(servers)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Preview error: {str(e)}'})

@app.route('/api/apply-server-replacement', methods=['POST'])
def apply_server_replacement():
    """Store custom servers untuk config generation (tidak untuk testing)"""
    try:
        data = request.json
        servers_input = data.get('servers', '').strip()
        
        if not servers_input:
            return jsonify({'success': False, 'message': 'No servers provided'})
        
        if not session_data['all_accounts']:
            return jsonify({'success': False, 'message': 'No VPN accounts found'})
        
        # Parse servers
        servers = parse_servers_input(servers_input)
        
        # Store servers untuk config generation (BUKAN untuk testing)
        session_data['custom_servers'] = servers
        
        print(f"🔄 Stored {len(servers)} custom servers untuk config generation")
        print(f"🔄 Servers: {servers}")
        
        return jsonify({
            'success': True,
            'message': f'Custom servers stored for config generation. Will be applied to {len(session_data["all_accounts"])} accounts when generating final config.',
            'total_accounts': len(session_data['all_accounts']),
            'servers_stored': len(servers),
            'note': 'Servers will be applied only during config generation, not during testing.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Storage error: {str(e)}'})

def parse_servers_input(servers_input):
    """Parse server input (comma or line separated)"""
    if not servers_input:
        return []
    
    # Try comma separation first
    servers = [s.strip() for s in servers_input.split(',') if s.strip()]
    
    # If only one result, try line separation
    if len(servers) == 1:
        servers = [s.strip() for s in servers_input.split('\n') if s.strip()]
    
    return servers

if __name__ == '__main__':
    load_dotenv()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)