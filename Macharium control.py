from time import sleep,localtime,ticks_ms
from machine import Pin,I2C,RTC,Timer,ADC,reset,TouchPad,WDT
from ssd1306 import SSD1306_I2C
import onewire
from neopixel import NeoPixel
from dht import DHT11
import math
import ds18x20
import network
import socket
import _thread
import ntptime
import urequests
import secrets
#watchdog timer
wdt=WDT(timeout=60000)
#GUI output devices init
led=Pin(2,Pin.OUT)
led.on()
screenstate=[0,1]
i2c=I2C(0,sda=Pin(19),scl=Pin(18),freq=400000)
dsp=SSD1306_I2C(128,64,i2c)
dsp.fill(0) 
dsp.text("IMacharium",0,0,1)
dsp.text("Starting....",10,32,1)
dsp.show()
sleep(1)
#sensors init
dht=DHT11(Pin(5,Pin.OUT,Pin.PULL_DOWN))
ow=onewire.OneWire(Pin(23))
ds=ds18x20.DS18X20(ow)
rom=ds.scan()[0]  
soilsens=ADC(Pin(32))
LDR=ADC(Pin(35))
waterlvlSens=TouchPad(Pin(12))
#output periferies init   
fan=Pin(21,Pin.OUT)
pump=Pin(22,Pin.OUT)
fan.off()  
pump.off()
#GUI input init
clk=Pin(17,Pin.IN)
dt=Pin(16,Pin.IN)
sw=Pin(4,Pin.IN) 
backButton=Pin(3 ,Pin.IN,Pin.PULL_UP)
#neopixel init
pixlenght=30
pixList=list()
pixParams=[0,0,0,1,0,0,50]#currentmode,color,color2,rainbowsteps,whiteTemperature,Brightness mode, Auto brightness treshold
brightness=1
pix=NeoPixel(Pin(33),pixlenght)
pix_off=False
pix.fill((0,0,0))
pix.write()
#settings variables
wlvlTrh=400
minSoilMoisture=30
wateringDuration=10#s
AirCirculationDuration=5 #v minútach
lastAirCirculation=0
AirCirculationFreq=3#pocet vetrani za hodinu
maxTempi=25
#timers
waterTim=Timer(0)
fanTim=Timer(1)
pixTim=Timer(2)
DataTim=Timer(3)
#variables
lastMove=0
swTstart=0
sleep(2)
#Flags
WIFI_PUMPON=[False,1]#value,duration
#DND
DND=False
DND_act=True
DND_start=[22,0]
DND_stop=[7,0]

rtc=RTC()
dsp.fill(0)
dsp.text("IMacharium",0,0,1)
dsp.text("Connecting to",4,32,1) 
dsp.text("WIFI",36,48,1)
dsp.show()
sleep(1)
wifi=network.WLAN(network.STA_IF)
sleep(1)
wifi.active(True)
wifi.connect(secrets.SSID,secrets.PWD)
attempts=0
while wifi.isconnected()==False:
    if attempts>30:
        dsp.fill(0)
        dsp.text('Connection failed',2,32,1)
        dsp.text('Restarting...',4,48,1)
        dsp.show()
        sleep(3)
        reset()
    attempts+=1
    sleep(1)
    led.value(not led.value())
ip=wifi.ifconfig()[0]
dsp.fill(0)
dsp.text("IMacharium",0,0,1)
dsp.text("Connected!",10,22,1)
dsp.text("IP:",0,38,1)
dsp.text(str(ip),0,54,1)
led.on()
dsp.show()
sleep(5)
#setting time
print(ip)
ntptime.settime() 
#functions for data collection
def measure():
    global tempo,humo,tempi,light,soilmoist
    try:
        dht.measure()
        tempo=dht.temperature()
        humo=dht.humidity()
    except:
        tempo=0
        humo=0
    try:
        ds.convert_temp()
        sleep(0.5)
        tempi=ds.read_temp(rom)
    except:
        tempi=2  
    R2=4200#potentiometer resistance-connected in series with LDR
    val100=200#hodnota R pri intenzite 100
    light=int((val100*100)/((3.3-(LDR.read_uv()/10**6))/((LDR.read_uv()/10**6)/R2)))#hodnota svetla v rozsahu od 0-100
    #print(LDR.read_uv(),light)
    soilmoist=int(100-(soilsens.read_u16()/(65535/100)))#hodnota vlhkosti pôdy v rozsahu od 0-100
#fuction for OLED display UI
def drawscreen():
    global screenstate,tempi,tempo,humo,soilmoist,pixParams,brightness,minSoilMoisture,AirCirculationDuration, AirCirculationFreq, maxTempi,wlvlTrh,light
