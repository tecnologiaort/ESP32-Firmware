from ORT import *
from time import *
t = 0.2
for i in range(1,5):
    salidaAnalogica(i,100)
    sleep(t)
    
for i in range(1,5):  
    salidaDigital(i,1)
    sleep(t)

for i in range(4):
    for i in range(1,5):
        salidaAnalogica(i,0)
        salidaDigital(i,1)
    sleep(t)

    for i in range(1,5):
        salidaAnalogica(i,100)
        salidaDigital(i,0)
    sleep(t)
    
for i in range(1,5):
    salidaAnalogica(i,0)
    sleep(t)

    
