# ThermoGuard AI — Guide de Simulation Wokwi (ESP32 + DHT22)

Ce dossier contient tous les fichiers nécessaires pour exécuter la simulation de l'ESP32 et du capteur DHT directement dans le simulateur en ligne **[Wokwi](https://wokwi.com/)**, relié en direct à votre tableau de bord **ThermoGuard AI**.

---

## 1. Fichiers du projet Wokwi

* [`diagram.json`](diagram.json) : Le schéma du circuit électronique (ESP32 DevKit V1 relié au DHT22 virtuel sur le **GPIO 4**).
* [`sketch.ino`](sketch.ino) : Le code C++ Arduino configuré pour le Wi-Fi virtuel `Wokwi-GUEST` et la transmission HTTP/HTTPS POST.
* [`libraries.txt`](libraries.txt) : Les bibliothèques requises (`DHT sensor library`, `Adafruit Unified Sensor`).

> [!IMPORTANT]
> **Configuration Matérielle vs Virtuelle :**
> - **Wokwi (Simulation en ligne) :** Utilise le capteur **DHT22** sur **GPIO 4**.
> - **Matériel physique réel :** Utilise le capteur **DHT11** sur **GPIO 4** (voir [`esp32/cabinet_sensor.ino`](../esp32/cabinet_sensor.ino)).

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

### Étape C : Configurer l'adresse du Dashboard
Dans `sketch.ino`, configurez la variable `DASHBOARD_URL` :
- **Si vous utilisez la passerelle Wokwi IoT Gateway :**
  ```cpp
  const char* DASHBOARD_URL = "http://10.0.2.2:5000/api/readings";
  ```
- **Si vous utilisez un tunnel public (ex: Cloudflared, Ngrok, Localtunnel) :**
  ```cpp
  const char* DASHBOARD_URL = "https://votre-url-publique/api/readings";
  ```
- **Si votre backend est déployé dans le cloud (Render, Railway, etc.) :**
  ```cpp
  const char* DASHBOARD_URL = "https://votre-instance-thermoguard.onrender.com/api/readings";
  ```

### Étape D : Lancer la simulation
1. Démarrez votre backend local (`python backend/app.py`) ou vérifiez que votre cloud est actif.
2. Sur Wokwi, cliquez sur le bouton vert **Play (Start Simulation)**.
3. Observez le **Serial Monitor** (115200 baud) : vous verrez `[SUCCESS 201] Telemetry delivered to ThermoGuard AI Dashboard!`.
4. Sur votre Dashboard ([http://localhost:5000](http://localhost:5000)), le voyant passe immédiatement à **ESP32 ONLINE (HARDWARE MODE)** et les graphiques se mettent à jour en temps réel !

---

## 3. Comment tester les anomalies en direct dans Wokwi

Pendant que la simulation tourne dans Wokwi :
1. **Cliquez directement sur le composant DHT22** dans le schéma Wokwi.
2. Une petite fenêtre interactive apparaît avec deux curseurs :
   * **Temperature (°C)**
   * **Humidity (%)**
3. Glissez la température au-dessus de **38°C** (Avertissement) ou **52°C** (Critique), ou augmentez l'humidité au-dessus de **70%** / **85%**.
4. Regardez votre Dashboard ThermoGuard AI : le modèle **Isolation Forest** détecte immédiatement l'anomalie, la jauge passe au rouge, et une alerte SCADA est instantanément enregistrée dans le centre d'alarmes !
