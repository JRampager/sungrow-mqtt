#!/usr/bin/env python

# Copyright (c) 2021 Pontus Nordin
# Based on a copy of [thomasfa18's Sungrow Monitor script](https://github.com/thomasfa18/solar-sungrow)
# MQTT stuff stolen from all over the internet
# First try with python... not good looking and probably not efficient or totally failsafe
# First try with MQTT... probably not doing it right... lots of problem with publishing state after X number of messages, return code = 4
# Probably not handling network loop correct...
# Has been running fine for some time now 
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian
from pymodbus.client.sync import ModbusTcpClient
import paho.mqtt.client as mqtt
from pytz import timezone
import config
import json
import time
import datetime
import requests
import traceback
from threading import Thread

MIN_SIGNED   = -2147483648
MAX_UNSIGNED =  4294967295

print ("Timezone is %s" % config.timezone)
print ("The current time is %s" % (str(datetime.datetime.now(timezone(config.timezone))).partition('.')[0]))

# Modbus datatypes and register lengths
sungrow_moddatatype = {
  'S16':1,
  'U16':1,
  'S32':2,
  'U32':2,
  'STR16':8
  }

# Load the modbus map from file
print ("Load modbus mapping file")
modmap_file = "modbus-sungrow"
modmap = __import__(modmap_file)

# Load ModBusTCPClient
print ("Load ModbusTcpClient")
client = ModbusTcpClient(config.inverter_ip, 
                         timeout=config.timeout,
                         RetryOnEmpty=True,
                         retries=3,
						             ZeroMode=True,
                         port=config.inverter_port)

# Arrays, kept for conveniance although not needed since only one value is used
inverter = {}
power_gen = []
daily_power_yields = []
total_power_yields = []
internal_temperature = []

bus = json.loads(modmap.scan)

# MQTT Client connect
try: 
  print ("Connecting to MQTT server")
  mqtt_client = mqtt.Client('sungrow_data')
  mqtt_client.username_pw_set(config.mqtt_username,config.mqtt_password)
  mqtt_client.connect(config.mqtt_server, port=config.mqtt_port)
  mqtt_client.loop_start()
except:
  print ("Connection to MQTT server failed")

