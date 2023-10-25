from tkinter import *
import customtkinter

root = customtkinter.CTk()

# Aparência da tela - Tema
customtkinter.set_appearance_mode("Dark")

# Tamanho da janela
root.geometry("400x240")
root.title("CRIPPER - Comunicação via RF")

root.eval('tk::PlaceWindow . center')

label1 = customtkinter.CTkLabel(root, text="Estabelecer Comunicação")
label1.pack(padx=20, pady=20)

newDevice = customtkinter.CTkButton(master=root, text="Novo Dispositivo")
newDevice.pack(padx=20, pady=20)

recognizedDevice = customtkinter.CTkButton(master=root, text="Dispositivo Conhecido")
recognizedDevice.pack(padx=20, pady=20)

# Proibe redimensionamento de tela
root.resizable(False,False)

root.mainloop()