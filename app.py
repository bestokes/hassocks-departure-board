from flask import Flask, render_template, jsonify
import requests
import json
import os
import threading
import time
import logging
import logging.handlers
import signal
import sys
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED

# Import API credentials from credentials file
try:
    from credentials import API_KEY, API_URL
except ImportError:
    # Fallback to environment variables if credentials file is not available
    API_KEY = os.environ.get('RAIL_API_KEY')
    API_URL = os.environ.get('RAIL_API_URL')

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global variables for data management
current_data = None
last_data_update = 0
data_lock = threading.Lock()
scheduler = None

def fetch_train_data():
    """Fetch train data from the UK Rail API"""
    headers = {
        'x-apikey': API_KEY,
        'User-Agent': 'curl/7.64.1'
    }
    
    try:
        logger.info("Fetching train data from API")
        response = requests.get(API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info("Successfully fetched train data")
        return response.json()
    except requests.exceptions.RequestException as e:
        # Log the failure but don't retry - wait for next polling interval
        logger.error(f"API request failed: {e}")
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
            service_info['status_class'] = 'status-cancelled'
        elif service_info['etd'] == 'Delayed':
            service_info['status'] = 'Delayed'
            service_info['status_class'] = 'status-delayed'
        elif service_info['etd'] != 'On time' and service_info['etd'] != service_info['std']:
            service_info['status'] = service_info['etd']
            service_info['status_class'] = 'status-delayed'
        else:
            service_info['status'] = 'On time'
            service_info['status_class'] = 'status-on-time'
        
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

def scheduler_error_listener(event):
    """Handle scheduler errors"""
    if event.exception:
        logger.error(f"Scheduler job {event.job_id} failed: {event.exception}")
    else:
        logger.warning(f"Scheduler job {event.job_id} missed execution")

def update_data():
    """Fetch fresh data"""
    global current_data, last_data_update
    
    logger.info("Starting data update")
    
    # Fetch fresh data
    data = fetch_train_data()
    if data:
        with data_lock:
            current_data = data
            last_data_update = time.time()
        logger.info("Data updated successfully")
    else:
        logger.warning("Failed to fetch fresh data - will retry at next interval")

def start_background_scheduler():
    """Start the background scheduler for automatic updates using APScheduler"""
    global scheduler
    
    scheduler = BackgroundScheduler()
    
    # Schedule updates every 30 seconds
    scheduler.add_job(update_data, 'interval', seconds=30, id='data_update')
    
    # Add error listener
    scheduler.add_listener(scheduler_error_listener, EVENT_JOB_ERROR | EVENT_JOB_MISSED)
    
    # Start the scheduler
    scheduler.start()
    
    # Run initial update immediately
    update_data()
    
    logger.info("APScheduler started - data will update every 30 seconds")

@app.route('/')
def index():
    """Main page showing the departure board"""
    return render_template('index.html')

@app.route('/api/departures')
def get_departures():
    """API endpoint to get departure data"""
    global current_data, last_data_update
    
    with data_lock:
        if current_data is None:
            # If no data available yet, fetch it
            data = fetch_train_data()
            if data:
                current_data = data
                last_data_update = time.time()
            else:
                return jsonify({'error': 'Unable to fetch data'}), 500
    
    services = parse_train_services(current_data)
    platform_1, platform_2, no_platform = group_by_platform(services)
    
    return jsonify({
        'platform_1': platform_1,
        'platform_2': platform_2,
        'no_platform': no_platform,
        'last_updated': datetime.now().strftime('%H:%M:%S'),
        'station_name': current_data.get('locationName', 'Hassocks')
    })

@app.route('/api/polling-schedule')
def get_polling_schedule():
    """API endpoint to get the polling schedule"""
    try:
        with open('polling_schedule.json', 'r') as f:
            schedule_data = json.load(f)
        return jsonify(schedule_data)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # Fallback to default schedule if file is missing or invalid
        default_schedule = {
            "00": "5m", "01": "5m", "02": "5m", "03": "5m", "04": "2m", "05": "1m",
            "06": "30s", "07": "30s", "08": "30s", "09": "1m", "10": "1m", "11": "1m",
            "12": "1m", "13": "1m", "14": "1m", "15": "1m", "16": "30s", "17": "30s",
            "18": "30s", "19": "1m", "20": "2m", "21": "5m", "22": "5m", "23": "5m"
        }
        return jsonify(default_schedule)


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Shutting down gracefully...")
    if scheduler and scheduler.running:
        scheduler.shutdown()
    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == '__main__':
    # Start the background scheduler for automatic updates
    start_background_scheduler()
    
    # Start the Flask app in production mode
    app.run(debug=False, host='0.0.0.0', port=5001)
