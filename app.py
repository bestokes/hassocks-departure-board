from flask import Flask, render_template, jsonify, send_from_directory
import requests
import json
import os
import threading
import time
from datetime import datetime
from screenshot_service import take_departure_board_screenshot

# Get API credentials from environment variables with fallbacks
API_KEY = os.environ.get('RAIL_API_KEY')
API_URL = os.environ.get('RAIL_API_URL')

app = Flask(__name__)

# Global variable to track last screenshot time
last_screenshot_time = 0
screenshot_interval = 30  # seconds

def fetch_train_data():
    """Fetch train data from the UK Rail API"""
    headers = {
        'x-apikey': API_KEY,
        'User-Agent': 'curl/7.64.1'
    }
    
    try:
        response = requests.get(API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def parse_train_services(data):
    """Parse the API response and extract train services"""
    if not data or 'trainServices' not in data:
        return []
    
    services = []
    for service in data['trainServices']:
        # Extract basic service information
        destination = service.get('destination', [{}])[0].get('locationName', 'Unknown')
        
        # Apply platform assignment rules
        platform = service.get('platform', '')
        if not platform:
            if 'Littlehampton' in destination:
                platform = '2'
            elif 'Brighton' in destination:
                platform = '2'
            elif 'London Victoria' in destination:
                platform = '1'
        
        service_info = {
            'std': service.get('std', ''),
            'etd': service.get('etd', ''),
            'platform': platform,
            'destination': destination,
            'operator': service.get('operator', ''),
            'is_cancelled': service.get('isCancelled', False),
            'cancel_reason': service.get('cancelReason', ''),
            'delay_reason': service.get('delayReason', '')
        }
        
        # Determine status
        if service_info['is_cancelled']:
            service_info['status'] = 'Cancelled'
            service_info['status_class'] = 'cancelled'
        elif service_info['etd'] == 'Delayed':
            service_info['status'] = 'Delayed'
            service_info['status_class'] = 'delayed'
        elif service_info['etd'] != 'On time' and service_info['etd'] != service_info['std']:
            service_info['status'] = service_info['etd']
            service_info['status_class'] = 'delayed'
        else:
            service_info['status'] = 'On time'
            service_info['status_class'] = 'on-time'
        
        services.append(service_info)
    
    return services

def group_by_platform(services):
    """Group services by platform and limit to 5 per platform"""
    platform_1 = []
    platform_2 = []
    no_platform = []
    
    for service in services:
        platform = service['platform']
        if platform == '1':
            platform_1.append(service)
        elif platform == '2':
            platform_2.append(service)
        else:
            no_platform.append(service)
    
    # Sort by scheduled departure time
    platform_1.sort(key=lambda x: x['std'])
    platform_2.sort(key=lambda x: x['std'])
    no_platform.sort(key=lambda x: x['std'])
    
    # Limit to 5 services per platform
    platform_1 = platform_1[:5]
    platform_2 = platform_2[:5]
    
    return platform_1, platform_2, no_platform

@app.route('/')
def index():
    """Main page showing the departure board"""
    return render_template('index.html')

def trigger_screenshot_if_needed():
    """Trigger screenshot if enough time has passed since the last one"""
    global last_screenshot_time
    current_time = time.time()
    
    if current_time - last_screenshot_time >= screenshot_interval:
        # Run screenshot in a separate thread to avoid blocking the API response
        def take_screenshot_async():
            try:
                take_departure_board_screenshot()
            except Exception as e:
                print(f"Screenshot failed: {e}")
        
        screenshot_thread = threading.Thread(target=take_screenshot_async)
        screenshot_thread.daemon = True
        screenshot_thread.start()
        
        last_screenshot_time = current_time
        print(f"Screenshot triggered at {datetime.now().strftime('%H:%M:%S')}")

@app.route('/api/departures')
def get_departures():
    """API endpoint to get departure data"""
    data = fetch_train_data()
    if not data:
        return jsonify({'error': 'Unable to fetch data'}), 500
    
    services = parse_train_services(data)
    platform_1, platform_2, no_platform = group_by_platform(services)
    
    # Trigger screenshot after successful data fetch
    trigger_screenshot_if_needed()
    
    return jsonify({
        'platform_1': platform_1,
        'platform_2': platform_2,
        'no_platform': no_platform,
        'last_updated': datetime.now().strftime('%H:%M:%S'),
        'station_name': data.get('locationName', 'Hassocks')
    })

@app.route('/image.png')
def serve_image():
    """Serve the latest screenshot"""
    return send_from_directory('static', 'image.png')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
