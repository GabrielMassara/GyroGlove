#include <Wire.h>
#include <I2Cdev.h>
#include <MPU6050.h>

const int D1 = A1;
const int D2 = A2;
const int D3 = A3;

// Multiplexador, pois precisarei de mais portas analogicas do que as que tem disponiveis
const int MUX_SIG = A0;  // Pino de sinal do multiplexer
const int MUX_S0 = 2;    // Pino de seleção S0
const int MUX_S1 = 3;    // Pino de seleção S1  
const int MUX_S2 = 4;    // Pino de seleção S2
const int MUX_S3 = 5;    // Pino de seleção S3
const int D0_CHANNEL = 0; // Canal 0 do multiplexer para D0
const int D4_CHANNEL = 1; // Canal 1 do multiplexer para D4

// Variáveis para o MPU6050
MPU6050 mpu;
int16_t ax, ay, az, gx, gy, gz;
int vx, vy;

//Apebnas para otimizacao
unsigned long lastTime = 0;
const unsigned long INTERVAL = 10;

// Função que le o canal do multiplexador
int readMux(int channel) {
  // Seleciona o canal no multiplexer
  digitalWrite(MUX_S0, bitRead(channel, 0));
  digitalWrite(MUX_S1, bitRead(channel, 1));
  digitalWrite(MUX_S2, bitRead(channel, 2));
  digitalWrite(MUX_S3, bitRead(channel, 3));
  
  delayMicroseconds(10);
  return analogRead(MUX_SIG);
}

void setup() {
  Serial.begin(115200);
  
  pinMode(MUX_S0, OUTPUT);
  pinMode(MUX_S1, OUTPUT);
  pinMode(MUX_S2, OUTPUT);
  pinMode(MUX_S3, OUTPUT);
  
  while (!Serial) {
    delay(1);
  }
  
  Wire.begin();
  Wire.setClock(400000);
  
  mpu.initialize();
  if (!mpu.testConnection()) { 
    while (1); 
  }
  
  mpu.setDLPFMode(MPU6050_DLPF_BW_98);
  mpu.setFullScaleGyroRange(MPU6050_GYRO_FS_500);
}

void loop() {
  unsigned long currentTime = millis();
  
  if (currentTime - lastTime >= INTERVAL) {
    lastTime = currentTime;
    
    // Le os valores dos dedos
    int valorD0 = readMux(D0_CHANNEL);  // D0 via canal 0 do multiplexer
    int valorD1 = analogRead(D1);       // D1 direto
    int valorD2 = analogRead(D2);       // D2 direto
    int valorD3 = analogRead(D3);       // D3 direto
    int valorD4 = readMux(D4_CHANNEL);  // D4 via canal 1 do multiplexer
    
    // Lê dados do MPU6050 de forma otimizada
    mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
    
    // Calcula coordenadas do ponteiro
    vx = constrain((gx + 15) / 120, -10, 10);
    vy = constrain(-(gz - 100) / 120, -10, 10);
    
    Serial.print("D0:");
    Serial.print(valorD0);
    Serial.print(" D1:");
    Serial.print(valorD1);
    Serial.print(" D2:");
    Serial.print(valorD2);
    Serial.print(" D3:");
    Serial.print(valorD3);
    Serial.print(" D4:");
    Serial.print(valorD4);
    Serial.print(" X:");
    Serial.print(vx);
    Serial.print(" Y:");
    Serial.println(vy);
  }
}
