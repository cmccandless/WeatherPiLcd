#!/usr/bin/python

import sys
import rpi_i2c_driver
from time import *
import datetime
import requests
import thread
import signal
import threading
import netifaces as ni

reqInProgress = False
req = None
lcd = None
go = True
lastUpdate = 0

#Weather Update Interval
updateInterval = 5 #minutes
updateInterval *= 60 #convert to seconds 

stateLength = 10 #seconds

#Settings
cityIds = {'Elkhart':4919987,
           'Longview':4707814}
cityid = cityIds['Elkhart']
appid = 'a7edc6f3527194353d5dcbcbbf679fe0'

#Constants
url = 'http://api.openweathermap.org/data/2.5/weather?id={}&appid={}&units=imperial'.format(cityid,appid)
mphToKnots = 0.868976

def displayImage(image, xpos=0):
  lcd.lcd_load_custom_chars(image)
  lcd.lcd_write(0x80+xpos)
  lcd.lcd_write_char(0)
  lcd.lcd_write_char(1)
  lcd.lcd_write_char(2)
  lcd.lcd_write(0xC0+xpos)
  lcd.lcd_write_char(3)
  lcd.lcd_write_char(4)
  lcd.lcd_write_char(5)
  return

def requestWeatherData():
  global req
  global lastUpdate
  global reqInProgress
  if reqInProgress:
    return
  reqInProgress = True
  try:
    req = requests.get(url)
    lastUpdate = time()
  except requests.exceptions.ConnectionError as e:
    print e
  finally:
    reqInProgress = False
  return

def scrollAdjustStr(str,scrollLength,scrollPos,spacing):
  if len(str)<=scrollLength:
    return str.ljust(scrollLength)
  shortStr = str
  pos = scrollPos % (len(str) + spacing)
  for i in range(0,spacing):
    shortStr = shortStr + ' '
  else:  
    shortStr = shortStr[pos:pos+scrollLength]
    return shortStr + str[:scrollLength-len(shortStr)]

def shutdown():
  global go
  go = None
  print("Shutting down all threads...")
  currentThread = threading.currentThread()
  for thread in threading.enumerate():
    if thread != currentThread:
      thread.join()
  print("All threads finished.")
  if lcd != None:
    print("Clearing LCD and turning it off...")
    lcd.lcd_clear()
    sleep(1)
    lcd.backlight(0)
    print("LCD backlight off.")
  return
  
def displayData():
  weatherDetails = None
  weatherMain = None
  wind = None
  clouds = 0
  weatherSys = None
  city = None
  image = None
  currentTemp = 0
  conditions = None
  humidity = None
  image = None

  state = 0
  lastStateChange = time()
  scrollPos = 0

  canDisplayWeather = 0

  while(go):
    currentTime = time()
    if currentTime - lastUpdate > updateInterval or not canDisplayWeather:
      thread.start_new_thread(requestWeatherData,())
      if req != None:
        try:
          json = req.json()
          canDisplayWeather = 1
          weatherDetails = json['weather'][0]
          weatherMain = json['main']
          wind = json['wind']
          clouds = int(json['clouds']['all'])
          weatherSys = json['sys']
          city = json['name']
  
          image = weatherDetails['icon']
          currentTemp = int(float(weatherMain['temp'])+0.5)
          conditions = weatherDetails['main']
          humidity = int(weatherMain['humidity'])
          windSpeed = round(float(wind['speed'])*mphToKnots,1)
          windDeg = int(float(wind['deg'])+0.5)
        except ValueError as e:
          print(e)
          state = 0
          canDisplayWeather = 0


    if state == 0:
      now = localtime()
      lcd.lcd_display_string(strftime('%H:%M:%S %Z',now),1)
      lcd.lcd_display_string(strftime("%a %b %d, %Y",now),2)
    elif state == 1:
      lcd.lcd_clear()
      scrollLength = 16
      scrollRate = 3
      spacing = scrollLength/2
      try:
        lcd.lcd_display_string(ni.ifaddresses('wlan0')[2][0]['addr'],1)
      except KeyError:
        errStr = 'wlan0 not connected'
        lcd.lcd_display_string(scrollAdjustStr(errStr,scrollLengthscrollPos*scrollRate,spacing),1)
      try:
        lcd.lcd_display_string(ni.ifaddresses('eth0')[2][0]['addr'],2)
      except KeyError:
        errStr = 'eth0 not connected'
        lcd.lcd_display_string(scrollAdjustStr(errStr,scrollLength,scrollPos*scrollRate,spacing),2)
    elif state == 2:
      scrollLength = 9
      scrollRate = 4
      spacing = scrollLength*2/3
      city = 'Rancho Santa Margarita'
      lcd.lcd_display_string(scrollAdjustStr(city,13,scrollPos*scrollRate,6),1)
      conditionStr = scrollAdjustStr(conditions+',',scrollLength,scrollPos*scrollRate,spacing)
      lcd.lcd_display_string(conditionStr,2)
      lcd.lcd_display_string_pos('{}{}'.format(currentTemp,chr(223)).rjust(4),2,scrollLength)
      displayImage(images[image],13)
    elif state == 3:
      lcd.lcd_display_string('Wind:{:4.1f}kn'.format(windSpeed),1)
      lcd.lcd_display_string_pos('{}{}'.format(windDeg,chr(223)),1,12)
      lcd.lcd_display_string('Clouds: {}%'.format(clouds),2)

    scrollPos += 1

    sleep(1)
    
    if currentTime - lastStateChange > stateLength:
      if canDisplayWeather:
        state = (state + 1) % 4
      else:
        state = (state + 1) % 2
      scrollPos = 0
      lcd.lcd_clear()
      lastStateChange = currentTime
      scrollPos = 0

  return


