import struct
from typing import List, Optional, Dict

# Protocol Constants
START_BYTE  = 0xFE
END_BYTE    = 0xFF
ESCAPE_BYTE = 0xFD

# State Machine Constants
STATE_WAIT_START = 0
STATE_READ_DATA  = 1
STATE_ESCAPE     = 2

class TelemetryParser:
    """
    Handles the 'Byte Stuffing' protocol (SLIP-like) defined in the Arduino firmware.
    - START_BYTE (254) indicates start of frame.
    - END_BYTE (255) indicates end of frame.
    - ESCAPE_BYTE (253) escapes the next byte if it matches a control byte.
    """
    def __init__(self):
        self.state = STATE_WAIT_START
        self.buffer = bytearray()
        # Expected size: 15 floats * 4 bytes = 60 bytes
        self.EXPECTED_PAYLOAD_SIZE = 60 

    def feed(self, chunk: bytes) -> List[Dict[str, List[float]]]:
        """
        Feeds raw bytes into the parser.
        Returns a list of successfully decoded telemetry packets found in this chunk.
        """
        decoded_packets = []

        for byte_val in chunk:
            # --- STATE 1: WAITING FOR START ---
            if self.state == STATE_WAIT_START:
                if byte_val == START_BYTE:
                    self.buffer.clear()
                    self.state = STATE_READ_DATA
            
            # --- STATE 2: READING DATA ---
            elif self.state == STATE_READ_DATA:
                if byte_val == START_BYTE:
                    # Unexpected START, reset buffer (resync)
                    self.buffer.clear()
                elif byte_val == END_BYTE:
                    # Packet Complete, Try to Decode
                    packet = self._decode_payload(self.buffer)
                    if packet:
                        decoded_packets.append(packet)
                    self.state = STATE_WAIT_START
                elif byte_val == ESCAPE_BYTE:
                    self.state = STATE_ESCAPE
                else:
                    self.buffer.append(byte_val)

            # --- STATE 3: HANDLE ESCAPE ---
            elif self.state == STATE_ESCAPE:
                # Append the literal byte, regardless of what it is
                self.buffer.append(byte_val)
                self.state = STATE_READ_DATA

        return decoded_packets

    def _decode_payload(self, raw_data: bytearray) -> Optional[Dict[str, List[float]]]:
        """
        Unpacks the struct:
        float pt[7];
        float lc[3];
        float tc[5];
        Total: 15 floats (Little Endian)
        """
        if len(raw_data) != self.EXPECTED_PAYLOAD_SIZE:
            # Log specific error if needed, for now just ignore incomplete/corrupt frames
            return None

        try:
            # < = Little Endian, 15f = 15 floats
            floats = struct.unpack('<15f', raw_data)

            # Map based on struct layout
            # pt[0]..pt[6] (7 items)
            pt_values = list(floats[0:7])
            # lc[0]..lc[2] (3 items)
            lc_values = list(floats[7:10])
            # tc[0]..tc[4] (5 items)
            tc_values = list(floats[10:15])

            return {
                "pt": pt_values,
                "lc": lc_values,
                "tc": tc_values
            }
        except struct.error:
            return None