from astropy.coordinates import EarthLocation, AltAz, get_sun
from astropy.time import Time, TimeDelta
from astropy.units import deg
import numpy as np
import datetime

"""
Posição da entrada do Predio "Paulo Freire" FUP-UnB
"""
passoH = 10
passoD = 7
NH = 1+(10*60)//passoH
ND = 1+365//passoD
lat1= -(15+36/60+3/3600)
long1= -(47+39/60+32/3600)
data1 = "2024-12-21"
data2 = "2025-06-20"
data3 = "2025-12-21"
fuso =  3
azimute = np.zeros((ND,NH))
altura  = np.zeros((ND,NH))
sombraX = np.zeros((ND,NH))
sombraY = np.zeros((ND,NH))
horadia = np.empty((ND,NH),dtype='object')
prumo = 1.0

"""
Calcula a posição do Sol (azimute e altura) para uma dada localização e tempo.
"""
def pos_sol(latitude,longitude,tempo):
    local = EarthLocation(lat=latitude*deg, lon=longitude*deg)
    altaz_frame = AltAz(location=local, obstime=tempo)
    sol = get_sun(tempo)
    sol_altaz = sol.transform_to(altaz_frame)
    altura = sol_altaz.alt.value
    azimute = sol_altaz.az.value
    return altura,azimute

"""
Calcula o comprimento e as coordenadas da sombra de um prumo.
"""
def calcular_sombra_prumo(altura_prumo, altura_solar, azimute_solar):
    if  (altura_solar==90):
        return 0, 0, 0
    else: 
       comprimento_sombra = altura_prumo / np.tan(np.deg2rad(altura_solar))
       x_sombra = -comprimento_sombra * np.sin(np.deg2rad(azimute_solar))
       y_sombra = comprimento_sombra * np.cos(np.deg2rad(azimute_solar))
       return comprimento_sombra, x_sombra, y_sombra

data_atual = Time(data1)
data_fim = Time(data3)
horas = np.arange(7+fuso, 17.05+fuso, passoH/60) # Intervalos de passoH minutos
ho=0
for hora in horas:
    data_atual = Time(data1)
    di=0
    while data_atual <= data_fim:
        dia_str = data_atual.iso.split(' ')[0]
        date_obj = datetime.datetime.strptime(dia_str, '%Y-%m-%d')
        tempo_str = f"{dia_str} {int(hora):02d}:{int((hora - int(hora)) * 60):02d}:00"
        tempo1= (Time(tempo_str, scale='utc'))
        altura_sol,azimute_sol = pos_sol(lat1, long1, tempo1)
        comprimento_sombra,x_sombra,y_sombra = calcular_sombra_prumo(prumo, altura_sol, azimute_sol)
        altura[di,ho] = altura_sol
        azimute[di,ho] = azimute_sol
        sombraX[di,ho] = x_sombra
        sombraY[di,ho] = y_sombra
        horadia[di,ho] = str(tempo1)
#        print(ho,di,tempo1,altura_sol,azimute_sol,comprimento_sombra,-x_sombra,y_sombra)
        data_atual += TimeDelta(passoD) # Incrementa para passoD
        di +=1 
#    print("")
    ho +=1