#home screen
    if screenstate[0]==0:
        if screenstate[1]>3:
            screenstate[1]=1
        if screenstate[1]<0:
            screenstate[1]=0
        if screenstate[1]==0:
            dsp.poweroff()
        elif screenstate[1]==1:
            dsp.fill(0)
            dsp.poweron()
            dsp.fill_rect(0,15,128,12,1)
            dsp.text("Lighting",2,16,0)
            dsp.text("Data",2,28,1)
            dsp.text("Settings",2,40,1)
        elif screenstate[1]==2:
            dsp.fill(0)
            dsp.poweron()
            dsp.fill_rect(0,27,128,12,1)
            dsp.text("Lighting",2,16,1)
            dsp.text("Data",2,28,0)
            dsp.text("Settings",2,40,1)
        elif screenstate[1]==3:
            dsp.fill(0)
            dsp.poweron()
            dsp.fill_rect(0,39,128,12,1)
            dsp.text("Lightning",2,16,1)
            dsp.text("Data",2,28,1)
            dsp.text("Settings",2,40,0)
        if screenstate[1]!=0:
            dtmTuple=rtc.datetime()
            dtm=f'{dtmTuple[4]}:{dtmTuple[5]}  {dtmTuple[2]}/{dtmTuple[1]}'
            dsp.text(dtm,0,0,1)
#lightning
    elif screenstate[0]==1:
        if pixParams[0]>4:
            pixParams[0]=-1
        elif pixParams[0]<-1:
            pixParams[0]=4
            
        if pixParams[5]>2:
            pixParams[5]=0
        elif pixParams[5]<0:
            pixParams[5]=2
        #brightness mode+values
        if pixParams[0]!=2 and pixParams[0]!=-1:
            a=0
            if screenstate[1]>3:
                screenstate[1]=0
            elif screenstate[1]<0:
                screenstate[1]=3
        elif pixParams[0]==-1:
            screenstate[1]==0
        else:
            a=12
            if screenstate[1]>4:
                screenstate[1]=0
            elif screenstate[1]<0:
                screenstate[1]=4 
        dsp.fill(0)
        if ((pixParams[0]!=2 and screenstate[1]!=0 and screenstate[1]!=2 and screenstate[1]!=3)or(pixParams[0]==2 and screenstate[1]!=0 and screenstate[1]!=3 and screenstate[1]!=4))and (pixParams[0]!=4 or pixParams[0]!=-1):
            dsp.text(f'Mode: {pixParams[0]}',2,16,1)
            dsp.text(f'Brigh. mode {pixParams[5]}',2,40+a,1)
            if pixParams[5]==0:
                dsp.text(f'Brightness {brightness}',2,52+a,1)
            else:
                dsp.text(f'Treshold {pixParams[6]}',2,52+a,1)
        elif screenstate[1]==0 and pixParams[0]!=4 and pixParams[0]!=-1:
            dsp.fill_rect(0,15,128,12,1)
            dsp.text(f'Mode: {pixParams[0]}',2,16,0)
            dsp.text(f'Brigh. mode {pixParams[5]}',2,40+a,1)
            if pixParams[5]==0:
                dsp.text(f'Brightness {brightness}',2,52+a,1)
            else:
                dsp.text(f'Treshold {pixParams[6]}',2,52+a,1)
        elif pixParams[0]!=4 and pixParams[0]!=-1:
            if pixParams[0]!=2:
                if screenstate[1]==2:
                    dsp.fill_rect(0,39,128,12,1)
                    dsp.text(f'Mode: {pixParams[0]}',2,16,1)
                    dsp.text(f'Brigh. mode {pixParams[5]}',2,40,0)
                    if pixParams[5]==0:
                        dsp.text(f'Brightness {brightness}',2,52,1)
                    else:
                        dsp.text(f'Treshold {pixParams[6]}',2,52,1)
                elif screenstate[1]==3:
                    dsp.fill_rect(0,51,128,12,1)
                    dsp.text(f'Mode: {pixParams[0]}',2,16,1)
                    dsp.text(f'Brigh. mode {pixParams[5]}',2,40,1)
                    if pixParams[5]==0:
                        dsp.text(f'Brightness {brightness}',2,52,0)
                    else:
                        dsp.text(f'Treshold {pixParams[6]}',2,52,0)
                        
            elif pixParams[0]==2:
                if screenstate[1]==3:
                    dsp.fill_rect(0,51,128,12,1)
                    dsp.text(f'Mode: {pixParams[0]}',2,16,1)
                    dsp.text(f'Brigh. mode {pixParams[5]}',2,52,0)
                elif screenstate[1]==4:
                    dsp.fill_rect(0,51,128,12,1)
                    dsp.text(f'Brigh. mode {pixParams[5]}',2,40,1)
                    if pixParams[5]==0:
                        dsp.text(f'Brightness {brightness}',2,52,0)
                    else:
                        dsp.text(f'Treshold {pixParams[6]}',2,52,0)
        elif pixParams[0]==-1:
                dsp.fill_rect(0,15,128,12,1)
                dsp.text(f'Mode: OFF',2,16,0)
            
        dtmTuple=rtc.datetime()
        dtm=f'{dtmTuple[4]}:{dtmTuple[5]}  {dtmTuple[2]}/{dtmTuple[1]}'
        dsp.text(dtm,0,0,1)
        
        if pixParams[0]==0:
            if screenstate[1]==1:
                dsp.fill_rect(0,27,128,12,1)
                dsp.text(f'Temp. {pixParams[4]}',2,28,0)
            else:
                dsp.text(f'Temp. {pixParams[4]}',2,28,1)
        elif pixParams[0]==1:
            if screenstate[1]==1:
                dsp.fill_rect(0,27,128,12,1)
                dsp.text(f'Color {pixParams[1]}',2,28,0)
            else:
                dsp.text(f'Color {pixParams[1]}',2,28,1)
        elif pixParams[0]==2:
            if screenstate[1]==1:
                dsp.fill_rect(0,27,128,12,1)
                dsp.text(f'Color1 {pixParams[1]}',2,28,0)
                dsp.text(f'Color2 {pixParams[2]}',2,40,1)
            elif screenstate[1]==2:
                dsp.fill_rect(0,39,128,12,1)
                dsp.text(f'Color1 {pixParams[1]}',2,28,1)
                dsp.text(f'Color2 {pixParams[2]}',2,40,0)
            else:
                if screenstate[1]!=4:
                    dsp.text(f'Color1 {pixParams[1]}',2,28,1)
                    dsp.text(f'Color2 {pixParams[2]}',2,40,1)
                elif screenstate[1]==4:
                    dsp.text(f'Color1 {pixParams[1]}',2,16,1)
                    dsp.text(f'Color2 {pixParams[2]}',2,28,1)         
        elif pixParams[0]==3:
            if screenstate[1]==1:
                dsp.fill_rect(0,27,128,12,1)
                dsp.text(f'Steps {pixParams[3]}',2,28,0)
            else:
                dsp.text(f'Steps {pixParams[3]}',2,28,1)
        elif pixParams[0]==4:
            dsp.fill_rect(0,15,128,12,1)
            dsp.text(f'Mode {pixParams[0]}',2,16,0)
            screenstate[1]==0
#data                
    elif screenstate[0]==2:
        if screenstate[1]>1:
            screenstate[1]=0
        if screenstate[1]<0:
            screenstate[1]=1
        dsp.fill(0)
        dtmTuple=rtc.datetime()
        dtm=f'{dtmTuple[4]}:{dtmTuple[5]}  {dtmTuple[2]}/{dtmTuple[1]}'
        dsp.text(dtm,0,0,1)
        if screenstate[1]==0:
            dsp.text(f'Temp. In:{tempi}C',2,16,1)
            dsp.text(f'Temp. Out:{tempo}C',2,28,1)
            dsp.text(f'Hum. Out:{humo}%',2,40,1)
            dsp.text(f'Soil. m:{soilmoist}',2,52,1)
        elif screenstate[1]==1:
            dsp.text(f'Temp. Out:{tempo}C',2,16,1)
            dsp.text(f'Hum. Out:{humo}%',2,28,1)
            dsp.text(f'Soil. m:{soilmoist}',2,40,1)
            dsp.text(f'Light int.{light}',2,52,1)
#settings            
    elif screenstate[0]==3:
        dsp.fill(0)
        dtmTuple=rtc.datetime()
        dtm=f'{dtmTuple[4]}:{dtmTuple[5]}  {dtmTuple[2]}/{dtmTuple[1]}'
        dsp.text(dtm,0,0,1)
        if screenstate[1]>4:
            screenstate[1]=0
        elif screenstate[1]<0:
            screenstate[1]=4
        if screenstate[1]==0:
            dsp.fill_rect(0,15,128,12,1)
            dsp.text(f'minSmoist: {minSoilMoisture}',1,16,0)
        elif screenstate[1]!=4:
            dsp.text(f'minSmoist: {minSoilMoisture}',1,16,1)
        if screenstate[1]==1:
            dsp.fill_rect(0,27,128,12,1)
            dsp.text(f'AirCirDur: {AirCirculationDuration}',1,28,0)
        elif screenstate[1]!=4:
            dsp.text(f'AirCirDur: {AirCirculationDuration}',1,28,1)
        if screenstate[1]==2:
            dsp.fill_rect(0,39,128,12,1)
            dsp.text(f'AirCirFq: {AirCirculationFreq}',1,40,0)
        elif screenstate[1]!=4:
            dsp.text(f'AirCirFq: {AirCirculationFreq}',1,40,1)
        if screenstate[1]==3:
            dsp.fill_rect(0,51,128,12,1)
            dsp.text(f'maxTempi: {maxTempi}',1,52,0)
        elif screenstate[1]!=4:
            dsp.text(f'maxTempi: {maxTempi}',1,52,1)
        if screenstate[1]==4:
            dsp.text(f'AirCirDur: {AirCirculationDuration}',1,16,1)
            dsp.text(f'AirCirFq: {AirCirculationFreq}',1,28,1)
            dsp.text(f'maxTempi: {maxTempi}',1,40,1)
            dsp.fill_rect(0,51,128,12,1)
            dsp.text(f'wlvlTrh: {wlvlTrh}',1,52,0)
            
    dsp.show()
#WEB UI functions
lightning_modes=['OFF','white','monocolor','bicolor','rainbow','auto']
def HTML():
    global pixParams,pump,fan, tempo,humo,tempi,light, soilmoist, brightness,msg,minSoilMoisture,wateringDuration,AirCirculationDuration,AirCirculationFreq,lastAirCirculation,maxTempi,wlvlTrh,DND_start,DND_stop
    DND_s=[str(DND_start[0]),str(DND_start[1])]
    DND_S=[str(DND_stop[0]),str(DND_stop[1])]
    if len(DND_s[0])==1:
           DND_s[0]='0'+DND_s[0]
    if len(DND_s[1])==1:
           DND_s[1]='0'+DND_s[1]
    if len(DND_S[0])==1:
           DND_S[0]='0'+DND_S[0]
    if len(DND_S[1])==1:
           DND_S[1]='0'+DND_S[1]
    page=f'''
<!doctype HTML>
<html>
    <head>
        <meta charset="utf-8">
        <meta content='width=device-width, initial-scale=1.0'>
        <title>iMacharium control</title>
    </head>
    <body>
         <h1 style='text-align: center; color: rgb(0,150,255); font-size: 40px;'>Welcome to iMacharium control centre</h1>
         </br><h2>{msg}</br>
         <div style='background-color: lightblue;'>
         <h2>Status:</h2>
         <p>Lightning mode: {lightning_modes[pixParams[0]+1]}</br>Pump: {pump.value()}</br>Fan: {fan.value()}</br>Temperature inside: {tempi}℃</br>Temperature outside: {tempo}℃</br>Humidity outside: {humo}%</br>Light intensity: {light}%</br>Soil moisture: {soilmoist}%</br>Water level capacitive sensor value: {waterlvlSens.read()}</br></p>
         </div>
         <div style='background-color: rgb(50,200,100);'>
         <h2>Lightning settings</h2>
         <form action='/lightning' method='POST'>
             <label for='lightningmode'>Lightning mode</label>
             <select id='lightningmode' name='lightningmode'>
             <option value='-1'>{lightning_modes[0]}</option>
             <option value='0'>{lightning_modes[1]}</option>
             <option value='1'>{lightning_modes[2]}</option>
             <option value='2'>{lightning_modes[3]}</option>
             <option value='3'>{lightning_modes[4]}</option>
             <option value='4'>{lightning_modes[5]}</option>
             </select></br>
             <label for='color1'>Color 1:</label>
             <input id='color1'name='color1' type='range' min='0' max='360' value='{pixParams[1]}' step='1'></br>
             <label for='color2'>Color 2:</label>
             <input id='color2'name='color2' type='range' min='0' max='360' value='{pixParams[2]}' step='1'></br>
             <label for='rainbowsteps'>Rainbow steps:</label>
             <input id='rainbowsteps'name='rainbowsteps' type='range' min='0' max='20' value='{pixParams[3]}' step='1'></br>
             <label for='whitetemp'>White temperature</label>
             <input id='whitetemp'name='whitetemp' type='range' min='0' max='255' value='{pixParams[4]}' step='1'></br>
             <label for='brightnessmode'>Brightness mode</label>
             <select id='brightnessmode' name='brightnessmode'>
             <option value='0'>Manual</option>
             <option value='1'>Auto-boolean</option>
             <option value='2'>Auto-dim</option>
             </select></br>
             <label for='brightnesstrh'>Automatic brightness theshold</label>
             <input id='brightnesstrh'name='brightnesstrh' type='range' min='0.25' max='0.8' value='{pixParams[6]}' step='0.05'></br>
             <label for='brightness'>Brightness</label>
             <input id='brightness'name='brightness' type='range' min='0' max='1' value='{brightness}' step='0.05'></br>
             <input type='submit'value='Apply settings'>
             </form>
             </div>
             </br>
             <div style='background-color: rgb(255,220,150);'>
             <h2>Plantcare system settings</h2>
             <form action='/settings' method='POST'>
             <label for='minSoilMoist'>Minimal soil moisture (%):</label>
             <input id='minSoilMoist' name='minSoilMoist' type='number' min='5' max='90' step='1' value='{minSoilMoisture}'></br>
             <label for='wateringDur'>Watering duration (s):</label>
             <input id='wateringDur' name='wateringDur' type='number' min='1' max='20' step='1' value='{wateringDuration}'></br>
             <label for='wlvlTrh'>Water level detector treshold:</label>
             <input id='wlvlTrh' name='wlvlTrh' type='number' min='1' max='1000' step='1' value='{wlvlTrh}'></br>
             <label for='AirCircDur'>Duration of the air circulation (min):</label>
             <input id='AirCircDur' name='AirCircDur' type='number' min='1' max='10' step='1' value='{AirCirculationDuration}'></br>
             <label for='AirCircFreq'>Air circulation frequency (per hour):</label>
             <input id='AirCircFreq' name='AirCircFreq' type='number' min='1' max='5' step='1' value='{AirCirculationFreq}'></br>
             <label for='maxTempi'>Maximal inside temperature (℃):</label>
             <input id='maxTempi' name='maxTempi' type='number' min='23' max='35' step='1' value='{maxTempi}'></br>
             <input type='submit'value='Apply settings'>
             </form>
             </div>
             <div style='background-color:rgb(100,200,100);'>
             <h2>DND settings</h2>
             <form action='/DND' method='POST'>
             <label for='DND_ON'>DND</label>
             <select id='DND_ON' name='DND_ON'>
             <option value='0'>OFF</option>
             <option value='1'>ON</option>
             </select></br>
             <label for='DND_start'>DND start time</label>
             <input type='time' id='DND_start' name='DND_start' min='15:00' max='23:59:59' value='{DND_s[0]}:{DND_s[1]}'></br>
             <label for='DND_stop'>DND end time</label>
             <input type='time' id='DND_stop' name='DND_stop' min='00:00' max='12:00' value='{DND_S[0]}:{DND_S[1]}'></br>
             <input type='submit' value='Apply DND settings'>
             </form>
             </div>
             <div style='background-color: rgb(0,100,100);'>
             <h2>One time pump run</h2>
             <form action='/pumpOn' method='POST'>
             <label for='waterDur'>One time watering duration (s):</label>
             <input type='number' value='1' min='1' max='10' step='1' name='waterDur' id='waterDur'>
             <input type='submit' value='Start watering'>
             </form>
             </div>
             <div style='background-color:gray;'>
             <h2>One time air circulation</h2>
             <form action='/fanOn' method='POST'>
             <label for='airCircDur'>One time air circulation duration (min):</label>
             <input type='number' id='airCircDur' name='airCircDur' min='1' max='10' step='1' value='1'>
             <input type='submit' value='Start air circulation'>
             </form>
             </div>
             </br>
             <form method='POST' action='allOff'>
             <input type='submit' value='All Off' style='font-size:20px;padding:10px;background-color:red;color:white; text-align:center; border:1px solid red;'>
             </form>
    </body>
</html>
'''
    return page.encode('utf-8')
run=True
msg='Ready!'
def start_server(IP):
    global run,server
    server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((IP,80))
    server.listen()
    server.settimeout(0.1)
    run=True
    _thread.start_new_thread(handle_client,())
    #handle_client()
def handle_client():
    global run,server,pixParams,pump,fan, tempo,humo,tempi,light, soilmoist, brightness,msg,minSoilMoisture,wateringDuration,AirCirculationDuration,AirCirculationFreq,lastAirCirculation,maxTempi,wlvlTrh,lastAirCirculation,pix_off,WIFI_PUMPON,DND_act,DND_start,DND_stop
    while run:
        try:
            conn, addr=server.accept()
            request=conn.recv(1024).decode('utf-8')
            #print(request)
            pumpon=False
            wdur=0
            if request[0:3]=='GET':
                msg='Ready!'
                conn.send(HTML())
                conn.close()
            elif request.split(' HTTP/1.1')[0]=='POST /lightning':
                data=request.split('\r\n\r\n')[-1]
                data=data.split('&')
                params=dict()
                for param in data:
                    param=param.split('=')
                    params.update({param[0]:param[1]})
                pixParams[0]=int(params['lightningmode'])
                pixParams[1]=int(params['color1'])
                pixParams[2]=int(params['color2'])
                pixParams[3]=int(params['rainbowsteps'])
                pixParams[4]=int(params['whitetemp'])
                pixParams[5]=int(params['brightnessmode'])
                pixParams[6]=float(params['brightnesstrh'])
                brightness=float(params['brightness'])
                msg='Lighning changes applied succesfully!'
                conn.send(HTML())
                conn.close()
            elif request.split(' HTTP/1.1')[0]=='POST /settings':
                data=request.split('\r\n\r\n')[1]
                data=data.split('&')
                params=dict()
                for param in data:
                    param=param.split('=')
                    params.update({param[0]:int(param[1])})
                #print(params)
                minSoilMoisture=params['minSoilMoist']
                wateringDuration=params['wateringDur']
                wlvlTrh=params['wlvlTrh']
                AirCirculationDuration=params['AirCircDur']
                AirCirculationFreq=params['AirCircFreq']
                maxTempi=params['maxTempi']
                msg='Settings changes applied succesfully!'
                conn.send(HTML())
                conn.close()
            elif request.split(' HTTP/1.1')[0]=='POST /DND':
                data=request.split('\r\n\r\n')[1]
                data=data.split('&')
                #print(data)
                DND_act=bool(data[0].split('=')[1])
                tm=data[1].split('=')[1]
                tm=tm.split('%3A')
                #print(tm)
                DND_start=[int(tm[0]),int(tm[1])]
                tm=data[2].split('=')[1]
                tm=tm.split('%3A')
                DND_stop=[int(tm[0]),int(tm[1])]
                msg='DND settings changes applied succesfully'
                conn.send(HTML())
                conn.close()
            elif request.split(' HTTP/1.1')[0]=='POST /pumpOn':
                data=request.split('\r\n\r\n')[1]
                data=data.split('=')
                if data[0]=='waterDur':   
                    if pump.value()==0 and waterlvlSens.read()<=wlvlTrh and fan.value()==0:
                        pix_off=True
                        updatePix()
                        msg='Watering started succesfully!'
                        WIFI_PUMPON=[True,(int(data[1])*1000)]
                        conn.send(HTML())
                        conn.close()
                        print('WATERING STARTED')
                    elif waterlvlSens.read()>wlvlTrh:
                        dsp.text('H2O',90,0,1)
                        dsp.show()
                        msg='Could not perform action beacuse of low water level'
                        conn.send(HTML())
                        conn.close()
                    elif pump.value()==1:
                        msg='Pump is already on'
                        conn.send(HTML())
                        conn.close()
                    elif fan.value()==1:
                        msg='Fan is on, cannot turn on pump at the same time'
                        conn.send(HTML())
                        conn.close()
                else:
                    msg='Error-no data'
                    conn.send(HTML())
                    conn.close()
            elif request.split(' HTTP/1.1')[0]=='POST /fanOn':
                data=request.split('\r\n\r\n')[1]
                print(data)
                data=data.split('=')
                if data[0]=='airCircDur':
                    if fan.value()==0 and pump.value()==0:
                        pix_off=True
                        updatePix()
                        fan.on()
                        lastAirCiculation=ticks_ms()
                        fanTim.init(period=int(data[1])*60000,mode=Timer.ONE_SHOT,callback=fanOff)
                        msg='Air circulation has started succesfully!'
                        print('AIR CIRCULATION HAS STARTED')
                    elif fan.value()==1:
                        msg='Fan is already on'
                    elif pump.value()==1:
                        msg='Pump is on, cannot turn on fan at the same time'
                    conn.send(HTML())
                    conn.close()
                else:
                    msg='Error-no data'
                    conn.send(HTML())
                    conn.close()
            elif request.split(' HTTP/1.1')[0]=='POST /allOff':
                if fan.value() and pump.value():
                    fan.off()
                    pump.off()
                    msg='Fan and pump turned off'
                if fan.value():
                    fan.off()
                    msg='Fan turned off succesfully'
                elif pump.value():
                    pump.off()
                    msg='Pump turned off succesfully'
                else:
                    msg=' Everything is already off'
                conn.send(HTML())
                conn.close()
        except OSError:
            pass
#thingpreak data upload-not working
def uplData(t):
    global tempi, tempo, humo, light, soilmoist
    #print('starting upoload')
    URL='http://api.thingspeak.com/update?api_key={}&field1={}&field2={}&field3={}&field4={}&field5={}&field6={}&field7={}&field8={}'.format(secrets.API,tempo,humo,tempi,soilmoist,light,pump.value(),fan.value(),waterlvlSens.read())
    #print(URL)
    response=urequests.get(URL)
    #print(response.status_code)
    response.close()
    #print('uploaded data')
DataTim.init(mode=Timer.PERIODIC, period=600000, callback=uplData)
#neopixel patterns functions
def HSV2RGB(deg):
    global brightness
    m=1/60
    if deg>=0 and deg<60:
        R=1
        G=0
        B=m*deg
    if deg>=60 and deg<120:
        R=1-m*(deg-60)
        G=0
        B=1
    if deg>=120 and deg<180:
        R=0
        G=m*(deg-120)
        B=1
    if deg>=180 and deg<240:
        R=0
        G=1
        B=1-m*(deg-180)
    if deg>=240 and deg<300:
        R=m*(deg-240)
        G=1
        B=0
    if deg>=300 and deg<360:
        R=1
        G=1-m*(deg-300)
        B=0
    myColor=(int(R*255*brightness),int(G*255*brightness),int(B*255*brightness))
    return myColor
def pixUpdateBrightness(mode,treshold):
    global light,brightness
    if mode==1:
        if light>treshold:
            brightness=0
        else:
            brightness=1
    if mode==2:
        if light>treshold:
            brightness=0
        else:
            brightness=0.1+((light/treshold)*0.9)
def pixfill(color):
    global pixlenght,pix
    #for i in range(0,pixlenght):
        #pix[i]=HSV2RGB(color)
        #pix.write()
        #sleep(0.1)
    pix.fill(HSV2RGB(color))
    pix.write()
def pixbicolor(color1,color2):
    global pix,pixlength
    for i in range(pixlenght):
        if i%2==0:
            pix[i]=HSV2RGB(color1)
        else:
            pix[i]=HSV2RGB(color2)
    pix.write()
def pixDynamicRainbowInit():
    global pixlenght
    global pixList
    pixList=[hue*int(360/pixlenght) for hue in range(pixlenght)]
def pixDynamicRainbow(step):
    global pixList,pix
    #print('dynamic rainbow')
    for i in range(len(pixList)):
        pixList[i]+=step
        if pixList[i]>=360:
            pixList[i]-=360
        pix[i]=HSV2RGB(pixList[i])
    pix.write()
def pixWhite(temp):
    global pix
    pix.fill((int(255*brightness),int(255*brightness),int((255-temp)*brightness)))
    pix.write()
def pixAuto():
    brght=math.sin((100-light)*(0.031415/2))
    pix.fill((int(255*brght),0,int(255*brght)))
    pix.write()
def updatePix():
    global pixParams,brightness,pix,pix_off
    if brightness>1:
        brightness=1
    if brightness<0:
        brightness=0
    if pixParams[1]>360:
        pixParams[1]-=360
    elif pixParams[1]<0:
        pixParams[1]+=360
    if pixParams[2]>360:
        pixParams[2]-=360
    elif pixParams[2]<0:
        pixParams[2]+=360
    if pixParams[3]>20:
        pixParams[3]-=20
    elif pixParams[3]<0:
        pixParams[3]+=20
    if pixParams[4]>255:
        pixParams[4]-=255
    elif pixParams[4]<0:
        pixParams[4]+=255
    if pixParams[5]>2:
        pixParams[5]==0
    elif pixParams[5]<0:
        pixParams[5]==2
    if pixParams[6]>100:
        pixParams[6]-=100
    elif pixParams[6]<0:
        pixParams[6]+=100
        
    pixUpdateBrightness(pixParams[5],pixParams[6])
    
    if pixParams[0]>4:
        pixParams[0]==0
    elif pixParams[0]<-1:
        pixParams[0]=4
    if pix_off or pixParams[0]==-1:
        pix.fill((0,0,0))
        pix.write()
    elif pixParams[0]==0:
        pixWhite(pixParams[4])
    elif pixParams[0]==1:
        pixfill(pixParams[1])
    elif pixParams[0]==2:
        pixbicolor(pixParams[1],pixParams[2])
    elif pixParams[0]==3:
        pixDynamicRainbow(pixParams[3])
    elif pixParams[0]==4:
        pixAuto()
#UI input IRQ handlers
def encoderRotation(obj):
    global screenstate,brightness,pixParams,maxTempi,AirCirculationDuration, AirCirculationFreq, minSoilMoisture, lastMove, wlvlTrh
    if ticks_ms()-lastMove>=100:
        lastMove=ticks_ms()
        print(sw.value())
        if sw.value()==1:
            if dt.value()==0:
                screenstate[1]-=1
                print('A')
            else:
                screenstate[1]+=1
                print('a')
        else:
            if screenstate[0]==1:
                if screenstate[1]==0:
                    if dt.value()==1:
                        pixParams[0]+=1
                    else:
                        pixParams[0]-=1
                if pixParams[0]==0 and screenstate[1]==1:
                    if dt.value()==1:
                        pixParams[4]+=5
                    else:
                        pixParams[4]-=5
                elif pixParams[0]==1 and screenstate[1]==1:
                    if dt.value()==1:
                        pixParams[1]+=2
                    else:
                        pixParams[1]-=2
                elif pixParams[0]==2:
                    if screenstate[1]==1:
                        if dt.value()==1:
                            pixParams[1]+=2
                        else:
                            pixParams[1]-=2
                    if screenstate[1]==2:
                        if dt.value()==1:
                            pixParams[2]+=2
                        else:
                            pixParams[2]-=2
                    if screenstate[1]==3:
                        if dt.value()==1:
                            pixParams[5]+=1
                        else:
                            pixParams[5]-=1
                    if screenstate[1]==4:
                        if pixParams[5]==0:
                            if dt.value()==1:
                                brightness+=0.05
                            else:
                                brightness-=0.05
                        else:
                            if dt.value()==1:
                                pixParams[6]+=2
                            else:
                                pixParams[6]-=2
                        
                elif pixParams[0]==3 and screenstate[1]==1:
                    if dt.value()==1:
                        pixParams[3]+=1
                    else:
                        pixParams[3]-=1
                    pixDynamicRainbowInit()
                elif pixParams[0]!=2 and screenstate[1]==3:
                    if pixParams[5]==0:
                        if dt.value()==1:
                            brightness+=0.05
                        else:
                            brightness-=0.05
                    else:
                        if dt.value()==1:
                            pixParams[6]+=2
                        else:
                            pixParams[6]-=2
                elif pixParams[0]!=2 and screenstate[1]==2:
                    if dt.value()==1:
                        pixParams[5]+=1
                    else:
                        pixParams[5]-=1
                updatePix()
            elif screenstate[0]==3:
                if screenstate[1]==0:
                    if dt.value()==1:
                        minSoilMoisture+=2
                    else:
                        minSoilMoisture-=2
                    if minSoilMoisture>70:
                        minSoilMoisture=5
                    if minSoilMoisture<5:
                        minSoilMoisture=70
                elif screenstate[1]==1:
                    if dt.value()==1:
                        AirCirculationDuration+=1
                    else:
                        AirCirculationDuration-=1
                    if AirCirculationDuration>7:
                        AirCirculationDuration=1
                    if AirCirculationDuration<0:
                        AirCirculationDuration=7
                elif screenstate[1]==2:
                    if dt.value()==1:
                        AirCirculationFreq+=1
                    else:
                        AirCirculationFreq-=1
                    if AirCirculationFreq>5:
                        AirCirculationFreq=1
                    if AirCirculationFreq<1:
                        AirCirculationFreq=5
                elif screenstate[1]==3:
                    if dt.value()==1:
                        maxTempi+=1
                    else:
                        maxTempi-=1
                    if maxTempi>35:
                        maxTempi=24
                    if maxTempi<24:
                        maxTempi=35#
                elif screenstate[1]==4:
                    if dt.value()==1:
                        wlvlTrh+=5
                    else:
                        wlvlTrh-=5
                    if wlvlTrh>1000:
                        wlvlTrh=700
                    elif wlvlTrh<1:
                        wlvlTrh=1
        drawscreen()
        dsp.show()
def encoderPress(obj):
    global swTstart,lastMove
    if obj.value()==0:
        swTstart=ticks_ms()
    else:
        if (ticks_ms()-swTstart)<1000 and (ticks_ms()-swTstart)>=300 and (ticks_ms()-lastMove)>200:
            print('pressed')
            if screenstate[0]==0:
                screenstate[0]=screenstate[1]
                screenstate[1]=0 
    lastMove=ticks_ms()
    drawscreen()
    dsp.show()
def backButtonPress(obj):
    global screenstate,lastMove
    if sw.value()==0 and obj.value()==0:
        run=False
        dsp.fill(0)
        dsp.text('Restarting',0,26 ,1)
        dsp.show()
        sleep(2)
        dsp.poweroff()
        reset()
    lastMove=ticks_ms()
    screenstate=[0,1]
    drawscreen()
#plantcare systems TIMER handlers
def pumpOff(t):
    pump.off()
def fanOff(t):
    fan.off()
#IRQ setup
clk.irq(trigger=Pin.IRQ_FALLING,handler=encoderRotation)
sw.irq(trigger=3,handler=encoderPress)
backButton.irq(trigger=Pin.IRQ_FALLING,handler=backButtonPress)
#starting to work
drawscreen()
updatePix()
pixDynamicRainbowInit()
measure()
start_server(ip)
sleep(2)
uplData(0)
#main loop
while True:
    measure()
    #pump
    if soilmoist<=minSoilMoisture and pump.value()==0 and waterlvlSens.read()<=wlvlTrh and fan.value()==0 and not DND:
        pix_off=True
        updatePix()
        pump.on()
        waterTim.init(period=(int(wateringDuration)*1000),mode=Timer.ONE_SHOT,callback=pumpOff)
    elif waterlvlSens.read()>wlvlTrh:
        dsp.text('H2O',90,0,1)
        dsp.show()
    if WIFI_PUMPON[0]:
        pump.on()
        waterTim.init(period=WIFI_PUMPON[1],mode=Timer.ONE_SHOT,callback=pumpOff)
        WIFI_PUMPON[0]=False
    #fan
    if tempi>maxTempi and tempi-tempo>=1:
        if fan.value()==0 and pump.value()==0:
            pix_off=True
            updatePix()
            fan.on()
            lastAirCirculation=ticks_ms()
            fanTim.init(period=AirCirculationDuration*60000,mode=Timer.ONE_SHOT,callback=fanOff)
            dsp.text('HOT',100,0,1)
            dsp.show()
    if (ticks_ms()-lastAirCirculation)>=(((60*60*1000)/AirCirculationFreq)-(AirCirculationDuration*60000)):
        if fan.value()==0 and pump.value()==0:
            pix_off=True
            updatePix()
            lastAirCirculation=ticks_ms()
            fan.on()
            fanTim.init(period=AirCirculationDuration*60000,mode=Timer.ONE_SHOT,callback=fanOff)
    #screen
    if ticks_ms()-lastMove>60000:
        screenstate=[0,0]
        drawscreen()
    if screenstate[0]==2:
        drawscreen()
    #print(tempo,tempi,humo,light,soilmoist)
    #neopixel
    if (not (fan.value() or pump.value()))and not DND: 
        pix_off=False
    updatePix()
    #DND
    if DND_act:
        dtmtuple=rtc.datetime()
        if (dtmtuple[4]*60+dtmtuple[5]>DND_start[0]*60+DND_start[1]) or (dtmtuple[4]*60+dtmtuple[5]<DND_stop[0]*60+DND_stop[1]):
                DND=True
                pix_off=True
        else:
            DND=False
    else:
        DND=False
    wdt.feed()
    sleep(1)