import datetime
from typing import Tuple

import numpy as np
from astropy.coordinates import AltAz, EarthLocation, get_sun
from astropy.time import Time, TimeDelta
from astropy.units import deg

# lat, lon = location
# earth_location = EarthLocation(lat=lat, lon=lon)
# Time must also be an astropy time, at UTC.

# TODO: Test this in a complete way for a single Time and try to generalize for multiple times.
def get_sun_altaz(location: EarthLocation, time: Time) -> Tuple[float,float]:
    """ 
    Calculate the coordinate of the Sun in the sky in terms as an (altitude, azimuth), 
    based on an EarthLocation and an Astropy Time.
    """
    frame = AltAz(location=location, obstime=time)
    sun = get_sun(time).transform_to(frame)
    return (sun.alt.value, sun.az.value)


# Initial code from Paulo Brito
def main():
    """
    Posição da entrada do Predio "Paulo Freire" FUP-UnB
    """
    step_hour = 10
    step_day = 7

    lat1= -(15+36/60+3/3600)
    long1= -(47+39/60+32/3600)
    date1 = "2024-12-21"
    date2 = "2025-06-20" # what is this unused variable for?
    date3 = "2025-12-21"
    timezone_shift =  3

    NH = 1+(10*60)//step_hour
    ND = 1+365//step_day

    azimuth = np.zeros((ND,NH))
    altitude  = np.zeros((ND,NH))
    shadow_x = np.zeros((ND,NH))
    shadow_y = np.zeros((ND,NH))
    hours_and_days = np.empty((ND,NH),dtype='object')
    plumb = 1.0

    # def pos_sol(latitude,longitude,time):
    #     """
    #     Calcula a posição do Sol (azimute e altura) para uma dada localização e tempo.
    #     """
    #     local = EarthLocation(lat=latitude*deg, lon=longitude*deg)
    #     altaz_frame = AltAz(location=local, obstime=time)
    #     sol = get_sun(time)
    #     sol_altaz = sol.transform_to(altaz_frame)
    #     altura = sol_altaz.alt.value
    #     azimute = sol_altaz.az.value
    #     return altura,azimute

    def plumb_shadow(plumb_length, sun_alt, sun_az):
        """
        Calculates the length and coordinates of a plumb bob's shadow.
        """

        if  (sun_alt==90):
            return 0, 0, 0
        else: 
            comprimento_sombra = plumb_length / np.tan(np.deg2rad(sun_alt))
            x_sombra = -comprimento_sombra * np.sin(np.deg2rad(sun_az))
            y_sombra = comprimento_sombra * np.cos(np.deg2rad(sun_az))
        return comprimento_sombra, x_sombra, y_sombra

    data_atual = Time(date1)
    data_fim = Time(date3)
    horas = np.arange(7+timezone_shift, 17.05+timezone_shift, step_hour/60) # Intervalos de passoH minutos
    ho=0
    print("# ho,di,tempo1,altura_sol,azimute_sol,comprimento_sombra,-x_sombra,y_sombra", "\n")
    for hora in horas:
        data_atual = Time(date1)
        di=0
        while data_atual <= data_fim:
            dia_str = data_atual.iso.split(' ')[0]
            date_obj = datetime.datetime.strptime(dia_str, '%Y-%m-%d')
            tempo_str = f"{dia_str} {int(hora):02d}:{int((hora - int(hora)) * 60):02d}:00"
            tempo1= (Time(tempo_str, scale='utc'))
            altura_sol,azimute_sol = pos_sol(lat1, long1, tempo1)
            comprimento_sombra,x_sombra,y_sombra = plumb_shadow(plumb, altura_sol, azimute_sol)
            altitude[di,ho] = altura_sol
            azimuth[di,ho] = azimute_sol
            shadow_x[di,ho] = x_sombra
            shadow_y[di,ho] = y_sombra
            hours_and_days[di,ho] = str(tempo1)
            print(ho,di,tempo1,altura_sol,azimute_sol,comprimento_sombra,-x_sombra,y_sombra)
            data_atual += TimeDelta(step_day) # Incrementa para passoD
            di +=1 
            # print("")
        ho += 1


