# Note: this is a rough and ready work-in-progress. It doesn't quite work right yet as 
# the data isn't quite right.
#
# Stored data (from this code, but similar shows in Wireshark for the original software)
# seems to be like this:
#
# | Element| Length | Example | Notes |
# |-|-|-|-|
# | Endpoint | 1 byte | 0x02 | |
# | Reponse identifier | 1 byte | 'P' | |
# | First block | 14 bytes | | |
# | Second block | 16 bytes | | |
# | Third block | 16 bytes | | |
# | Fourth block | 16 bytes | | |
#
# Only the first block seems to have valid identifiers.
# I don't understand why there sometimes seems to be a further offset
# and it gerts out of sync, but not every time

import struct

SKIP_BYTES = 8192
RECORD_SIZE = 16

def parse_response(r):
    endpoint = r[0]
    response_identifier = chr(r[1])
    
    if endpoint not in [0x00, 0x01, 0x02, 0xff]:
        print("Unexpected endpoint 0x{:x}".format(endpoint))
        return None

    if response_identifier == 'N':  # Serial Number
        serial_number = r[2:18].hex()
        return {'Response': 'N', 'Serial Number': serial_number}

    elif response_identifier == 'G':  # Basic Data
        miles = r[2]
        frequency = r[3]
        timezone = r[4]
        firmware = struct.unpack('>H', r[6:8])[0]
        firmware_version = f"{firmware >> 8}.{firmware & 0xFF}"
        return {'Response': 'G', 'Miles': miles, 'Frequency': frequency, 'TimeZone': timezone, 'Firmware': firmware_version}

    elif response_identifier == 'P':  # Position
        data_type = r[2:5].hex()
        if data_type == 'ffffff':
            #return {'Response': 'P', 'Data Type': 'NOP', 'Payload': r[6:].hex()}
            return
        elif data_type == 'eeeeee':
            year = 2000 + r[8]
            month = r[9]
            day = r[10]
            hour = r[11]
            minute = r[12]
            second = r[13]
            return {'Response': 'P', 'Data Type': 'DateTime', 'Date': f"{year}-{month:02}-{day:02}", 'Time': f"{hour:02}:{minute:02}:{second:02}"}
        elif data_type == 'dddddd':
            distance = int.from_bytes(r[5:8], 'big')
            return {'Response': 'P', 'Data Type': 'Distance', 'Distance': distance}
        else:
            print(r)
            print(r.hex())
            speed = int.from_bytes(r[2:5], 'big')
            altitude = int.from_bytes(r[5:8], 'big') # TODO: consider sign
            lon_polarity = "+" if r[8]==0 else "-"
            lon_degrees = r[9]
            lon_minutes = int.from_bytes(r[10:13], 'big')
            lat_polarity = "+" if r[13]==0 else "-"
            lat_degrees = r[14]
            lat_minutes = int.from_bytes(r[15:18], 'big')
            print({'Response': 'P', 'Data Type': 'Position', 'Speed': speed, 'Altitude': altitude,
                   'Longitude': "{}{}.{}".format(lon_polarity, lon_degrees, lon_minutes),
                   'Latitude': "{}{}.{}".format(lat_polarity, lat_degrees, lat_minutes)})
            # exit(1)
            return {'Response': 'P', 'Data Type': 'Position', 'Speed': speed, 'Altitude': altitude, 'Longitude': (lon_polarity, lon_degrees, lon_minutes), 'Latitude': (lat_polarity, lat_degrees, lat_minutes)}

    elif response_identifier == 'E':  # Unknown
        return {'Response': 'E', 'Data': 'Unknown'}

    return None

def process_file(filename):
    with open(filename, 'rb') as f:
        #f.seek(SKIP_BYTES) # Skipped these before storing
        f.seek(0x3e00) # Skip to something with known location date
        i = 0
        while True:
            r = f.read(RECORD_SIZE)
            if not r:
                print("Failed to read record")
                exit(1)
            if len(r) < RECORD_SIZE:
                print("Insufficiently read {} bytes".format(len(r)))
                exit(1)
            print(r)
            result = parse_response(r)
            if result:
                print(result)
            i = i + 1
            if(i>10):
                break

process_file('output_data.bin')
