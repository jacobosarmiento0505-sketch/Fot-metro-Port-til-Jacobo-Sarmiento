# Firmware (ESP32)

Carpeta reservada para el firmware del ESP32 (lectura del sensor TCS34725
por I2C, manejo del display OLED, lectura de los botones CALIBRAR/MEDIR y
lógica de cálculo de la muestra).

Pendiente de implementación. Sugerencia de librerías Arduino/ESP-IDF:

- `Adafruit_TCS34725` (sensor de color I2C)
- `Adafruit_SSD1306` + `Adafruit_GFX` (display OLED)

Pines sugeridos según el esquemático (`electronica/kicad/fotometro.kicad_sch`):

| Señal | Función |
|---|---|
| SDA / SCL | Bus I2C compartido (OLED + TCS34725) |
| GPIO_CAL | Botón CALIBRAR (activo en bajo, pull-up externo) |
| GPIO_MED | Botón MEDIR (activo en bajo, pull-up externo) |
