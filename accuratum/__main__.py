import astropy.units as u
# import astropy.coordinates

class SolarClock:
    # Coordinates for "Praça do cruzeiro, Brasilia, DF, Brazil"
    def __init__(self, longitude: float = -47.91526919090653, latitude: float = -15.783507525862756):
        
        if isinstance(longitude, float) and isinstance(longitude, float):
            self.lat = latitude*u.deg
            self.lon = longitude*u.deg
        else:
            msg = ( 'Accuratum: SolarClock initialization error. '
                    'Both longitude and latitude must be of type float'
                    f', received: {longitude}, {latitude}.'
            )
            raise TypeError(msg)

def main():
    print("Accuratum CLI is running with arguments:")

if __name__ == "__main__":
    main()