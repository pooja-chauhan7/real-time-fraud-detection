"""
Main Application - Simplified Version (No Kafka Required)
Real-Time Fraud Detection System

This version runs locally without Kafka/Spark.
Perfect for demonstration and testing.

Usage:
    python main.py
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.app import create_app
import config

def main():
    """Main entry point"""
    print("\n" + "=" * 60)
    print("   🛡️  REAL-TIME FRAUD DETECTION SYSTEM  🛡️")
    print("=" * 60)
    print(f"\n📊 System Configuration:")
    print(f"   • Transactions/second: {config.TRANSACTIONS_PER_SECOND}")
    print(f"   • Max transaction amount: ${config.MAX_TRANSACTION_AMOUNT}")
    print(f"\n🌐 Services:")
    print(f"   • API Server: http://localhost:{config.API_PORT}")
    print(f"   • Dashboard: Open frontend_dashboard/index.html in browser")
    print(f"\n📝 Quick Start:")
    print(f"   1. Open http://localhost:{config.API_PORT}/api/ to test API")
    print(f"   2. Open frontend_dashboard/index.html for the dashboard")
    print(f"\n⚠️  Note: The dashboard auto-starts the live transaction stream!")
    print(f"\n⚠️  Press Ctrl+C to stop\n")
    print("=" * 60 + "\n")
    
    # Create and run Flask app
    app = create_app()
    app.run(
        host=config.API_HOST, 
        port=config.API_PORT, 
        debug=config.API_DEBUG, 
        threaded=True
    )

if __name__ == "__main__":
    main()