# Publish config data to MQTT Server  
if mqtt_client is not None:
  print ("Publishing MQTT config to Home Assistant")
  publish_result = mqtt_client.publish(
    topic="homeassistant/sensor/" + config.mqtt_devicename + "/" + config.mqtt_devicename + "TotalActivePower/config",
    payload='{"device_class":"power","name":"'
    + config.mqtt_devicename
    + 'TotalActivePower","state_topic":"sungrow/sensor/'
    + config.mqtt_devicename
    + '/state","unit_of_measurement":"W","value_template":"{{ value_json.totalactivepower}}","unique_id":"'
    + config.mqtt_devicename.lower()
    + '_sensor_totalactivepower","device":{"identifiers":["'
    + config.mqtt_devicename.lower()
    + '_sensor"],"name":"'
    + config.mqtt_devicename
    + 'Sensors","model":"Sungrow '
    + config.mqtt_devicename
    + '","manufacturer":"Sungrow"}, "icon":"mdi:solar-power"}',
    qos=1,
    retain=True,
  )
  print("MQTT config for TotalActivePower published with result = " + str(publish_result[0]))

  publish_result = mqtt_client.publish(
    topic="homeassistant/sensor/" + config.mqtt_devicename + "/" + config.mqtt_devicename + "DailyPowerYields/config",
    payload='{"device_class":"energy","name":"'
    + config.mqtt_devicename
    + 'DailyPowerYields","state_topic":"sungrow/sensor/'
    + config.mqtt_devicename
    + '/state","unit_of_measurement":"kWh","value_template":"{{ value_json.dailypoweryields}}","unique_id":"'
    + config.mqtt_devicename.lower()
    + '_sensor_dailypoweryields","device":{"identifiers":["'
    + config.mqtt_devicename.lower()
    + '_sensor"],"name":"'
    + config.mqtt_devicename
    + 'Sensors","model":"Sungrow '
    + config.mqtt_devicename
    + '","manufacturer":"Sungrow"}, "icon":"mdi:solar-power"}',
    qos=1,
    retain=True,
  )       
  print("MQTT config for DailyPowerYields published with result = " + str(publish_result[0]))

  publish_result = mqtt_client.publish(
    topic="homeassistant/sensor/" + config.mqtt_devicename + "/" + config.mqtt_devicename + "TotalPowerYields/config",
    payload='{"device_class":"energy","name":"'
    + config.mqtt_devicename
    + 'TotalPowerYields","state_topic":"sungrow/sensor/'
    + config.mqtt_devicename
    + '/state","unit_of_measurement":"kWh","value_template":"{{ value_json.totalpoweryields}}","unique_id":"'
    + config.mqtt_devicename.lower()
    + '_sensor_totalpoweryields","device":{"identifiers":["'
    + config.mqtt_devicename.lower()
    + '_sensor"],"name":"'
    + config.mqtt_devicename
    + 'Sensors","model":"Sungrow '
    + config.mqtt_devicename
    + '","manufacturer":"Sungrow"}, "icon":"mdi:solar-power"}',
    qos=1,
    retain=True,
  )       
  print("MQTT config for TotalPowerYields published with result = " + str(publish_result[0]))

  publish_result = mqtt_client.publish(
    topic="homeassistant/sensor/" + config.mqtt_devicename + "/" + config.mqtt_devicename + "InteralTemperature/config",
    payload='{"device_class":"temperature","name":"'
    + config.mqtt_devicename
    + 'InternalTemperature","state_topic":"sungrow/sensor/'
    + config.mqtt_devicename
    + '/state","unit_of_measurement":"C","value_template":"{{ value_json.internaltemperature}}","unique_id":"'
    + config.mqtt_devicename.lower()
    + '_sensor_internaltemperature","device":{"identifiers":["'
    + config.mqtt_devicename.lower()
    + '_sensor"],"name":"'
    + config.mqtt_devicename
    + 'Sensors","model":"Sungrow '
    + config.mqtt_devicename
    + '","manufacturer":"Sungrow"}, "icon":"mdi:thermometer"}',
    qos=1,
    retain=True,
  )     
  print("MQTT config for InternalTemperature published with result = " + str(publish_result[0]))

def update_sensors(totalactivepower, dailypoweryields, totalpoweryields, internaltemperature):
    # Build payload
    payload_str='{"totalactivepower":' + totalactivepower + ', "dailypoweryields":' + dailypoweryields + ', "totalpoweryields":' + totalpoweryields + ', "internaltemperature":' + internaltemperature + '}'
    # Publish
    publish_result = mqtt_client.publish(
      topic="sungrow/sensor/" + config.mqtt_devicename + "/state",
      payload=payload_str,
      qos=0,
      retain=False,
    )
    print("Message " + str(publish_result[1]) + " published with result = " + str(publish_result[0]) + " and payload = " + payload_str)
    # Return result
    return publish_result[0] 

