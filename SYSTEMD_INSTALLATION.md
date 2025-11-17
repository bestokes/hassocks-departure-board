# Systemd Service Installation Guide

## Prerequisites

- Linux system with systemd
- Python 3.9+ installed
- Application dependencies installed (`pip install -r requirements.txt`)

## Installation Steps

### 1. Prepare the Application Directory

```bash
# Create application directory
sudo mkdir -p /opt/hassocks-departure-board

# Copy application files
sudo cp -r app.py requirements.txt templates/ static/ polling_schedule.json /opt/hassocks-departure-board/

# Set proper ownership (service runs as user 'ben')
sudo chown -R ben:ben /opt/hassocks-departure-board
```

### 2. Install Python Dependencies

```bash
# Install dependencies in system Python or virtual environment
cd /opt/hassocks-departure-board
sudo pip3 install -r requirements.txt
```

### 3. Configure API Credentials

Create a credentials file (this should be kept secure):

```bash
sudo nano /opt/hassocks-departure-board/credentials.py
```

Add your API credentials:
```python
API_KEY = "your_actual_api_key_here"
API_URL = "your_actual_api_url_here"
```

Set secure permissions:
```bash
sudo chmod 600 /opt/hassocks-departure-board/credentials.py
sudo chown ben:ben /opt/hassocks-departure-board/credentials.py
```

### 4. Install Systemd Service

```bash
# Copy service file to systemd directory
sudo cp hassocks-departure-board.service /etc/systemd/system/

# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable hassocks-departure-board

# Start the service
sudo systemctl start hassocks-departure-board
```

### 5. Verify Installation

```bash
# Check service status
sudo systemctl status hassocks-departure-board

# View application logs
sudo journalctl -u hassocks-departure-board -f

# Test the web interface
curl http://localhost:5001/
```

## Service Management Commands

### Start/Stop/Restart Service
```bash
sudo systemctl start hassocks-departure-board
sudo systemctl stop hassocks-departure-board
sudo systemctl restart hassocks-departure-board
```

### Check Service Status
```bash
sudo systemctl status hassocks-departure-board
```

### View Logs
```bash
# Follow logs in real-time
sudo journalctl -u hassocks-departure-board -f

# View recent logs
sudo journalctl -u hassocks-departure-board --since "1 hour ago"

# View all logs
sudo journalctl -u hassocks-departure-board
```

### Enable/Disable Auto-start
```bash
sudo systemctl enable hassocks-departure-board
sudo systemctl disable hassocks-departure-board
```

## Troubleshooting

### Service Fails to Start
1. Check service status: `sudo systemctl status hassocks-departure-board`
2. View detailed logs: `sudo journalctl -u hassocks-departure-board`
3. Verify file permissions in `/opt/hassocks-departure-board/`
4. Check if credentials file exists and has correct format

### Application Not Accessible
1. Verify service is running: `sudo systemctl status hassocks-departure-board`
2. Check if port 5001 is bound: `sudo netstat -tlnp | grep 5001`
3. Verify firewall allows port 5001: `sudo ufw status`

### Permission Issues
1. Ensure application directory owned by nobody:nogroup
2. Check credentials file permissions (600)
3. Verify Python can access all required files

## Security Considerations

- The service runs as `nobody:nogroup` for minimal privileges
- Application files are isolated in `/opt/hassocks-departure-board/`
- Credentials file has restricted permissions (600)
- Systemd security features are enabled (NoNewPrivileges, PrivateTmp, etc.)
- Resource limits prevent memory exhaustion

## Monitoring

### Health Check
The application includes a health check endpoint:
```bash
curl http://localhost:5001/health
```

### System Resources
Monitor system resources:
```bash
# Check memory usage
sudo systemctl show hassocks-departure-board --property=MemoryCurrent

# Check CPU usage
top -p $(pgrep -f "python.*app.py")
```

## Updating the Application

When updating the application:

```bash
# Stop the service
sudo systemctl stop hassocks-departure-board

# Update application files
sudo cp -r app.py templates/ static/ /opt/hassocks-departure-board/

# Restart the service
sudo systemctl start hassocks-departure-board

# Verify it's working
sudo systemctl status hassocks-departure-board
```

## Uninstallation

To completely remove the service:

```bash
# Stop and disable the service
sudo systemctl stop hassocks-departure-board
sudo systemctl disable hassocks-departure-board

# Remove service file
sudo rm /etc/systemd/system/hassocks-departure-board.service

# Remove application files (optional)
sudo rm -rf /opt/hassocks-departure-board

# Reload systemd
sudo systemctl daemon-reload
