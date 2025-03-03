# Note: this is a rough and ready work-in-progress. It may not quite work right yet as 
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
# This code now throws away the endpoint and response identifier bytes every 64 bytes,
# and assumes all blocks are position records.

# TODO: Check speed and altitude units are correct
# TODO: identify track start/end
# TODO: check we're getting all the positions
# TODO: figure out what the deal is with correlating time records with position records
#       - seems to be too far between date records and unclear if consistenly receiving
#       a position at 1Hz

import struct

SKIP_BYTES = 8192
RECORD_SIZE = 16

def parse_positions(d):
    positions = []
    for i in range(0, len(d), RECORD_SIZE):
        p = d[i:i+RECORD_SIZE]
        positions.append(parse_position(p))
    return positions

def parse_position(p):
    data_type = p[:3].hex()
    
    if data_type == 'ffffff':
        return {'Data Type': 'NOP', 'Payload': p.hex()}
    elif data_type == 'eeeeee':
        timestep = p[0]
        milmode = p[1]
        timezone = p[2]
        year = 2000 + p[6]
        month = p[7]
        day = p[8]
        hour = p[9]
        minute = p[10]
        second = p[11]
        return {'Data Type': 'DateTime', 'Timestep': timestep, 'MilMode': milmode, 'TimeZone': timezone,
                'Date': f"{year}-{month:02}-{day:02}", 'Time': f"{hour:02}:{minute:02}:{second:02}"}
    elif data_type == 'dddddd':
        distance = int.from_bytes(p[:3], 'big')
        return {'Data Type': 'Distance', 'Distance': distance}
    else:
        speed = int.from_bytes(p[0:3], 'big')
        altitude = int.from_bytes(p[3:6], 'big') # TODO: consider sign
        lon_polarity = "+" if p[6]==0 else "-"
        lon_degrees = p[7]
        lon_minutes = int.from_bytes(p[8:11], 'big')
        lat_polarity = "+" if p[11]==0 else "-"
        lat_degrees = p[12]
        lat_minutes = int.from_bytes(p[13:16], 'big')
        return({'Data Type': 'Position', 'Speed': speed, 'Altitude': altitude,
                'Longitude': "{}{}.{}".format(lon_polarity, lon_degrees, lon_minutes),
                'Latitude': "{}{}.{}".format(lat_polarity, lat_degrees, lat_minutes)})

CHUNK_SIZE = 64
def strip_reponse_identifier(data):
    result = bytearray()
    for i in range(0, len(data), CHUNK_SIZE):
        chunk = data[i:i + CHUNK_SIZE]
        # if len(chunk) == CHUNK_SIZE:
        result.extend(chunk[2:])
        # else:
            # result.extend(chunk)
    return bytes(result)

def process_file(filename):
    with open(filename, 'rb') as f:
        data = f.read()
        # Strip first 2 bytes from every 64 bytes, i.e. all endpoint and response identifiers
        # Assumption is that all responses are Position responses
        data = strip_reponse_identifier(data)
        result = parse_positions(data[8192:])
        for r in result:
            if r['Data Type'] != 'NOP':
                print(r)

process_file('2025-03-03_output_data.bin')