def load_register(registers):
  from pymodbus.payload import BinaryPayloadDecoder
  from pymodbus.constants import Endian

  #moved connect to here so it reconnect after a failure
  client.connect()
  #iterate through each avaialble register in the modbus map
  for thisrow in registers:
    name = thisrow[0]
    startPos = thisrow[1]-1 #offset starPos by 1 as zeromode = true seems to do nothing for client
    data_type = thisrow[2]
    format = thisrow[3]
   
    #try and read but handle exception if fails
    try:
      received = client.read_input_registers(address=startPos,
                                             count=sungrow_moddatatype[data_type],
                                              unit=config.slave)
    except:
      thisdate = str(datetime.datetime.now(timezone(config.timezone))).partition('.')[0]
      thiserrormessage = thisdate + ': Connection not possible. Check settings or connection.'
      print (thiserrormessage)
      return
    
    # 32bit double word data is encoded in Endian.Little, all byte data is in Endian.Big
    if '32' in data_type:
        message = BinaryPayloadDecoder.fromRegisters(received.registers, byteorder=Endian.Big, wordorder=Endian.Little)
    else:
        message = BinaryPayloadDecoder.fromRegisters(received.registers, byteorder=Endian.Big, wordorder=Endian.Big)
    #decode correctly depending on the defined datatype in the modbus map
    if data_type == 'S32':
      interpreted = message.decode_32bit_int()
    elif data_type == 'U32':
      interpreted = message.decode_32bit_uint()
    elif data_type == 'U64':
      interpreted = message.decode_64bit_uint()
    elif data_type == 'STR16':
      interpreted = message.decode_string(16).rstrip('\x00')
    elif data_type == 'STR32':
      interpreted = message.decode_string(32).rstrip('\x00')
    elif data_type == 'S16':
      interpreted = message.decode_16bit_int()
    elif data_type == 'U16':
      interpreted = message.decode_16bit_uint()
    else: #if no data type is defined do raw interpretation of the delivered data
      interpreted = message.decode_16bit_uint()
    
    #check for "None" data before doing anything else
    if ((interpreted == MIN_SIGNED) or (interpreted == MAX_UNSIGNED)):
      displaydata = None
    else:
      #put the data with correct formatting into the data table
      if format == 'FIX3':
        displaydata = float(interpreted) / 1000
      elif format == 'FIX2':
        displaydata = float(interpreted) / 100
      elif format == 'FIX1':
        displaydata = float(interpreted) / 10
      else:
        displaydata = interpreted
    
    inverter[name] = displaydata
  
  #Add timestamp based on local time rather than inverter time
  inverter["0000 - Timestamp"] = str(datetime.datetime.now(timezone(config.timezone))).partition('.')[0]

# define a loop timer
def loop_timer(delay, task):
  next_time = time.time() + delay
  while True:
    time.sleep(max(0, next_time - time.time()))
    try:
      task()
    except Exception:
      traceback.print_exc()
      # in production code you might want to have this instead of course:
      # logger.exception("Problem while executing repetitive task.")
    # skip tasks if we are behind schedule:
    next_time += (time.time() - next_time) // delay * delay + delay

#loop counter
count=0
    
#main program loop
def main():
  global count
  try:
    global inverter
    inverter = {}
    # Read ModBus values
    print ("Load ModBusTCP registers")
    load_register(modmap.sungrow_registers)
    if len(inverter) > 0: #only continue if we get a successful read
      if inverter["5031 - Total active power"] <90000: #sometimes the modbus give back a weird value
        power_gen.append(inverter["5031 - Total active power"])
        print ("Total active power = %s" % inverter["5031 - Total active power"])
      else:
        print ("Didn't get a read for Active Power")
      if inverter["5003 - Daily power yields"] <9000: #sometimes the modbus give back a weird value
        daily_power_yields.append(inverter["5003 - Daily power yields"])
        print ("Daily power yields = %s" % inverter["5003 - Daily power yields"])
      else:
        print ("Didn't get a read for Daily power yields")
      if inverter["5144 - Total power yields"] <9000: #sometimes the modbus give back a weird value
        total_power_yields.append(inverter["5144 - Total power yields"])
        print ("Total power yields = %s" % inverter["5144 - Total power yields"])
      else:
        print ("Didn't get a read for Total power yields")   
      if inverter["5008 - Internal temperature"] <9000: #sometimes the modbus give back a weird value
        internal_temperature.append(inverter["5008 - Internal temperature"])
        print ("Internal temperature = %s" % inverter["5008 - Internal temperature"])
      else:
        print ("Didn't get a read for Internal temperature")              
    # we are done with the ModBusTCP connection for now so close it
    client.close()
    print (inverter)
    # Update MQTT state
    update_sensors(str(power_gen[0]), str(daily_power_yields[0]), str(total_power_yields[0]), str(internal_temperature[0]))

  except Exception as err:
    print ("[ERROR] %s" % err)
    client.close()
  #increment counter
  count+=1
  #wipe the arrays for next run
  del power_gen[:]
  del daily_power_yields[:]
  del total_power_yields[:]
  del internal_temperature[:]
  #sleep until next read
  print ("Read %d completed. Sleeping %ds...." % (count, config.scan_interval))

loop_timer(config.scan_interval, main)

