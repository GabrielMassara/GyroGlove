#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import serial
import time
import pyautogui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class ArduinoThread(QThread):
    finger_values_updated = pyqtSignal(list)

    def __init__(self, com_port='COM9'):
        super().__init__()
        self.com_port = com_port
        self.running = False
        self.arduino = None

    def connect_arduino(self):
        try:
            self.arduino = serial.Serial(self.com_port, 115200, timeout=0.01)
            time.sleep(1)
            print(f"Conectado na porta {self.com_port} a 115200 baud")
            return True
        except Exception as e:
            print(f"Erro ao conectar na porta {self.com_port}: {e}")
            return False

    def run(self):
        if not self.connect_arduino():
            return

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0
        sensitivity = 0.8

        print("Lendo dados... (Clique em Parar para finalizar)")
        print("Mova o mouse para o canto superior esquerdo para parar em emergência")

        try:
            while self.running:
                if self.arduino.in_waiting > 0:
                    linha = self.arduino.readline().decode().strip()
                    if linha and "X:" in linha:
                        try:
                            x_part = linha.split("X:")[1].split()[0]
                            y_part = linha.split("Y:")[1].split()[0]

                            sensor_x = int(x_part)
                            sensor_y = int(y_part)

                            mouse_x = sensor_y * sensitivity
                            mouse_y = -sensor_x * sensitivity

                            if abs(sensor_x) > 0 or abs(sensor_y) > 0:
                                pyautogui.move(mouse_x, mouse_y)

                        except (ValueError, IndexError):
                            pass

                        self.detect_fingers(linha)

                time.sleep(0.001)

        except pyautogui.FailSafeException:
            print("\nFailSafe ativado! Mouse movido para canto superior esquerdo.")
        except Exception as e:
            print(f"\nErro durante execução: {e}")
        finally:
            if self.arduino:
                self.arduino.close()
            print("Desconectado")

    def detect_fingers(self, linha):
        fingers = [
            ("D0:", 630, "indicador", 1024),
            ("D1:", 480, "médio", 1024),
            ("D2:", 480, "anelar", 1024),
            ("D3:", 480, "polegar", 1024),
            ("D4:", 600, "mindinho", 1024)
        ]

        finger_values = [0, 0, 0, 0, 0]

        for i, (finger_tag, threshold, name, max_val) in enumerate(fingers):
            if finger_tag in linha:
                try:
                    valor = int(linha.split(finger_tag)[1].split()[0])
                    percentage = max(0, min(100, 100 - int((valor / max_val) * 100)))
                    finger_values[i] = percentage

                    if valor < threshold:
                        print(f"Dedo {name} ({finger_tag[:-1]}) detectado - Valor: {valor}, Slider: {percentage}%")

                except (ValueError, IndexError):
                    pass

        self.finger_values_updated.emit(finger_values)

    def stop(self):
        self.running = False
        if self.arduino:
            try:
                self.arduino.close()
            except:
                pass


class GyroGlovesWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.arduino_thread = None
        self.setupUI()
        self.connectSignals()

    def setupUI(self):
        self.setObjectName("GyroGloves")
        self.setGeometry(0, 0, 570, 399)
        self.setMinimumSize(570, 399)
        self.setMaximumSize(570, 399)
        self.setWindowTitle("GyroGloves")
        self.setStyleSheet("background-color: rgb(42, 42, 42);")

        self.centralwidget = QWidget()
        self.setCentralWidget(self.centralwidget)

        self.label = QLabel(self.centralwidget)
        self.label.setGeometry(QRect(180, 0, 201, 51))
        self.label.setStyleSheet("""
            color: rgb(206, 255, 92);
            font: 25 28pt "Yu Gothic UI Light";
        """)
        self.label.setText("Gyro Gloves")

        self.slidePositions = [30, 80, 130, 180, 230]
        self.sliders = []
        self.sliderLabels = []
        self.fingerInputs = []

        for i in range(5):
            slider = QSlider(self.centralwidget)
            slider.setObjectName(f"verticalSlider_{i + 1}")
            slider.setGeometry(QRect(self.slidePositions[i], 119 + i, 22, 211))
            slider.setOrientation(Qt.Vertical)
            slider.setMinimum(0)
            slider.setMaximum(100)
            slider.setValue(0)
            self.sliders.append(slider)

            label = QLabel(self.centralwidget)
            label.setObjectName(f"label_{i + 2}")
            label.setGeometry(QRect(self.slidePositions[i], 80, 31, 21))
            label.setStyleSheet("""
                color: rgb(206, 255, 92);
                font: 25 15pt "Yu Gothic UI Light";
            """)
            label.setText(f"D{i}")
            self.sliderLabels.append(label)

            char_input = QLineEdit(self.centralwidget)
            char_input.setObjectName(f"fingerInput_{i}")
            char_input.setGeometry(QRect(self.slidePositions[i] - 5, 100, 32, 23))
            char_input.setMaxLength(1)
            char_input.setStyleSheet("""
                color: rgb(206, 255, 92);
                font: 10pt "MS Shell Dlg 2";
                background-color: rgb(60, 60, 60);
                border: 1px solid rgb(100, 100, 100);
                text-align: center;
            """)
            char_input.setPlaceholderText("?")
            self.fingerInputs.append(char_input)

        self.okButtons = []
        for i in range(5):
            button = QPushButton(self.centralwidget)
            button.setObjectName(f"pushButton_{i + 1}")
            button.setGeometry(QRect(20 + (i * 50), 340, 41, 23))
            button.setCursor(QCursor(Qt.PointingHandCursor))
            button.setStyleSheet("""
                color: rgb(206, 255, 92);
                font: 10pt "MS Shell Dlg 2";
            """)
            button.setText("OK")
            self.okButtons.append(button)

        self.label_com = QLabel(self.centralwidget)
        self.label_com.setGeometry(QRect(370, 80, 51, 21))
        self.label_com.setStyleSheet("""
            color: rgb(206, 255, 92);
            font: 25 15pt "Yu Gothic UI Light";
        """)
        self.label_com.setText("COM:")

        self.lineEdit_com = QLineEdit(self.centralwidget)
        self.lineEdit_com.setGeometry(QRect(420, 70, 41, 41))
        self.lineEdit_com.setStyleSheet("""
            color: rgb(206, 255, 92);
            font: 12pt "MS Shell Dlg 2";
        """)
        self.lineEdit_com.setText("COM9")

        self.pushButton_salvar = QPushButton(self.centralwidget)
        self.pushButton_salvar.setGeometry(QRect(470, 70, 91, 41))
        self.pushButton_salvar.setCursor(QCursor(Qt.PointingHandCursor))
        self.pushButton_salvar.setStyleSheet("""
            color: rgb(206, 255, 92);
            font: 10pt "MS Shell Dlg 2";
        """)
        self.pushButton_salvar.setText("Salvar")

        self.pushButton_iniciar = QPushButton(self.centralwidget)
        self.pushButton_iniciar.setGeometry(QRect(370, 140, 191, 41))
        self.pushButton_iniciar.setCursor(QCursor(Qt.PointingHandCursor))
        self.pushButton_iniciar.setStyleSheet("""
            color: rgb(206, 255, 92);
            font: 10pt "MS Shell Dlg 2";
        """)
        self.pushButton_iniciar.setText("Iniciar")

        self.pushButton_parar = QPushButton(self.centralwidget)
        self.pushButton_parar.setGeometry(QRect(370, 190, 191, 41))
        self.pushButton_parar.setCursor(QCursor(Qt.PointingHandCursor))
        self.pushButton_parar.setStyleSheet("""
            color: rgb(206, 255, 92);
            font: 10pt "MS Shell Dlg 2";
        """)
        self.pushButton_parar.setText("Parar")

        self.label_imagem = QLabel(self.centralwidget)
        self.label_imagem.setGeometry(QRect(390, 240, 221, 191))

        self.carregarImagem()

        self.label_autor = QLabel(self.centralwidget)
        self.label_autor.setGeometry(QRect(0, 380, 161, 21))
        self.label_autor.setStyleSheet("""
            color: rgb(206, 255, 92);
            font: 25 10pt "Yu Gothic UI Light";
        """)
        self.label_autor.setText("Gabriel Evangelista Massara")

    def carregarImagem(self):
        image_path = "files/img/cat2.png"
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    self.label_imagem.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.label_imagem.setPixmap(scaled_pixmap)
            else:
                self.label_imagem.setText("Imagem não encontrada")
                self.label_imagem.setStyleSheet("color: rgb(206, 255, 92);")
        else:
            self.label_imagem.setText("🐱")
            self.label_imagem.setStyleSheet("""
                color: rgb(206, 255, 92);
                font-size: 48px;
                qproperty-alignment: AlignCenter;
            """)

    def connectSignals(self):
        for i, button in enumerate(self.okButtons):
            button.clicked.connect(lambda checked, idx=i: self.onOkClicked(idx))

        for i, slider in enumerate(self.sliders):
            slider.valueChanged.connect(lambda value, idx=i: self.onSliderChanged(idx, value))

        for i, char_input in enumerate(self.fingerInputs):
            char_input.textChanged.connect(lambda text, idx=i: self.onFingerCharChanged(idx, text))

        self.pushButton_salvar.clicked.connect(self.onSalvarClicked)
        self.pushButton_iniciar.clicked.connect(self.onIniciarClicked)
        self.pushButton_parar.clicked.connect(self.onPararClicked)

        self.pushButton_parar.setEnabled(False)

    def updateSliders(self, finger_values):
        for i, value in enumerate(finger_values):
            if i < len(self.sliders):
                current_value = self.sliders[i].value()
                if abs(current_value - value) > 2:
                    self.sliders[i].setValue(int(value))

    def onOkClicked(self, index):
        slider_value = self.sliders[index].value()
        print(f"OK {index} clicado - Slider D{index} valor: {slider_value}")

    def onSliderChanged(self, index, value):
        print(f"Slider D{index} mudou para: {value}")

    def onFingerCharChanged(self, index, text):
        print(f"Dedo D{index} caractere mudou para: '{text}'")

    def onSalvarClicked(self):
        com_port = self.lineEdit_com.text()
        print(f"Salvar clicado - Porta COM: {com_port}")

        valores = [slider.value() for slider in self.sliders]
        print(f"Valores dos sliders: {valores}")

        caracteres = [input_field.text() for input_field in self.fingerInputs]
        print(f"Caracteres dos dedos: {caracteres}")

    def onIniciarClicked(self):
        if self.arduino_thread is None or not self.arduino_thread.isRunning():
            com_port = self.lineEdit_com.text() or "COM9"
            print(f"Iniciando comunicação com Arduino na porta {com_port}...")

            self.arduino_thread = ArduinoThread(com_port)
            self.arduino_thread.running = True

            self.arduino_thread.finger_values_updated.connect(self.updateSliders)

            self.arduino_thread.start()

            self.pushButton_iniciar.setText("Executando...")
            self.pushButton_iniciar.setEnabled(False)
            self.pushButton_parar.setEnabled(True)
        else:
            print("Arduino já está executando!")

    def onPararClicked(self):
        print("Parando comunicação com Arduino...")

        if self.arduino_thread and self.arduino_thread.isRunning():
            try:
                self.arduino_thread.finger_values_updated.disconnect(self.updateSliders)
            except:
                pass

            self.arduino_thread.stop()
            self.arduino_thread.wait(2000)

            if self.arduino_thread.isRunning():
                self.arduino_thread.terminate()

        self.pushButton_iniciar.setText("Iniciar")
        self.pushButton_iniciar.setEnabled(True)
        self.pushButton_parar.setEnabled(False)

        print("Comunicação parada.")

    def closeEvent(self, event):
        if self.arduino_thread and self.arduino_thread.isRunning():
            print("Finalizando conexão com Arduino...")

            try:
                self.arduino_thread.finger_values_updated.disconnect(self.updateSliders)
            except:
                pass

            self.arduino_thread.stop()
            self.arduino_thread.wait(2000)

            if self.arduino_thread.isRunning():
                self.arduino_thread.terminate()

        event.accept()


class GyroGlovesApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = GyroGlovesWindow()

    def run(self):
        self.window.show()
        return self.app.exec_()


def main():
    try:
        app = GyroGlovesApp()
        sys.exit(app.run())
    except Exception as e:
        print(f"Erro ao executar a aplicação: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()