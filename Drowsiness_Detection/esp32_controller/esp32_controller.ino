#define IN1 25
#define IN2 26
#define ENA 27
#define BUZZER 14
#define GREEN_LED 18
#define RED_LED 19

void setup() {
  Serial.begin(9600);

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
}

void makeCall(String gpsLocation) {
  // 1. Send SMS with GPS Location
  Serial.println("AT+CMGF=1"); // Set SMS to text mode
  delay(1000);
  Serial.println("AT+CMGS=\"+917699602984\""); // Replace with your emergency contact number
  delay(1000);
  
  Serial.print("Emergency! Driver Drowsiness Detected. GPS Location: https://maps.google.com/?q=");
  Serial.print(gpsLocation);
  delay(100);
  Serial.write(26); // ASCII code of CTRL+Z to send the SMS
  delay(5000); // Wait 5 seconds for the SMS to be sent

  // 2. Make the phone call
  // Replace with your emergency contact number
  Serial.println("ATD+919999999999;");
}

void loop() {

  if (Serial.available()) {

    String commandStr = Serial.readStringUntil('\n');
    commandStr.trim();

    if (commandStr.length() > 0) {
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
