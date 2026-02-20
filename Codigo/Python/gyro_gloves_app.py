#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import serial
import time
import json
import pyautogui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class CalibrationThread(QThread):
    finger_values_updated = pyqtSignal(list)

    def __init__(self, com_port='COM9', configs=None):
        super().__init__()
        self.com_port = com_port
        self.configs = configs or self.load_default_configs()
        self.running = False
        self.arduino = None

    def load_default_configs(self):
        return {
            "com_port": "COM9",
            "fingers": [
                {"name": "D0", "key": "", "threshold": 630},
                {"name": "D1", "key": "", "threshold": 480},
                {"name": "D2", "key": "", "threshold": 480},
                {"name": "D3", "key": "", "threshold": 480},
                {"name": "D4", "key": "", "threshold": 600}
            ]
        }

    def connect_arduino(self):
        try:
            self.arduino = serial.Serial(self.com_port, 115200, timeout=0.01)
            time.sleep(1)
            print(f"Conectado na porta {self.com_port} a 115200 baud para calibração")
            return True
        except Exception as e:
            print(f"Erro ao conectar na porta {self.com_port}: {e}")
            return False

    def run(self):
        if not self.connect_arduino():
            return

        print("Modo de calibração iniciado - apenas lendo potenciômetros...")
        print("(Clique em Parar Calibração para finalizar)")

        try:
            while self.running:
                if self.arduino.in_waiting > 0:
                    try:
                        linha = self.arduino.readline().decode('utf-8', errors='ignore').strip()
                        if linha:
                            self.read_finger_values(linha)
                    except UnicodeDecodeError:
                        # Ignorar linhas com erro de decodificação
                        continue
                time.sleep(0.001)

        except Exception as e:
            print(f"\nErro durante calibração: {e}")
        finally:
            if self.arduino:
                self.arduino.close()
            print("Calibração finalizada")

    def read_finger_values(self, linha):
        finger_names = ["indicador", "médio", "anelar", "polegar", "mindinho"]
        finger_values = [0, 0, 0, 0, 0]
        raw_values = [0, 0, 0, 0, 0]  # Valores brutos dos potenciômetros
        max_val = 1024

        for i, finger_config in enumerate(self.configs["fingers"]):
            finger_tag = f"{finger_config['name']}:"
            name = finger_names[i]

            if finger_tag in linha:
                try:
                    valor = int(linha.split(finger_tag)[1].split()[0])
                    percentage = max(0, min(100, 100 - int((valor / max_val) * 100)))
                    finger_values[i] = percentage
                    raw_values[i] = valor
                except (ValueError, IndexError):
                    pass

        self.finger_values_updated.emit([finger_values, raw_values])

    def stop(self):
        self.running = False
        if self.arduino:
            try:
                self.arduino.close()
            except:
                pass


class ArduinoThread(QThread):
    finger_values_updated = pyqtSignal(list)

    def __init__(self, com_port='COM9', configs=None):
        super().__init__()
        self.com_port = com_port
        self.configs = configs or self.load_default_configs()
        self.running = False
        self.arduino = None
        self.pressed_keys = {}  # Dicionário para controlar teclas e repetição

    def load_default_configs(self):
        return {
            "com_port": "COM9",
            "fingers": [
                {"name": "D0", "key": "", "threshold": 630},
                {"name": "D1", "key": "", "threshold": 480},
                {"name": "D2", "key": "", "threshold": 480},
                {"name": "D3", "key": "", "threshold": 480},
                {"name": "D4", "key": "", "threshold": 600}
            ]
        }

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

        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0
        sensitivity = 0.8

        print("Lendo dados... (Clique em Parar para finalizar)")

        try:
            while self.running:
                if self.arduino.in_waiting > 0:
                    try:
                        linha = self.arduino.readline().decode('utf-8', errors='ignore').strip()
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
                    except UnicodeDecodeError:
                        # Ignorar linhas com erro de decodificação
                        continue

                time.sleep(0.001)

        except Exception as e:
            print(f"\nErro durante execução: {e}")
        finally:
            if self.arduino:
                self.arduino.close()
            print("Desconectado")

    def detect_fingers(self, linha):
        finger_names = ["indicador", "médio", "anelar", "polegar", "mindinho"]
        finger_values = [0, 0, 0, 0, 0]
        raw_values = [0, 0, 0, 0, 0]  # Valores brutos dos potenciômetros
        max_val = 1024

        for i, finger_config in enumerate(self.configs["fingers"]):
            finger_tag = f"{finger_config['name']}:"
            threshold = finger_config["threshold"]
            key = finger_config["key"]
            name = finger_names[i]

            if finger_tag in linha:
                try:
                    valor = int(linha.split(finger_tag)[1].split()[0])
                    percentage = max(0, min(100, 100 - int((valor / max_val) * 100)))
                    finger_values[i] = percentage
                    raw_values[i] = valor

                    if valor < threshold:
                        # Manter tecla pressionada se configurada e repetir continuamente
                        if key and key.strip():
                            try:
                                if key not in self.pressed_keys:
                                    # Primeira vez pressionando a tecla
                                    pyautogui.keyDown(key)
                                    self.pressed_keys[key] = 0
                                else:
                                    # Repetir a tecla a cada 5 ciclos (~50ms)
                                    self.pressed_keys[key] += 1
                                    if self.pressed_keys[key] >= 5:
                                        pyautogui.press(key)
                                        self.pressed_keys[key] = 0
                            except Exception as e:
                                print(f"Erro ao pressionar tecla '{key}': {e}")
                    else:
                        # Soltar tecla quando dedo não for detectado
                        if key and key in self.pressed_keys:
                            try:
                                pyautogui.keyUp(key)
                                del self.pressed_keys[key]
                            except Exception as e:
                                print(f"Erro ao liberar tecla '{key}': {e}")

                except (ValueError, IndexError):
                    pass

        self.finger_values_updated.emit([finger_values, raw_values])

    def stop(self):
        self.running = False
        # Soltar todas as teclas pressionadas antes de parar
        for key in list(self.pressed_keys.keys()):
            try:
                pyautogui.keyUp(key)
            except:
                pass
        self.pressed_keys.clear()

        if self.arduino:
            try:
                self.arduino.close()
            except:
                pass


class GyroGlovesWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.arduino_thread = None
        self.calibration_thread = None
        self.configs = self.loadConfigs()
        self.setupUI()
        self.connectSignals()
        self.loadConfigsToUI()

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
        self.valueLabels = []  # Labels para mostrar valores dos potenciômetros

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

            # Label para mostrar valor do potenciômetro
            value_label = QLabel(self.centralwidget)
            value_label.setObjectName(f"valueLabel_{i}")
            value_label.setGeometry(QRect(self.slidePositions[i] - 10, 365, 50, 15))
            value_label.setStyleSheet("""
                color: rgb(206, 255, 92);
                font: 8pt "MS Shell Dlg 2";
                text-align: center;
            """)
            value_label.setText("0")
            self.valueLabels.append(value_label)

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

        self.pushButton_calibrar = QPushButton(self.centralwidget)
        self.pushButton_calibrar.setGeometry(QRect(370, 240, 93, 41))
        self.pushButton_calibrar.setCursor(QCursor(Qt.PointingHandCursor))
        self.pushButton_calibrar.setStyleSheet("""
            color: rgb(206, 255, 92);
            font: 10pt "MS Shell Dlg 2";
        """)
        self.pushButton_calibrar.setText("Calibrar")

        self.pushButton_parar_calibracao = QPushButton(self.centralwidget)
        self.pushButton_parar_calibracao.setGeometry(QRect(468, 240, 93, 41))
        self.pushButton_parar_calibracao.setCursor(QCursor(Qt.PointingHandCursor))
        self.pushButton_parar_calibracao.setStyleSheet("""
            color: rgb(206, 255, 92);
            font: 9pt "MS Shell Dlg 2";
        """)
        self.pushButton_parar_calibracao.setText("Parar Calib.")

        self.label_imagem = QLabel(self.centralwidget)
        self.label_imagem.setGeometry(QRect(390, 290, 221, 141))

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
        self.pushButton_calibrar.clicked.connect(self.onCalibrarClicked)
        self.pushButton_parar_calibracao.clicked.connect(self.onPararCalibracaoClicked)

        self.pushButton_parar.setEnabled(False)
        self.pushButton_parar_calibracao.setEnabled(False)

    def loadConfigs(self):
        """Carrega configurações do arquivo configs.glv"""
        try:
            with open('configs.glv', 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Erro ao carregar configurações: {e}")
            # Retorna configurações padrão
            return {
                "com_port": "COM9",
                "fingers": [
                    {"name": "D0", "key": "", "threshold": 630},
                    {"name": "D1", "key": "", "threshold": 480},
                    {"name": "D2", "key": "", "threshold": 480},
                    {"name": "D3", "key": "", "threshold": 480},
                    {"name": "D4", "key": "", "threshold": 600}
                ]
            }

    def saveConfigs(self):
        """Salva configurações no arquivo configs.glv"""
        try:
            # Atualiza configurações com valores atuais da UI
            self.configs["com_port"] = self.lineEdit_com.text()

            for i in range(5):
                self.configs["fingers"][i]["key"] = self.fingerInputs[i].text()
                # Manter o threshold atual (não alterar pelo botão Salvar)
                # Os thresholds são alterados apenas pelos botões OK individuais

            with open('configs.glv', 'w', encoding='utf-8') as f:
                json.dump(self.configs, f, indent=4, ensure_ascii=False)

            print("Configurações salvas com sucesso!")
            return True
        except Exception as e:
            print(f"Erro ao salvar configurações: {e}")
            return False

    def loadConfigsToUI(self):
        """Carrega configurações para a interface"""
        try:
            self.lineEdit_com.setText(self.configs["com_port"])

            for i in range(5):
                if i < len(self.configs["fingers"]):
                    finger_config = self.configs["fingers"][i]
                    self.fingerInputs[i].setText(finger_config.get("key", ""))
                    # Converter valor bruto do potenciômetro para porcentagem do slider
                    threshold_bruto = finger_config.get("threshold", 0)
                    slider_value = int((threshold_bruto / 1024.0) * 100)
                    self.sliders[i].setValue(slider_value)
        except Exception as e:
            print(f"Erro ao carregar configurações para UI: {e}")

    def updateSliders(self, data):
        if isinstance(data, list) and len(data) == 2:
            finger_values, raw_values = data

            # Atualizar sliders
            for i, value in enumerate(finger_values):
                if i < len(self.sliders):
                    current_value = self.sliders[i].value()
                    if abs(current_value - value) > 2:
                        self.sliders[i].setValue(int(value))

            # Atualizar labels dos valores brutos
            for i, raw_value in enumerate(raw_values):
                if i < len(self.valueLabels):
                    self.valueLabels[i].setText(str(raw_value))
        else:
            # Compatibilidade com formato antigo (apenas finger_values)
            finger_values = data
            for i, value in enumerate(finger_values):
                if i < len(self.sliders):
                    current_value = self.sliders[i].value()
                    if abs(current_value - value) > 2:
                        self.sliders[i].setValue(int(value))

    def onOkClicked(self, index):
        slider_value = self.sliders[index].value()
        finger_key = self.fingerInputs[index].text()
        # Pegar o valor atual do potenciômetro mostrado na label
        current_raw_value = int(self.valueLabels[index].text()) if self.valueLabels[index].text().isdigit() else 0
        print(
            f"OK {index} clicado - Slider D{index} valor: {slider_value}%, Valor atual potenciômetro: {current_raw_value}, Tecla: '{finger_key}'")

        # Salva o valor atual do potenciômetro como threshold
        if index < len(self.configs["fingers"]):
            self.configs["fingers"][index]["threshold"] = current_raw_value
            self.configs["fingers"][index]["key"] = finger_key
            self.saveConfigs()

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

        # Salva todas as configurações
        if self.saveConfigs():
            QMessageBox.information(self, "Sucesso", "Configurações salvas com sucesso!")
        else:
            QMessageBox.warning(self, "Erro", "Erro ao salvar configurações!")

    def onIniciarClicked(self):
        if self.arduino_thread is None or not self.arduino_thread.isRunning():
            com_port = self.lineEdit_com.text() or "COM9"
            print(f"Iniciando comunicação com Arduino na porta {com_port}...")

            self.arduino_thread = ArduinoThread(com_port, self.configs)
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

    def onCalibrarClicked(self):
        if self.calibration_thread is None or not self.calibration_thread.isRunning():
            com_port = self.lineEdit_com.text() or "COM9"
            print(f"Iniciando calibração na porta {com_port}...")

            self.calibration_thread = CalibrationThread(com_port, self.configs)
            self.calibration_thread.running = True

            self.calibration_thread.finger_values_updated.connect(self.updateSliders)

            self.calibration_thread.start()

            self.pushButton_calibrar.setText("Calibrando...")
            self.pushButton_calibrar.setEnabled(False)
            self.pushButton_parar_calibracao.setEnabled(True)
            self.pushButton_iniciar.setEnabled(False)  # Desabilita iniciar durante calibração
        else:
            print("Calibração já está executando!")

    def onPararCalibracaoClicked(self):
        print("Parando calibração...")

        if self.calibration_thread and self.calibration_thread.isRunning():
            try:
                self.calibration_thread.finger_values_updated.disconnect(self.updateSliders)
            except:
                pass

            self.calibration_thread.stop()
            self.calibration_thread.wait(2000)

            if self.calibration_thread.isRunning():
                self.calibration_thread.terminate()

        self.pushButton_calibrar.setText("Calibrar")
        self.pushButton_calibrar.setEnabled(True)
        self.pushButton_parar_calibracao.setEnabled(False)
        self.pushButton_iniciar.setEnabled(True)  # Reabilita iniciar

        print("Calibração parada.")

    def closeEvent(self, event):
        # Finaliza thread principal se estiver rodando
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

        # Finaliza thread de calibração se estiver rodando
        if self.calibration_thread and self.calibration_thread.isRunning():
            print("Finalizando calibração...")

            try:
                self.calibration_thread.finger_values_updated.disconnect(self.updateSliders)
            except:
                pass

            self.calibration_thread.stop()
            self.calibration_thread.wait(2000)

            if self.calibration_thread.isRunning():
                self.calibration_thread.terminate()

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