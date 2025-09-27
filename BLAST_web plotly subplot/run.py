import sys
import os

# --- Python sys.path debugging: ---
# print("--- top of run.py: sys.path ---")
# for p_idx, p_val in enumerate(sys.path):
#     print(f"{p_idx}: {p_val}")
# print("-------------------------------")
# Check if the current directory is what we expect
# print(f"--- CWD in run.py: {os.getcwd()} ---")
# --- End sys.path debugging ---

# Initialize logging first - fail fast if logging setup fails
try:
    from app.logging.logger_manager import get_logger_manager
    from app.logging.performance_monitor import get_performance_monitor
    from app.logging.freeze_detector import get_freeze_detector
    
    logger_manager = get_logger_manager()
    logger_manager.start_async_writer()
    app_logger = logger_manager.get_logger('app')
    
    # Start performance monitoring
    perf_monitor = get_performance_monitor()
    perf_monitor.start_monitoring()
    
    # Start freeze detection
    freeze_detector = get_freeze_detector()
    freeze_detector.start()
    
    app_logger.info("="*50)
    app_logger.info("BLAST Application Starting")
    app_logger.info(f"Working directory: {os.getcwd()}")
    app_logger.info(f"Python version: {sys.version}")
    app_logger.info("="*50)
except Exception as e:
    print(f"FATAL: Failed to initialize logging: {e}", file=sys.stderr)
    sys.exit(1)

from app import create_app

try:
    app = create_app()
    app_logger.info("Flask app created successfully")
except Exception as e:
    app_logger.error(f"Failed to create Flask app: {e}", exc_info=True)
    raise

if __name__ == '__main__':
    try:
        app_logger.info("Starting Flask development server")
        app.run(debug=True)
    except KeyboardInterrupt:
        app_logger.info("Application stopped by user")
        perf_monitor.stop_monitoring()
        freeze_detector.stop()
        logger_manager.stop_async_writer()
    except Exception as e:
        app_logger.error(f"Application crashed: {e}", exc_info=True)
        perf_monitor.stop_monitoring()
        freeze_detector.stop()
        logger_manager.stop_async_writer()
        raise 