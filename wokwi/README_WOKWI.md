# CabinetSense AI — Guide de Simulation Wokwi (ESP32 + DHT)

Ce dossier contient tous les fichiers nécessaires pour exécuter la simulation de l'ESP32 et du capteur DHT directement dans le simulateur en ligne **[Wokwi](https://wokwi.com/)**.

---

## 1. Fichiers du projet Wokwi

* [`diagram.json`](diagram.json) : Le schéma du circuit électronique (ESP32 DevKit V1 relié au DHT22/DHT11 sur le **GPIO 4**).
* [`sketch.ino`](sketch.ino) : Le code C++ Arduino configuré pour le Wi-Fi virtuel `Wokwi-GUEST` et l'envoi HTTP POST.
* [`libraries.txt`](libraries.txt) : Les bibliothèques requises (`DHT sensor library`, `Adafruit Unified Sensor`).

---

## 2. Comment lancer la simulation sur Wokwi (Étape par étape)

### Étape A : Ouvrir Wokwi
1. Rendez-vous sur **[https://wokwi.com/](https://wokwi.com/)**.
2. Cliquez sur **ESP32** puis **ESP32 with Arduino**.

### Étape B : Copier les fichiers
1. Dans l'éditeur Wokwi, ouvrez l'onglet **`sketch.ino`** et collez le contenu de [`wokwi/sketch.ino`](sketch.ino).
2. Cliquez sur l'onglet **`diagram.json`** et remplacez son contenu par [`wokwi/diagram.json`](diagram.json).
3. Dans l'onglet **`Library Manager`** (ou `libraries.txt`), ajoutez :
   ```text
   DHT sensor library
   Adafruit Unified Sensor
   ```

### Étape C : Lancer la simulation
1. Cliquez sur le bouton vert **Play (Start Simulation)**.
2. Ouvrez le **Serial Monitor** en bas à droite (115200 baud).
3. Vous verrez l'ESP32 virtuel se connecter à `Wokwi-GUEST` et afficher les mesures.

---

## 3. Comment tester les anomalies en direct dans Wokwi

Pendant que la simulation tourne :
1. **Cliquez directement sur le composant DHT** dans le schéma Wokwi.
2. Une petite fenêtre interactive apparaît avec deux curseurs :
   * **Temperature (°C)**
   * **Humidity (%)**
3. Glissez la température au-dessus de **38°C** ou **52°C** pour simuler une surchauffe, ou la réelevez à plus de **75%** pour simuler une infiltration d'humidité !

---

## 4. Comment relier Wokwi (Cloud) à votre serveur Flask Local (`localhost:5000`)

Comme Wokwi s'exécute dans votre navigateur cloud et que votre serveur Flask tourne sur votre machine locale (`127.0.0.1:5000`), utilisez l'une de ces 2 méthodes pour connecter Wokwi à votre tableau de bord :

### Méthode 1 : Avec Ngrok (Le plus simple et rapide - Gratuit)
1. Ouvrez un terminal et lancez :
   ```powershell
   npx localtunnel --port 5000
   # OU avec ngrok :
   # ngrok http 5000
   ```
2. Vous obtiendrez une URL publique (ex: `https://cool-lion-12.loca.lt`).
3. Dans `sketch.ino` sur Wokwi, modifiez la ligne :
   ```cpp
   const char* SERVER_ENDPOINT = "https://cool-lion-12.loca.lt/api/readings";
   ```
4. Vos données Wokwi apparaîtront **instantanément** sur votre tableau de bord local en tant que **`HARDWARE MODE`** !

### Méthode 2 : Avec Wokwi IoT Gateway
Si vous avez installé la passerelle locale Wokwi, l'URL est directement :
```cpp
const char* SERVER_ENDPOINT = "http://10.0.2.2:5000/api/readings";
```
