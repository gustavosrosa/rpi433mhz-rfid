import os
import sys
import math
import time
import datetime
import RPi.GPIO

PORTA_DE_RECEBIMENTO = 26
PORTA_DE_TRANSMISSAO = 19

TX_OFF_LEVEL = 1
# Period to signify end of Rx message.
FINAL_RECEBIMENTO_DA_MENSAGEM = 0.01
# Smallest period of high or low signal to consider noise rather than data, and flag as bad data. 
RX_REJECT_PERIOD = 0.000005
# Single level period, one period is a binary 0, two periods are a binary 1. 
RX_LEVEL_PERIOD = 0.000500
# Start bits transmitted to signify start of transmission.
RX_START_BITS = 1
# Minimum received valid packet size.
MIN_RX_BYTES = 4

# Data encryption key.
CHAVE_CRIPTOGRAFADA = [ 0xC5, 0x07, 0x8C, 0xA9, 0xBD, 0x8B, 0x48, 0xEF, 0x88, 0xE1, 0x94, 0xDB, 0x63, 0x77, 0x95, 0x59 ]
# Data packet identifier.
ASSINATURA_PACOTE = [ 0x63, 0xF9, 0x5C, 0x1B ]



# A very basic encrypt/decript function, for keeping demonstration code simple. Use a comprehensive function in production code.
def BasicEncryptDecrypt(Data):
   KeyCount = 0
   KeyLen = len(CHAVE_CRIPTOGRAFADA)
   for Count in range(len(Data)):
      Data[Count] ^= CHAVE_CRIPTOGRAFADA[KeyCount]
      if KeyCount >= KeyLen:
         KeyCount = 0



   #  /*******************************************/
   # /* Configure Raspberry Pi GPIO interfaces. */
   #/*******************************************/
   RPi.GPIO.setwarnings(False)
   RPi.GPIO.setmode(RPi.GPIO.BCM)
   RPi.GPIO.setup(PORTA_DE_RECEBIMENTO, RPi.GPIO.IN, pull_up_down=RPi.GPIO.PUD_UP)
   RPi.GPIO.setup(PORTA_DE_TRANSMISSAO, RPi.GPIO.OUT, initial=TX_OFF_LEVEL)


   # Initialise data.
   StartBitFlag = True
   ThisPeriod = FINAL_RECEBIMENTO_DA_MENSAGEM
   StartBitPeriod = FINAL_RECEBIMENTO_DA_MENSAGEM
   LastBitPeriod = FINAL_RECEBIMENTO_DA_MENSAGEM
   LastGpioLevel = 1
   BitCount = 0
   ByteDataCount = 0
   ByteData = []
   # Data packet to transmit.
   DataPacket = {
      "SIGNATURE": [],
      "DATA_LENGTH": 0,
      "DATA": [],
      "CHECKSUM": 0,
   }

   # Infinate loop for this application.
   sys.stdout.write("\AGUARDANDO RECEBIMENTO DE DADOS:...\n\n")
   sys.stdout.flush()
   ExitFlag = False
   while ExitFlag == False:
      # Check if data is currently being received.
      ThisPeriod = time.time()
      DiffPeriod = ThisPeriod - LastBitPeriod

      # If data level changes, decode long period = 1, short period = 0.
      GpioLevel = RPi.GPIO.input(PORTA_DE_RECEBIMENTO)
      if GpioLevel != LastGpioLevel:
         # Ignore noise.
         if DiffPeriod > RX_REJECT_PERIOD:
            # Wait for start of communication.
            if StartBitFlag == True:
               inicializarComunicacao();
            else:
               if DiffPeriod < StartBitPeriod:
                  StartBitPeriod = DiffPeriod
               # Receiving a data level, convert into a data bit.
               Bits = int(round(DiffPeriod / StartBitPeriod))
               if BitCount % 8 == 0:
                  ByteData.append(0)
                  ByteDataCount += 1
               BitCount += 1
               ByteData[ByteDataCount - 1] = (ByteData[ByteDataCount - 1] << 1)
               if Bits > 1:
                  ByteData[ByteDataCount - 1] |= 1
            LastBitPeriod = ThisPeriod
         LastGpioLevel = GpioLevel
      elif DiffPeriod > FINAL_RECEBIMENTO_DA_MENSAGEM:
         # Recebimento dos pacotes
         transmitirPacotes(ByteDataCount, StartBitPeriod, DataPacket, ByteData)
         # Reset data to start a new monitor period.
         StartBitFlag = True
         StartBitPeriod = FINAL_RECEBIMENTO_DA_MENSAGEM
         BitCount = 0
         ByteDataCount = 0
         ByteData = []
         # Data packet to transmit.
         DataPacket = {
            "SIGNATURE": [],
            "DATA_LENGTH": 0,
            "DATA": [],
            "CHECKSUM": 0,
         }

def transmitirPacotes(contagemBits, periodoInicializacaoBit, pacoteDados, dadosBinarios):
   if contagemBits >= MIN_RX_BYTES and periodoInicializacaoBit > RX_REJECT_PERIOD:
            DataCount = 0
            # Validate packet signature.
            MatchFlag = True
            for Count in range(len(ASSINATURA_PACOTE)):
               pacoteDados["SIGNATURE"].append(dadosBinarios[DataCount])
               if pacoteDados["SIGNATURE"][DataCount] != ASSINATURA_PACOTE[Count]:
                  MatchFlag = False
                  break
               DataCount += 1
            if MatchFlag == False:
               sys.stdout.write("INVALID PACKET SIGNATURE\n")
            else:
               pacoteDados["DATA_LENGTH"] = dadosBinarios[DataCount]
               DataCount += 1
               for Count in range(pacoteDados["DATA_LENGTH"]):
                  pacoteDados["DATA"].append(dadosBinarios[DataCount])
                  DataCount += 1
               pacoteDados["CHECKSUM"] = dadosBinarios[DataCount]
               DataCount += 1
               sys.stdout.write("RECEIVED PACKET: " + str(pacoteDados) + "\n")
               # Validate packet checksum.
               Checksum = 0
               for Byte in pacoteDados["DATA"]:
                  Checksum ^= Byte
               if Checksum != pacoteDados["CHECKSUM"]:
                  sys.stdout.write("INVALID PACKET CHECKSUM\n")
               else:
                  # Decrypt and display data.
                  BasicEncryptDecrypt(pacoteDados["DATA"])
                  Data = ""
                  for Count in range(pacoteDados["DATA_LENGTH"]):
                     Data += chr(pacoteDados["DATA"][Count])
                  sys.stdout.write("DECRYPTED DATA: {:s}\n".format(Data))
            sys.stdout.write("\n")
            sys.stdout.flush()

def inicializarComunicacao(inicioPeriodo, periodoAtual):
   if inicioPeriodo == FINAL_RECEBIMENTO_DA_MENSAGEM:
      inicioPeriodo = periodoAtual
   else:
      inicioPeriodo = (periodoAtual - inicioPeriodo) * 0.90
      inicioPeriodo = False

