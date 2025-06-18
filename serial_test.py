import logging
from serial.tools import list_ports

def main():
    # Configure root logger to show debug/info messages
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger(__name__)

    logger.debug("Enumerating serial ports...")
    ports = list_ports.comports()

    if not ports:
        logger.info("No serial ports found.")
        return

    for port in ports:
        # port.device is like 'COM5' or '/dev/ttyUSB0'
        # port.description gives a human-readable name
        logger.info(f"{port.device} — {port.description}")

if __name__ == "__main__":
    main()