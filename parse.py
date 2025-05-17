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

import datetime

# The first 8192 bytes of the data do not relate to flights.
# The format of these bytes is not fully understood.
SKIP_BYTES = 8192
RECORD_SIZE = 16

def parse_positions(d):
    # stripped_data = d[SKIP_BYTES:]
    positions = []
    started = False
    for i in range(0, len(d), RECORD_SIZE):
        p = d[i:i+RECORD_SIZE]
        pos = parse_position(p)
        if started or pos['Data Type'] == 'DateTime':
            # print(pos)
            started = True
            positions.append(pos)
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
        return {'Data Type': 'DateTime',
                'Timestep': timestep,
                'MilMode': milmode,
                'TimeZone': timezone,
                'DateTime': datetime.datetime(year, month, day, hour, minute, second)
                }
    elif data_type == 'dddddd':
        distance = int.from_bytes(p[:3], 'big')
        return {'Data Type': 'Distance', 'Distance': distance}
    else:
        speed = int.from_bytes(p[0:3], 'big') / 1000
        altitude = int.from_bytes(p[3:6], 'big') / 10 # TODO: consider sign in top bit
        lon_polarity = "+" if p[6]==0 else "-"
        lon_degrees = p[7]
        lon_minutes = int.from_bytes(p[8:11], 'big')
        lat_polarity = "+" if p[11]==0 else "-"
        lat_degrees = p[12]
        lat_minutes = int.from_bytes(p[13:16], 'big')
        return({'Data Type': 'Position',
                'Speed': speed,
                'Altitude': altitude,
                'Longitude': float("{}{}.{:07d}".format(lon_polarity, lon_degrees, lon_minutes)),
                'Latitude': float("{}{}.{:07d}".format(lat_polarity, lat_degrees, lat_minutes))})

def dump_rec_type(data):
    prev = None
    i = 1
    for r in data:
        if r['Data Type'] == prev:
            i = i+1
        else:
            print('{} x {}'.format(prev, i))
            i = 1
        prev = r['Data Type']

def dump_recs(data):
    for r in data:
        if r['Data Type'] != 'NOP':
            print(r)

def split_flights(data):
    flights = []
    flight = []
    # Flights start with a DateTime record, accumulate until we get a DateTime record, or EOF
    for r in data:
        if r['Data Type'] == 'NOP':
            continue
        elif r['Data Type'] == 'DateTime':
            if len(flight) > 0:
                flights.append(flight)
            flight = []
        flight.append(r)
    flights.append(flight)
    return flights
