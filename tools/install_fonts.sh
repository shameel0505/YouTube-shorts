#!/bin/bash
# Install required fonts for YouTube Shorts pipeline on Linux/GCP

set -e

echo "Updating apt and installing fonts-open-sans..."
sudo apt-get update
sudo apt-get install -y fonts-open-sans wget unzip fontconfig

FONT_DIR="/usr/local/share/fonts"
sudo mkdir -p $FONT_DIR

echo "Downloading Bebas Neue..."
wget -qO BebasNeue.zip "https://fonts.google.com/download?family=Bebas%20Neue"
sudo unzip -o BebasNeue.zip -d $FONT_DIR
rm BebasNeue.zip

echo "Downloading Anton..."
wget -qO Anton.zip "https://fonts.google.com/download?family=Anton"
sudo unzip -o Anton.zip -d $FONT_DIR
rm Anton.zip

echo "Downloading Montserrat..."
wget -qO Montserrat.zip "https://fonts.google.com/download?family=Montserrat"
sudo unzip -o Montserrat.zip -d $FONT_DIR
rm Montserrat.zip

echo "Downloading Poppins..."
wget -qO Poppins.zip "https://fonts.google.com/download?family=Poppins"
sudo unzip -o Poppins.zip -d $FONT_DIR
rm Poppins.zip

echo "Updating font cache..."
sudo fc-cache -fv

echo "Fonts installed successfully!"