signal.signal(signal.SIGTERM, lambda num,fram: shutdown())
signal.signal(signal.SIGINT, lambda num,fram: shutdown())

lcd = rpi_i2c_driver.lcd()

if lcd == None:
  print("No I2C LCD detected!")
  sys.exit(0)

images = {
'01d' : [
  [0x00,0x00,0x06,0x04,0x00,0x00,0x05,0x0D],
  [0x00,0x04,0x0E,0x00,0x0E,0x1F,0x1F,0x1F],
  [0x00,0x00,0x0C,0x04,0x00,0x00,0x14,0x16],
  [0x05,0x00,0x00,0x04,0x06,0x00,0x00,0x00],
  [0x1F,0x1F,0x0E,0x00,0x0E,0x04,0x00,0x00],
  [0x14,0x00,0x00,0x04,0x0C,0x00,0x00,0x00],
],
'01n' : [
  [0x00,0x00,0x00,0x01,0x02,0x04,0x04,0x04],
  [0x00,0x00,0x1E,0x04,0x08,0x08,0x08,0x08],
  [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],
  [0x04,0x04,0x02,0x01,0x00,0x00,0x00,0x00],
  [0x06,0x03,0x00,0x00,0x1F,0x00,0x00,0x00],
  [0x00,0x18,0x08,0x10,0x00,0x00,0x00,0x00],
],
'02n' : [
  [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x03],
  [0x00,0x00,0x01,0x0C,0x09,0x03,0x17,0x18],
  [0x00,0x10,0x18,0x03,0x19,0x1C,0x1D,0x1D],
  [0x04,0x09,0x10,0x10,0x10,0x0F,0x00,0x00],
  [0x10,0x00,0x00,0x00,0x00,0x1F,0x00,0x00],
  [0x08,0x05,0x07,0x04,0x04,0x18,0x00,0x00],
],
'04n' : [
  [0x00,0x00,0x00,0x01,0x02,0x04,0x08,0x08],
  [0x00,0x00,0x03,0x14,0x08,0x10,0x00,0x00],
  [0x00,0x00,0x10,0x08,0x04,0x02,0x02,0x02],
  [0x08,0x07,0x00,0x00,0x00,0x00,0x00,0x00],
  [0x00,0x1F,0x00,0x00,0x00,0x00,0x00,0x00],
  [0x02,0x1C,0x00,0x00,0x00,0x00,0x00,0x00],
],
'10n' : [
  [0x00,0x00,0x00,0x01,0x02,0x04,0x08,0x08],
  [0x00,0x00,0x03,0x14,0x08,0x10,0x00,0x00],
  [0x00,0x00,0x10,0x08,0x04,0x02,0x02,0x02],
  [0x08,0x07,0x00,0x02,0x00,0x00,0x00,0x00],
  [0x00,0x1F,0x00,0x09,0x00,0x12,0x00,0x00],
  [0x02,0x1C,0x00,0x04,0x00,0x09,0x00,0x00],
],
'11n' : [
  [0x00,0x00,0x00,0x00,0x00,0x01,0x03,0x03],
  [0x00,0x00,0x0F,0x0F,0x1F,0x1F,0x1F,0x1F],
  [0x00,0x00,0x1C,0x18,0x10,0x00,0x18,0x18],
  [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],
  [0x0F,0x1F,0x1E,0x1C,0x18,0x00,0x00,0x00],
  [0x10,0x00,0x00,0x00,0x00,0x00,0x00,0x00],
],
'13n' : [
  [0x00,0x00,0x01,0x05,0x03,0x05,0x01,0x00],
  [0x00,0x00,0x00,0x08,0x10,0x0A,0x01,0x02],
  [0x00,0x00,0x00,0x00,0x10,0x14,0x18,0x14],
  [0x00,0x00,0x02,0x01,0x02,0x00,0x00,0x00],
  [0x00,0x10,0x14,0x18,0x14,0x10,0x00,0x00],
  [0x10,0x00,0x00,0x00,0x00,0x00,0x00,0x00],
],
'50n' : [
  [0x00,0x00,0x00,0x00,0x0E,0x11,0x00,0x0E],
  [0x00,0x00,0x00,0x00,0x07,0x18,0x00,0x07],
  [0x00,0x00,0x00,0x00,0x03,0x1C,0x00,0x03],
  [0x11,0x00,0x0E,0x11,0x00,0x00,0x00,0x00],
  [0x18,0x00,0x07,0x18,0x00,0x00,0x00,0x00],
  [0x1C,0x00,0x03,0x1C,0x00,0x00,0x00,0x00],
]
}

images['02d']=images['02n']
images['03d']=images['04n']
images['03n']=images['04n']
images['04d']=images['04n']
images['09d']=images['10n']
images['09n']=images['10n']
images['10d']=images['10n']
images['11d']=images['11n']
images['13d']=images['13n']
images['50d']=images['50n']

displayData()

