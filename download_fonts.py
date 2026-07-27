import os
import urllib.request

fonts = {
    "Montserrat-ExtraBold.ttf": "https://github.com/googlefonts/montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf",
    "BebasNeue-Regular.ttf": "https://github.com/googlefonts/bebasneue/raw/master/fonts/ttf/BebasNeue-Regular.ttf",
    "Poppins-Black.ttf": "https://github.com/googlefonts/poppins/raw/master/products/Poppins-Black.ttf"
}

os.makedirs("fonts", exist_ok=True)

for name, url in fonts.items():
    print(f"Downloading {name}...")
    try:
        urllib.request.urlretrieve(url, os.path.join("fonts", name))
        print(f"Downloaded {name} successfully.")
    except Exception as e:
        print(f"Failed to download {name}: {e}")

