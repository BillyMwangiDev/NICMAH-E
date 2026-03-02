"""
Receipt Printer Utility for POS System
Supports ESC/POS compatible thermal receipt printers via USB, Serial, and Network
"""
import logging
import platform
from io import BytesIO
from decimal import Decimal

logger = logging.getLogger(__name__)

# ESC/POS Command Constants
ESC = b'\x1b'
GS = b'\x1d'
LF = b'\n'
HT = b'\t'

# Try to import optional printer libraries
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    logger.warning("pyserial not available. Serial printer support disabled.")

try:
    import socket
    SOCKET_AVAILABLE = True
except ImportError:
    SOCKET_AVAILABLE = False

try:
    import subprocess
    SUBPROCESS_AVAILABLE = True
except ImportError:
    SUBPROCESS_AVAILABLE = False


class ReceiptPrinter:
    """
    ESC/POS Receipt Printer Handler
    Supports USB (via system printing), Serial, and Network printers
    """
    
    def __init__(self, printer_type='system', printer_name=None, connection_params=None):
        """
        Initialize printer
        
        Args:
            printer_type: 'system', 'serial', 'network', or 'usb'
            printer_name: Printer name (for system printers) or device path
            connection_params: Dict with connection parameters (port, baudrate, host, etc.)
        """
        self.printer_type = printer_type
        self.printer_name = printer_name
        self.connection_params = connection_params or {}
        self.connection = None
        
    def connect(self):
        """Establish connection to printer"""
        try:
            if self.printer_type == 'serial' and SERIAL_AVAILABLE:
                port = self.connection_params.get('port', 'COM1' if platform.system() == 'Windows' else '/dev/ttyUSB0')
                baudrate = self.connection_params.get('baudrate', 9600)
                timeout = self.connection_params.get('timeout', 5)
                self.connection = serial.Serial(port, baudrate, timeout=timeout)
                logger.info(f"Connected to serial printer at {port}")
                return True
                
            elif self.printer_type == 'network' and SOCKET_AVAILABLE:
                host = self.connection_params.get('host', '192.168.1.100')
                port = self.connection_params.get('port', 9100)
                timeout = self.connection_params.get('timeout', 5)
                self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.connection.settimeout(timeout)
                self.connection.connect((host, port))
                logger.info(f"Connected to network printer at {host}:{port}")
                return True
                
            elif self.printer_type in ['system', 'usb']:
                # System/USB printers use OS print commands
                return True
                
            else:
                logger.error(f"Printer type {self.printer_type} not supported or required library missing")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to printer: {str(e)}")
            return False
    
    def disconnect(self):
        """Close connection to printer"""
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
            except Exception as e:
                logger.error(f"Error closing printer connection: {str(e)}")
    
    def _send_raw(self, data):
        """Send raw data to printer"""
        if self.printer_type in ['serial', 'network']:
            if self.connection:
                if isinstance(data, str):
                    data = data.encode('utf-8')
                self.connection.sendall(data)
        elif self.printer_type == 'system' and SUBPROCESS_AVAILABLE:
            # Use system print command
            self._print_via_system(data)
    
    def _print_via_system(self, data):
        """Print via system print command (for USB/System printers)"""
        try:
            system = platform.system()
            printer_name = self.printer_name or self._get_default_printer()
            
            if system == 'Windows':
                # Windows: Use print command
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as f:
                    f.write(data if isinstance(data, bytes) else data.encode('utf-8'))
                    temp_file = f.name
                
                try:
                    subprocess.run([
                        'print', f'/D:{printer_name}', temp_file
                    ], check=True, capture_output=True)
                finally:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        
            elif system in ['Linux', 'Darwin']:  # Linux or macOS
                # Use lpr or lp command
                cmd = ['lpr'] if system == 'Linux' else ['lp']
                if printer_name:
                    cmd.extend(['-P', printer_name])
                    
                process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate(input=data if isinstance(data, bytes) else data.encode('utf-8'))
                
                if process.returncode != 0:
                    raise Exception(f"Print command failed: {stderr.decode()}")
                    
        except Exception as e:
            logger.error(f"System print failed: {str(e)}")
            raise
    
    def _get_default_printer(self):
        """Get default system printer name"""
        try:
            system = platform.system()
            if system == 'Windows':
                result = subprocess.run(
                    ['wmic', 'printer', 'where', 'default=true', 'get', 'name'],
                    capture_output=True, text=True
                )
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip() and 'Name' not in line:
                        return line.strip()
            elif system == 'Linux':
                result = subprocess.run(['lpstat', '-d'], capture_output=True, text=True)
                if ':' in result.stdout:
                    return result.stdout.split(':')[1].strip()
            elif system == 'Darwin':  # macOS
                result = subprocess.run(['lpstat', '-d'], capture_output=True, text=True)
                if ':' in result.stdout:
                    return result.stdout.split(':')[1].strip()
        except Exception as e:
            logger.warning(f"Could not get default printer: {str(e)}")
        return None
    
    def initialize(self):
        """Initialize printer (reset, set defaults)"""
        commands = [
            ESC + b'@',  # Initialize printer
            ESC + b'a' + b'\x01',  # Center alignment
        ]
        for cmd in commands:
            self._send_raw(cmd)
    
    def set_font(self, font='a', bold=False, double_height=False, double_width=False):
        """Set font style"""
        # Font selection
        font_byte = ord(font) if isinstance(font, str) else font
        self._send_raw(ESC + b'!' + bytes([font_byte]))
        
        # Bold
        if bold:
            self._send_raw(ESC + b'E' + b'\x01')
        else:
            self._send_raw(ESC + b'E' + b'\x00')
        
        # Double height/width
        size_byte = 0
        if double_height:
            size_byte |= 0x01
        if double_width:
            size_byte |= 0x10
        if size_byte:
            self._send_raw(GS + b'!' + bytes([size_byte]))
    
    def align(self, alignment='left'):
        """Set text alignment (left, center, right)"""
        align_map = {
            'left': b'\x00',
            'center': b'\x01',
            'right': b'\x02'
        }
        align_byte = align_map.get(alignment, b'\x00')
        self._send_raw(ESC + b'a' + align_byte)
    
    def text(self, text, newline=True):
        """Print text"""
        if isinstance(text, str):
            text = text.encode('utf-8')
        self._send_raw(text)
        if newline:
            self._send_raw(LF)
    
    def line(self, char='-', width=48):
        """Print a line of characters"""
        self.text(char * width)
    
    def cut(self, partial=False):
        """Cut paper (partial=True for partial cut)"""
        if partial:
            self._send_raw(GS + b'V' + b'\x42' + b'\x00')  # Partial cut
        else:
            self._send_raw(GS + b'V' + b'\x41' + b'\x03')  # Full cut
    
    def open_cash_drawer(self):
        """Open cash drawer (if connected)"""
        # ESC p m t1 t2
        # m = 0 (pin 2), 1 (pin 5)
        # t1 = ON time (0-255) * 2ms
        # t2 = OFF time (0-255) * 2ms
        self._send_raw(ESC + b'p' + b'\x00' + b'\x19' + b'\xFF')
    
    def print_receipt(self, sale):
        """Print a formatted receipt for a sale"""
        try:
            if not self.connect():
                raise Exception("Failed to connect to printer")
            
            self.initialize()
            
            # Header
            self.align('center')
            self.set_font('a', bold=True, double_height=True, double_width=True)
            self.text("NICMAH")
            self.text("")  # Blank line
            
            self.set_font('a', bold=False, double_height=False, double_width=False)
            self.text("Receipt")
            self.line()
            self.text("")  # Blank line
            
            # Receipt Info
            self.align('left')
            self.set_font('a', bold=True)
            self.text(f"Receipt: {sale.receipt_number}")
            self.text(f"Sale: {sale.sale_number}")
            self.text(f"Date: {sale.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            self.text(f"Cashier: {sale.cashier.get_full_name()}")
            if sale.seller:
                self.text(f"Seller: {sale.seller.get_full_name()}")
            self.set_font('a', bold=False)
            self.line()
            self.text("")  # Blank line
            
            # Items
            self.align('left')
            self.set_font('a', bold=True)
            self.text(f"{'Item':<20} {'Qty':>4} {'Price':>10} {'Total':>12}")
            self.set_font('a', bold=False)
            self.line('-')
            
            for item in sale.items.all():
                product_name = item.product.name[:20]  # Truncate if too long
                qty = str(item.quantity)
                price = f"KSh {item.unit_price:.2f}"
                total = f"KSh {item.total_price:.2f}"
                self.text(f"{product_name:<20} {qty:>4} {price:>10} {total:>12}")
            
            self.line()
            self.text("")  # Blank line
            
            # Totals
            self.align('right')
            self.text(f"Subtotal: KSh {sale.subtotal:.2f}")
            if sale.tax_amount > 0:
                self.text(f"Tax: KSh {sale.tax_amount:.2f}")
            if sale.discount_amount > 0:
                self.text(f"Discount: KSh {sale.discount_amount:.2f}")
            self.set_font('a', bold=True, double_height=True)
            self.text(f"TOTAL: KSh {sale.total_amount:.2f}")
            self.set_font('a', bold=False, double_height=False)
            
            if sale.change_amount > 0:
                self.text(f"Change: KSh {sale.change_amount:.2f}")
            
            self.text("")  # Blank line
            self.line()
            
            # Footer
            self.align('center')
            self.text("Thank you for your business!")
            self.text("NICMAH")
            self.text("Quality Agricultural Solutions")
            self.text("")  # Blank line
            self.text("")  # Blank line
            
            # Cut paper
            self.cut(partial=True)
            
            self.disconnect()
            return True
            
        except Exception as e:
            logger.error(f"Error printing receipt: {str(e)}")
            if self.connection:
                self.disconnect()
            raise
    
    def test_print(self):
        """Print a test receipt"""
        try:
            if not self.connect():
                raise Exception("Failed to connect to printer")
            
            self.initialize()
            self.align('center')
            self.set_font('a', bold=True, double_height=True, double_width=True)
            self.text("NICMAH")
            self.text("PRINTER TEST")
            self.line()
            self.align('left')
            self.set_font('a', bold=False)
            self.text("This is a test print from the POS system.")
            self.text(f"Printer Type: {self.printer_type}")
            if self.printer_name:
                self.text(f"Printer: {self.printer_name}")
            self.line()
            self.align('center')
            self.text("If you can read this, your printer is working!")
            self.text("")  # Blank line
            self.cut(partial=True)
            
            self.disconnect()
            return True
            
        except Exception as e:
            logger.error(f"Error in test print: {str(e)}")
            if self.connection:
                self.disconnect()
            raise


def get_available_printers():
    """Get list of available system printers"""
    printers = []
    try:
        system = platform.system()
        if system == 'Windows':
            result = subprocess.run(
                ['wmic', 'printer', 'get', 'name'],
                capture_output=True, text=True
            )
            lines = result.stdout.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and line != 'Name':
                    printers.append(line)
        elif system in ['Linux', 'Darwin']:
            result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if line.startswith('printer'):
                    parts = line.split()
                    if len(parts) > 1:
                        printers.append(parts[1])
    except Exception as e:
        logger.warning(f"Could not get printer list: {str(e)}")
    
    return printers
