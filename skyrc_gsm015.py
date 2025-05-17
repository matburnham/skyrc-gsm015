import argparse

import skyrc_usb
import parse
import igc

def save_data(filename, data):
  with open(filename, 'wb') as f:
      f.write(data)

def load_data(filename):
  with open(filename, 'rb') as f:
      data = f.read()
  return data 

# Example usage:
#  $ skyrc-gsm015 -r -o output_data.bin
#  $ skyrc-gsm015 -i output_data.bin

def main():
    # TODO: make sufficent arguments mandatory
    # TODO: show usage if no args
    parser = argparse.ArgumentParser(description="SkyRC GSM015 USB Data Reader")
    parser.add_argument("-r", "--read", action="store_true", help="Read data from device")
    parser.add_argument("-o", "--output", help="Output file")
    parser.add_argument("-i", "--input", help="Input file")
    parser.add_argument("-e", "--export", help="Export IGC format file")
    args = parser.parse_args()

    if(args.read):
      dev, ep_out, ep_in = skyrc_usb.find_device_endpoints()
      skyrc_usb.request_data(ep_out)
      data = skyrc_usb.read_data_from_device(dev, ep_in)
      if(args.output):
        print("Storing data in {}".format(args.output));
        save_data(args.output, data)
    elif(args.input):
       data = load_data(args.input)
    
    # Parse the data and export IGC files
    positions = parse.parse_positions(data)
    flights = parse.split_flights(positions)
    print("Found {} flights".format(len(flights)))
    for flight in flights:
      r = flight[0]
      dt = r['DateTime'].strftime("%Y%m%d-%H%M%S")
      igc_export_filename = "{}-{}.igc".format(args.export, dt)
      if(args.export):
         export_written = " written to {}".format(igc_export_filename)
      print(" * Flight {} with {:5d} records{}".format(dt, len(flight), export_written))

      if(args.export):
          #print("Writing flight data to {}".format(igc_export_filename))
          igc.write_igc(igc_export_filename, flight)

if __name__ == "__main__":
    main()
