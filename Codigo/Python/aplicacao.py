import serial
import time
import pyautogui


def conectar_arduino(porta='COM9'):
    try:
        arduino = serial.Serial(porta, 115200, timeout=0.01)
        time.sleep(1)
        print(f"Conectado na porta {porta} a 115200 baud")
        return arduino
    except:
        print(f"Erro ao conectar na porta {porta}")
        return None


def main():
    arduino = conectar_arduino('COM9')

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0
    sensitivity = 0.8

    if arduino:
        try:
            while True:
                if arduino.in_waiting > 0:
                    linha = arduino.readline().decode().strip()
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

                        if "D0:" in linha:
                            try:
                                valor_d0 = int(linha.split("D0:")[1].split()[0])
                                if valor_d0 < 630:
                                    print("Dedo indicador (D0) detectado")
                            except (ValueError, IndexError):
                                pass

                        if "D1:" in linha:
                            try:
                                valor_d1 = int(linha.split("D1:")[1].split()[0])
                                if valor_d1 < 480:
                                    print("Dedo médio (D1) detectado")
                            except (ValueError, IndexError):
                                pass

                        if "D2:" in linha:
                            try:
                                valor_d2 = int(linha.split("D2:")[1].split()[0])
                                if valor_d2 < 480:
                                    print("Dedo anelar (D2) detectado")
                            except (ValueError, IndexError):
                                pass

                        if "D3:" in linha:
                            try:
                                valor_d3 = int(linha.split("D3:")[1].split()[0])
                                if valor_d3 < 480:
                                    print("Dedo polegar (D3) detectado")
                            except (ValueError, IndexError):
                                pass

                        if "D4:" in linha:
                            try:
                                valor_d4 = int(linha.split("D4:")[1].split()[0])
                                if valor_d4 < 600:
                                    print("Dedo mindinho (D4) detectado")
                            except (ValueError, IndexError):
                                pass

                time.sleep(0.001)

        except KeyboardInterrupt:
            pass
        except pyautogui.FailSafeException:
            pass
        finally:
            arduino.close()
    else:
        print("Verifique conexão e porta COM")


if __name__ == "__main__":
    main()