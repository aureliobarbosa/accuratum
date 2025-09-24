import astropy.units as u
# import astropy.coordinates

class SolarClock:
    # if not set, longitude and latitude will corresponto to "Praça do cruzeiro, Brasilia, DF, Brazil"
    def __init__(self, longitude: float = -47.91526919090653, latitude: float = -15.783507525862756):
        
        if isinstance(longitude, float) and isinstance(longitude, float):
            self.lat = latitude*u.deg
            self.lon = longitude*u.deg
        else:
            raise AttributeError(f'Accuratum: longitude and latitude must be floats, received: {longitude}, {latitude}')

def main():
    print("Accuratum CLI is running with arguments:")

if __name__ == "__main__":
    main()