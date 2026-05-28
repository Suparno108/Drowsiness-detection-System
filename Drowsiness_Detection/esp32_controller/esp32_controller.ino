#define IN1 25
#define IN2 26
#define ENA 27
#define BUZZER 14
#define GREEN_LED 18
#define RED_LED 19

void setup() {
  Serial.begin(9600);
  // Initialize Serial2 for SIM800L GSM module (RX=16, TX=17)
  Serial2.begin(9600, SERIAL_8N1, 16, 17);

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(ENA, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);

  // Initialize motor direction
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  // Normal conditions at start
  digitalWrite(GREEN_LED, HIGH);
  digitalWrite(RED_LED, LOW);

  // Synchronize SIM800L Auto-Bauding with active confirmation
  Serial.println("Synchronizing baud rate with SIM800L...");
  bool gsmDetected = false;
  for (int i = 0; i < 10; i++) {
    Serial2.println("AT");
    delay(500);
    if (Serial2.available()) {
      String res = Serial2.readString();
      if (res.indexOf("OK") != -1) {
        gsmDetected = true;
        Serial.println("SIM800L Detected and Synchronized successfully!");
        break;
      }
    }
    Serial.print(".");
  }
  if (!gsmDetected) {
    Serial.println("\n[WARNING] SIM800L not responding! Check your wiring, RX/TX swap, and power.");
  }
}

void printGSMResponse(int timeoutMs = 1500) {
  unsigned long start = millis();
  Serial.print("SIM800L Response: ");
  bool dataReceived = false;
  
  while (millis() - start < timeoutMs) {
    while (Serial2.available()) {
      char c = Serial2.read();
      Serial.write(c);
      dataReceived = true;
      start = millis(); // Reset timeout on active data stream
    }
    delay(10);
  }
  if (!dataReceived) {
    Serial.print("(No Response / Timeout)");
  }
  Serial.println();
}

void makeCall(String gpsLocation) {
  Serial.println("--- EMERGENCY ALERT ACTIVATED ---");
  
  // 1. Send SMS with GPS Location
  Serial.println("Configuring SMS text mode (AT+CMGF=1)...");
  Serial2.println("AT+CMGF=1");
  printGSMResponse(1000);

  Serial.println("Setting recipient phone number (AT+CMGS)...");
  Serial2.println("AT+CMGS=\"+918972250166\"");
  printGSMResponse(1500); // Sometimes takes slightly longer for '>' prompt
  
  Serial.println("Sending emergency message content...");
  Serial2.print("Emergency! Driver Drowsiness Detected. GPS Location: https://maps.google.com/?q=");
  Serial2.print(gpsLocation);
  Serial2.write(26); // ASCII code of CTRL+Z to send the SMS
  
  Serial.println("Waiting for SMS to be transmitted over network...");
  printGSMResponse(12000); // SMS send can take 5-10s

  // 2. Make the phone call
  Serial.println("Dialing voice call to +918972250166 (ATD)...");
  Serial2.println("ATD+918972250166;");
  printGSMResponse(2000);
  
  Serial.println("--- EMERGENCY ALERT CONCLUDED ---");
}



void loop() {
  // 1. Read input from the Python application (PC Serial)
  if (Serial.available()) {
    String commandStr = Serial.readStringUntil('\n');
    commandStr.trim();

    if (commandStr.length() > 0) {
      // Pass-through utility: if command starts with AT, send directly to SIM800L
      if (commandStr.startsWith("AT") || commandStr.startsWith("at")) {
        Serial.print("[DEBUG] Forwarding to SIM800L: ");
        Serial.println(commandStr);
        Serial2.println(commandStr);
      }
      else {
        char command = commandStr.charAt(0);

        if(command == 'W') {
          // Warning (Strike 1 or 2)
          digitalWrite(GREEN_LED, LOW);
          digitalWrite(RED_LED, HIGH);
          digitalWrite(BUZZER, HIGH);
        }
        else if(command == 'E') {
          // Emergency (Strike 3)
          digitalWrite(GREEN_LED, LOW);
          digitalWrite(RED_LED, HIGH);
          digitalWrite(BUZZER, HIGH);

          // Gradually slow motor (Unavoidable stop)
          for(int speed=255; speed>=0; speed-=20){
            analogWrite(ENA, speed);
            delay(500);
          }

          analogWrite(ENA, 0);
          
          String gpsLocation = "Unknown";
          if (commandStr.length() > 1) {
            gpsLocation = commandStr.substring(1);
          }
          makeCall(gpsLocation);
        }
        else if(command == 'N') {
          // Normal (Eyes Open)
          digitalWrite(GREEN_LED, HIGH);
          digitalWrite(RED_LED, LOW);
          analogWrite(ENA, 255);
          digitalWrite(BUZZER, LOW);
        }
      }
    }
  }

  // 2. Continuous passive read from SIM800L to output any unsolicited cellular logs (e.g. RING, SMS, Network stats)
  if (Serial2.available()) {
    Serial.print("[SIM800L Live] ");
    while (Serial2.available()) {
      char c = Serial2.read();
      Serial.write(c);
    }
    Serial.println();
  }
}
