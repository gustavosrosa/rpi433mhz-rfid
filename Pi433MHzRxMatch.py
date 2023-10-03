#!/usr/bin/python
# /\ este comentário acima é necessário para o interpretador do raspberry.

#/************************************************************************************************************************/
#/* Pi433MHzRxMatch - 433MHz Reconhecimento e reação aos dados recebidos.                                                */
#/* -------------------------------------------------------------------------------------------------------------------- */
#/* Script para monitorar em 433MHz e scripts rodando para tipos de dados reconhecidos.                                  */
#/* Esse script presume a codificação de dados como "short level" = binary 0, e "long level" = binary 1.                 */
#/************************************************************************************************************************/


import os
import sys
import math
import time
import datetime
import RPi.GPIO


#/* -------------------------------------------------------------------------------------------------------------------- */
# Definição das constantes (*elas devem basicamente ser sincronizadas com as do programa transmissor.)
#/* -------------------------------------------------------------------------------------------------------------------- */

# Pino GPIO conectado ao receptor 433MHz:
PINO_GPIO_RX = 26
# Pino GPIO conectado ao transmissor 433MHz:
PINO_GPIO_TX = 19


# Nível GPIO para desligar o transmissor.
NIVEL_TX_OFF = 1
# Período sem nenhum dado RX para considerar o fim da mensagem de dados RX.
PERIODO_FIM_RX = 0.01
# Menor período de sinal alto ou baixo para considerar ruído ao invés de dados, e sinalizar como dados ruins.
PERIODO_REJEITAR_RX = 0.000005
# Número mínimo de bytes de dados recebidos para serem considerados dados válidos.
MINIMO_BYTES_RX = 4
# Registrar no "Log" dados recebidos que não derem "match". 
REGISTRAR_SEM_MATCH = False


# Campos de dados da configuração:
CONFIG_ELEMENTO_MATCH = 0
CONFIG_ELEMENTO_COMANDO = 1


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */

# Ler o arquivo de dados de configuração.
def CarregaConfig():
   DadosConfig = []
   Arquivo = open("Pi433MHzRxMatch.ini", 'r', 0)
   LinhaDeTexto = "."
   while LinhaDeTexto != "":
      LinhaDeTexto = Arquivo.readline().replace("\n", "")
      if LinhaDeTexto != "":
         Elemento = LinhaDeTexto.split("=")
         DadosConfig.append(Elemento)
   Arquivo.close()
   return DadosConfig


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */

# Configuração das interfaces GPIO do Raspberry.
RPi.GPIO.setwarnings(False)
RPi.GPIO.setmode(RPi.GPIO.BCM)
RPi.GPIO.setup(PINO_GPIO_RX, RPi.GPIO.IN, pull_up_down=RPi.GPIO.PUD_UP)
RPi.GPIO.setup(PINO_GPIO_TX, RPi.GPIO.OUT, initial=NIVEL_TX_OFF)


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */

# Inicializando os dados.
BuscaBitsIniciais = True
EstePeriodo = PERIODO_FIM_RX
PeriodoBitInicial = PERIODO_FIM_RX
PeriodoBitPassado = PERIODO_FIM_RX
NivelGpioPassado = 1
BitCount = 0
DadosByteCount = 0
DadosByte = []


# Lendo os dados de configuração.
DadosConfig = CarregaConfig()


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */

# Loop infinito para a aplicação.
sys.stdout.write("\nAGUARDANDO RECEBIMENTO DE DADOS...\n\n")
sys.stdout.flush()
ExitFlag = False
while ExitFlag == False:
   # Checagem se algum dado está atualmente sendo recebido.
   EstePeriodo = time.time()
   DiferencaPeriodo = EstePeriodo - PeriodoBitPassado

   # Se o nível de dados mudar, decodificar "long period" = 1, "short period" = 0.
   NivelGpio = RPi.GPIO.input(PINO_GPIO_RX)
   if NivelGpio != NivelGpioPassado:
      # Ignorar ruído.
      if DiferencaPeriodo > PERIODO_REJEITAR_RX:
         # Eperando pelo início da comunicação.
         if BuscaBitsIniciais == True:
            # Calculando o período de bit inicial, considerando como periodo para todos os bits seguintes.
            if PeriodoBitInicial == PERIODO_FIM_RX:
               PeriodoBitInicial = EstePeriodo
            else:
               PeriodoBitInicial = (EstePeriodo - PeriodoBitInicial) * 0.90
               BuscaBitsIniciais = False
         else:
            if DiferencaPeriodo < PeriodoBitInicial:
               PeriodoBitInicial = DiferencaPeriodo

            # Recebendo um nível de dado, convertendo em um bit de dado.
            Bits = int(round(DiferencaPeriodo / PeriodoBitInicial))
            if BitCount % 8 == 0:
               DadosByte.append(0)
               DadosByteCount += 1
            BitCount += 1
            DadosByte[DadosByteCount - 1] = (DadosByte[DadosByteCount - 1] << 1)
            if Bits > 1:
                DadosByte[DadosByteCount - 1] |= 1
         PeriodoBitPassado = EstePeriodo
      NivelGpioPassado = NivelGpio

#/* -------------------------------------------------------------------------------------------------------------------- */
   
   # Fim da recepção de dados.
   elif DiferencaPeriodo > PERIODO_FIM_RX:
      if DadosByteCount >= MINIMO_BYTES_RX and PeriodoBitInicial > PERIODO_REJEITAR_RX:
         # Formata dos bytes de dados em formato hexadecimal.
         StringDados = ""
         DadosCount = 0
         for Byte in DadosByte:
            StringDados += "{:02X}".format(Byte)
            DadosCount += 1

         # Checando se há "match" dos dados, checando pelo início dos dados pelo número de bytes nos dados de conig, ignorando o resto dos dados recebidos.
         Match = False
         for ConfigElemento in DadosConfig:
            ComprimentoConfigMatch = len(ConfigElemento[CONFIG_ELEMENTO_MATCH])
            if DadosByteCount * 2 >= ComprimentoConfigMatch and StringDados[:ComprimentoConfigMatch] == ConfigElemento[CONFIG_ELEMENTO_MATCH]:
               Match = True
               break

         # Resposta ao "match" dos dados.
         if Match == True:
            Now = datetime.datetime.now()
            sys.stdout.write(Now.strftime("%Y-%m-%d %H:%M:%S\n"))
            sys.stdout.write("MATCH: " + str(ConfigElemento) + "\n")
            sys.stdout.write("PERIODO DE BIT INICIAL {:f}\n".format(PeriodoBitInicial))
            sys.stdout.write(StringDados + "\n")
            sys.stdout.flush()
            os.system(ConfigElemento[CONFIG_ELEMENTO_COMANDO])
            sys.stdout.write("\n\n")
            sys.stdout.flush()
         elif REGISTRAR_SEM_MATCH == True:
            Now = datetime.datetime.now()
            sys.stdout.write(Now.strftime("%Y-%m-%d %H:%M:%S\n"))
            sys.stdout.write("SEM MATCH: " + str(ConfigElemento) + "\n")
            sys.stdout.write("PERIODO DE BIT INICIAL {:f}\n".format(PeriodoBitInicial))
            sys.stdout.write(StringDados + "\n")
            sys.stdout.flush()

      # Resetando dados para iniciar um novo período de monitoramento.
      BuscaBitsIniciais = True
      PeriodoBitInicial = PERIODO_FIM_RX
      BitCount = 0
      DadosByteCount = 0
      DadosByte = []


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */
