# Plantcare-system
A plant care system with watering, ventilation and light. It has physical UI, local web UI. It also sends data to thingspeak.
Microcontroler used: ESP32
# Sensors
DHT11-temperature and humidity outside the plant chamber;
DS18B20-temperature inside the plant chamber;
Capacitive soil moisture sensor;
LDR-measuring light intesity;
# Light-NeoPixel
It has 5 lightning modes: OFF, white, monocolor, bicolor, dynamic rainbow, plantcare(auto)-only purple;
On the white, monocolor and bicolor mode there are 3 brightness modes, manual, treshold, and dimming+treshold;
parameters changable in both physical and web UI;
# Watering
water now function using the web UI+watering plants when soil moisture is below treshold;
parameters changable in both physical and web UI;
# Ventilation
periodically ventilates + ventilates when temperature inside is high and the outside temperature is lower + ventilate now fuction using we UI;
parameters changable in both physical and web UI;
# DND
during DND lights are off and automatic watering is disabled;
You can switch it off or on and change the start and end time in the web UI;
The ESP32 RTC time is set automatically when connected to wifi (UTC time is used); 
# Physical UI
SSD1306 OLED, rotary enncoder, button;
Button press-home screen;
Rotation of the encorer-feature selection;
Encoder press feature selection;
Encoder press +  rotation-variable changing;
