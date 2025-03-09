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

# TODO: check we're getting all the positions
# TODO: check timing works correctly if you add 1 second each position

import aerofiles
import datetime
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

CHUNK_SIZE = 64
def strip_reponse_identifier(data):
    result = bytearray()
    for i in range(0, len(data), CHUNK_SIZE):
        chunk = data[i:i + CHUNK_SIZE]
        result.extend(chunk[2:])
    return bytes(result)

def process_file(filename):
    with open(filename, 'rb') as f:
        data = f.read()
        # Strip first 2 bytes from every 64 bytes, i.e. all endpoint and response identifiers
        # Assumption is that all responses are Position responses
        data = strip_reponse_identifier(data)
        result = parse_positions(data[8192:])
    return result

def dump_rec_type(data):
    prev = None
    i = 0
    for r in data:
        if r['Data Type'] == prev:
            i=i+1
        else:
            print('{} x {}'.format(prev, i))
            i=0
        prev = r['Data Type']

def dump_recs(data):
    for r in data:
        if r['Data Type'] != 'NOP':
            print(r)

def split_flights(data):
    flights = []
    flight = []
    for r in data:
        if r['Data Type'] == 'DateTime':
            if len(flight) > 0:
                flights.append(flight)
            flight = []
        flight.append(r)
    flights.append(flight)
    return flights

def write_igc(filename, data):
    with open(filename, 'wb') as fp:
        writer = aerofiles.igc.Writer(fp)

        # Note: https://aerofiles.readthedocs.io/en/latest/guide/igc-writing.html suggests using FXA,
        # but we don't have accuracy data to use.       
        #writer.write_fix_extensions([('FXA', 3), ('SIU', 2), ('ENL', 3)])

        need_headers = True
        dt = None

        for r in data:
            if r['Data Type'] == 'DateTime':
                print('End', dt)
                dt = r['DateTime']
                print('Start', dt)

                # Write header as soon as we've got a date
                if(need_headers):
                    writer.write_headers({
                        'manufacturer_code': 'XXX',
                        'logger_id': 'YYY',
                        'date': dt.date(),
                        'logger_type': 'SKYRC,GSM-015',
                        'gps_receiver': 'Unknown',
                    })
                    need_headers = False

            elif r['Data Type'] == 'Position':
                if dt is None:
                    print('.')
                    continue
                writer.write_fix(
                    dt.time(),
                    latitude=r['Latitude'],
                    longitude=r['Longitude'],
                    valid=True,
                    gps_alt=int(r['Altitude']),
                )
                dt = dt + datetime.timedelta(seconds=1)
            elif r['Data Type'] == 'NOP':
                pass
            else:
                print(r)
        print('End', dt)

data = process_file('2025-03-09_output_data.bin')
flights = split_flights(data)
for flight in flights:
    r = flight[0]
    dt = r['DateTime'].strftime("%Y%m%d-%H%M%S")
    write_igc("output-{}.igc".format(dt), flight)
