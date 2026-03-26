"""
Restaurant POS Desktop Application
Main entry point for the application
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PySide6.QtCore import QCoreApplication, Qt, QTimer
from PySide6.QtGui import QPixmap, QFont, QPalette, QColor

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database.connection import DatabaseManager
from ui.login_window import LoginWindow
from ui.main_window import MainWindow


class RestaurantPOSApp:
    """Main application class"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Restaurant POS")
        self.app.setOrganizationName("Restaurant POS")
        self.app.setApplicationVersion("1.0.0")
        
        # Set application style
        self.setup_style()
        
        # Initialize database
        self.init_database()
        
        # Show splash screen
        self.show_splash()
    
    def setup_style(self):
        """Setup application style"""
        try:
            # Suppress Qt warnings temporarily
            import os
            os.environ['QT_LOGGING_RULES'] = '*.warning=false'
            
            # Load stylesheet
            style_path = Path(__file__).parent / 'ui' / 'styles' / 'material_style.qss'
            if style_path.exists():
                with open(style_path, 'r', encoding='utf-8') as f:
                    stylesheet = f.read()
                    # Remove any potential problematic characters
                    stylesheet = stylesheet.replace('\ufeff', '')  # Remove BOM if present
                    self.app.setStyleSheet(stylesheet)
            
            # Set font
            font = QFont("Segoe UI", 10)
            self.app.setFont(font)
            
            print("✓ Estilos cargados correctamente")
        except Exception as e:
            print(f"⚠ Error al cargar estilos: {e}")
            # Continue without styles - app will still work
    
    def init_database(self):
        """Initialize database connection"""
        try:
            self.db = DatabaseManager()
            print("✓ Base de datos inicializada correctamente")
        except Exception as e:
            print(f"✗ Error al inicializar base de datos: {e}")
            QMessageBox.critical(
                None,
                "Error de Base de Datos",
                f"No se pudo inicializar la base de datos:\n{str(e)}\n\n"
                "La aplicación se cerrará."
            )
            sys.exit(1)
    
    def show_splash(self):
        """Show splash screen"""
        # Create splash screen
        splash_pix = QPixmap(400, 300)
        splash_pix.fill(QColor(255, 255, 255))
        
        splash = QSplashScreen(splash_pix, Qt.WindowType.WindowStaysOnTopHint)
        splash.setStyleSheet("""
            QSplashScreen {
                background-color: white;
                border-radius: 12px;
                border: 2px solid #FF6B35;
            }
        """)
        
        # Show splash for 1.5 seconds
        splash.show()
        
        # Process events to show splash
        self.app.processEvents()
        
        # Close splash after delay and show login
        QTimer.singleShot(1500, lambda: self.close_splash(splash))
    
    def close_splash(self, splash):
        """Close splash and show login"""
        splash.close()
        self.show_login()
    
    def show_login(self):
        """Show login window"""
        self.login_window = LoginWindow()
        
        if self.login_window.exec():
            # Login successful, show main window
            self.show_main_window()
        else:
            # Login cancelled or failed, exit
            sys.exit(0)
    
    def show_main_window(self):
        """Show main application window"""
        try:
            self.main_window = MainWindow()
            self.main_window.show()
        except Exception as e:
            print(f"✗ Error al mostrar ventana principal: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                None,
                "Error",
                f"No se pudo abrir la ventana principal:\n{str(e)}"
            )
            sys.exit(1)
    
    def run(self):
        """Run the application"""
        return self.app.exec()


def main():
    """Main entry point"""
    print("=" * 50)
    print("Restaurant POS Desktop Application")
    print("Versión 1.0.0")
    print("=" * 50)
    print()
    
    try:
        app = RestaurantPOSApp()
        sys.exit(app.run())
    except Exception as e:
        print(f"\n✗ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
