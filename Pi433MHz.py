#!/usr/bin/python
# /\ este comentário acima é necessário para o interpretador do raspberry.

#/************************************************************************************************************************/
#/* Pi433MHz - Script para monitoramento em 433MHz e exibição dos pacotes de dados recebidos.                            */
#/* -------------------------------------------------------------------------------------------------------------------- */
#/* Parametros ajustados mostram a quantidade de ruído para auxiliar                                                     */
#/* no posicionamento do módulo para longe de áreas com interferência de RF.                                             */
#/************************************************************************************************************************/


import os
import sys
import math # *Precisa mesmo de todas essas bibliotecas sendo importadas sem uso aqui?
import time
import hashlib
import datetime
import RPi.GPIO


#/* -------------------------------------------------------------------------------------------------------------------- */
# Definição das constantes.
#/* -------------------------------------------------------------------------------------------------------------------- */

# Define o pino GPIO conectado ao receptor 433MHz.
PINO_GPIO_RX = 26
# Define o pino GPIO conectado ao transmissor 433MHz.
PINO_GPIO_TX = 19


# ** Essa constante está invertida pelo possível uso de um NPN, caso não usar, inverte-la.**
# Nível GPIO para desligar o transmissor.
NIVEL_TX_OFF = 1


# Quando convertendo sinal 5V (modulo) para sinal 3.3V (rasp) para o GPIO do Raspberry, o transistor NPN inverte o sinal.
# (*Só está no código pois o desenvolvedor usou um transistor no circuito que inverte o sinal, se não for o caso
# é só mudar o valor para "0" ou então remover completamente do código)
INVERTER_BIT_RX = 1
# Período sem nenhum dado RX para considerar o fim da mensagem de dados RX.
# (*No código original esse valor é 1, não sei qual propósito e qual vale mais a pena manter)
PERIODO_FIM_RX = 0.01
# Menor período de sinal alto ou baixo para considerar ruído ao invés de dados, e sinalizar como dados ruins.
# (*No código original esse valor é 0.000020, não sei qual propósito e qual vale mais a pena manter)
PERIODO_REJEITAR_RX = 0.000005


# Bits iniciais transmitidos para considerar o começo da recepção.
BITS_INICIAIS_RX = 1
# Tamanho da assinatura Rx, quantidade de valores hexadecimais para usar como assinatura.
TAMANHO_ASSINATURA_RX = 4


# Colocando linhas de dados ruins no arquivo log.
REGISTRAR_DADOS_RUINS = False


# Nomes dos campos de dados Rx.
SEQUENCIA_DADOS = 0
PINO_DADOS_RX = 1
NIVEL_DADOS = 2
PERIODO_DADOS = 3


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */

# Classe para armazenar iterações do pacote de dados
class RxPacote:
   BitsIniciaisCount = BITS_INICIAIS_RX
   AltBitsIniciaisCount = BITS_INICIAIS_RX
   DadosCount = 0
   Dados = []
   PeriodoBit = 0
   NivelGpioPassado = INVERTER_BIT_RX
   AssinaturasRx = {}


# Inicializa dados da aplicação.
def DataInit(EstePacoteRx):
   EstePacoteRx.BitsIniciaisCount = BITS_INICIAIS_RX
   EstePacoteRx.AltBitsIniciaisCount = BITS_INICIAIS_RX
   EstePacoteRx.DadosCount = 0
   EstePacoteRx.Dados = []
   EstePacoteRx.PeriodoBit = 0
   EstePacoteRx.NivelGpioPassado = INVERTER_BIT_RX


# Escreve uma linha no arquivo log
def EscreveLinhaLog(ArquivoLog, LinhaLog):
   sys.stdout.write(LinhaLog)
   ArquivoLog.write(LinhaLog)


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */

# Configuração das interfaces GPIO do Raspberry.
RPi.GPIO.setwarnings(False)
RPi.GPIO.setmode(RPi.GPIO.BCM)
RPi.GPIO.setup(PINO_GPIO_RX, RPi.GPIO.IN, pull_up_down=RPi.GPIO.PUD_UP)
# *\/Não tinha no código original pois não tem funcionalidade para transmissão.
RPi.GPIO.setup(PINO_GPIO_TX, RPi.GPIO.OUT, initial=NIVEL_TX_OFF)


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */

# Inicializando uma nova caputra de pacote de dados.
EstePacoteRx = RxPacote
DataInit(EstePacoteRx)

#/* -------------------------------------------------------------------------------------------------------------------- */

# Loop infinito para a aplicação.
ExitFlag = False
RuidoCount = 0
SegundoPassado = 0
sys.stdout.write("\nAGUARDANDO RECEBIMENTO DE DADOS...\n\n")
sys.stdout.flush()

while ExitFlag == False:
   # Checagem se algum dado está atualmente sendo recebido.
   EstePeriodo = time.time()
   DiferencaPeriodo = EstePeriodo - EstePacoteRx.PeriodoBit
   EsteSegundo = int(EstePeriodo)

   if EsteSegundo != SegundoPassado:
      sys.stdout.write(" RUIDO: {:d}      \r".format(RuidoCount))
      sys.stdout.flush()
      RuidoCount = 0
      SegundoPassado = EsteSegundo

#/* -------------------------------------------------------------------------------------------------------------------- */

   # Checando se ainda não é o fim da mensagem de dados.
   if len(EstePacoteRx.Dados) == 0 or DiferencaPeriodo < PERIODO_FIM_RX:
      # Se o nível de dados mudar, "logar" informações sobre os dados recebidos.
      # Serão decodificados assim que os dados Rx estiverem completos.
      NivelGpio = RPi.GPIO.input(PINO_GPIO_RX)
      if NivelGpio != EstePacoteRx.NivelGpioPassado:
         if DiferencaPeriodo < PERIODO_REJEITAR_RX:
            RuidoCount += 1
         else:
            EstePacoteRx.Dados.append([EstePacoteRx.DadosCount, PINO_GPIO_RX, EstePacoteRx.NivelGpioPassado, DiferencaPeriodo])
            EstePacoteRx.DadosCount += 1
            # Registrando o período para calcular o tempo entre o fim desse período e o início do próximo,
            # indicando um sinal longo HIGH ou curto LOW.
            EstePacoteRx.PeriodoBit = EstePeriodo
            # Registrando também qual o nível de dados atual para comparar com o próximo.
            EstePacoteRx.NivelGpioPassado = NivelGpio

#/* -------------------------------------------------------------------------------------------------------------------- */

   # A mensagem de dados chegou ao fim.
   else:
      # Nova entrada no log.
      EntradaLog = ""
      DadosRuinsFlag = False

      # Fim dos dados detectado, decodificar dados.
      Agora = datetime.datetime.now()

      # Registrar a data e hora dos dados Rx.
      EntradaLog += Agora.strftime("%Y-%m-%d %H:%M:%S\n")

      # Calcular o tamanho dos dados uma vez, para usar depois.
      TamanhoDados = len(EstePacoteRx.Dados)
      EntradaLog += "TAMANHO DOS DADOS: {:d} ".format(TamanhoDados)

      # Iterar através dos dados para encontrar o menor período por um nível high e o menor período por um nível low.
      # Isso vai ser considerado a taxa de dados Tx para sinais high e low.
      MinPeriodoBaixoSeqCount = 0
      MinPeriodoBaixo = PERIODO_FIM_RX
      MinPeriodoAltoSeqCount = 0
      MinPeriodoAlto = PERIODO_FIM_RX
      for ColunaDados in EstePacoteRx.Dados:
         # Ignorar alguns dos primeiros e últimos períodos caso eles sejam ruído.
         if ColunaDados[SEQUENCIA_DADOS] > 2 and ColunaDados[SEQUENCIA_DADOS] < TamanhoDados - 2:
            if ColunaDados[NIVEL_DADOS] == 0 and ColunaDados[PERIODO_DADOS] < MinPeriodoBaixo:
               MinPeriodoBaixoSeqCount = ColunaDados[SEQUENCIA_DADOS]
               MinPeriodoBaixo = ColunaDados[PERIODO_DADOS]
            if ColunaDados[NIVEL_DADOS] == 1 and ColunaDados[PERIODO_DADOS] < MinPeriodoAlto:
               MinPeriodoAltoSeqCount = ColunaDados[SEQUENCIA_DADOS]
               MinPeriodoAlto = ColunaDados[PERIODO_DADOS]
      EntradaLog += "PERIODO BAIXO MINIMO: [{:d}] {:f} PERIODO ALTO MINIMO: [{:d}] {:f}\n".format(MinPeriodoBaixoSeqCount, MinPeriodoBaixo, MinPeriodoAltoSeqCount, MinPeriodoAlto)
      
#/* -------------------------------------------------------------------------------------------------------------------- */

      # Checando por dados que parecam errados e exibindo um erro ao invés dos dados caso eles sejam errôneos.
      if MinPeriodoBaixo == PERIODO_FIM_RX or MinPeriodoAlto == PERIODO_FIM_RX \
         or MinPeriodoBaixo < PERIODO_REJEITAR_RX or MinPeriodoAlto < PERIODO_REJEITAR_RX:
         DadosRuinsFlag = True
         EntradaLog += "! DADOS RUINS REJEITADOS !"
      
      else:
         # Se os dados parecerem OK, então exibir os dados em vários formatos para auxiliar na decodificação dos dados.
         # Exibir dados binários e guardar grupos de 8 bits como dados de byte para uso posterior.
         EntradaLog += "\nDADOS BINARIOS:\n"
         DadosBitCount = 0
         AltDadosBitCount = 0
         DadosByteCount = 0
         AltDadosByteCount = 0
         DadosByte = []
         AltDadosByte = []
         
         if INVERTER_BIT_RX == 0:
            TesteNivel = 0
         else:
            TesteNivel = 1
         for ColunaDados in EstePacoteRx.Dados:
            if ColunaDados[PERIODO_DADOS] < PERIODO_FIM_RX:
               if ColunaDados[NIVEL_DADOS] == TesteNivel:
                  
                  # Dividindo o período de nível de dados pelo período mínimo para o nível de dados LOW para calcular quantos bits são desse nível.
                  BitCount = int(round(ColunaDados[PERIODO_DADOS] / MinPeriodoBaixo))
                  for Count in range(BitCount):
                     if EstePacoteRx.BitsIniciaisCount > 0:
                        EstePacoteRx.BitsIniciaisCount -= 1
                     else:
                        if DadosBitCount % 8 == 0:
                           DadosByte.append(0)
                           DadosByteCount += 1
                        DadosBitCount += 1
                        EntradaLog += "0"
                        DadosByte[DadosByteCount - 1] = (DadosByte[DadosByteCount - 1] << 1) + 0
               else:
                  # Dividindo o período de nível de dados pelo período mínimo para o nível de dados HIGH para calcular quantos bits são desse nível.
                  BitCount = int(round(ColunaDados[PERIODO_DADOS] / MinPeriodoAlto))
                  for Count in range(BitCount):
                     if EstePacoteRx.BitsIniciaisCount > 0:
                        EstePacoteRx.BitsIniciaisCount -= 1
                     else:
                        if DadosBitCount % 8 == 0:
                           DadosByte.append(0)
                           DadosByteCount += 1
                        DadosBitCount += 1
                        EntradaLog += "1"
                        DadosByte[DadosByteCount - 1] = (DadosByte[DadosByteCount - 1] << 1) + 1

               if BitCount <= 2:
                  if EstePacoteRx.AltBitsIniciaisCount > 0:
                     EstePacoteRx.AltBitsIniciaisCount -= 1
                  else:
                     if AltDadosBitCount % 8 == 0:
                        AltDadosByte.append(0)
                        AltDadosByteCount += 1
                     AltDadosBitCount += 1
                     if BitCount == 1:
                        AltDadosByte[AltDadosByteCount - 1] = (AltDadosByte[AltDadosByteCount - 1] << 1) + 0
                     elif BitCount == 2:
                        AltDadosByte[AltDadosByteCount - 1] = (AltDadosByte[AltDadosByteCount - 1] << 1) + 1

#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */

         # Exibindo os dados de byte em formato hexadecimal.
         EntradaLog += "\n\nDADOS HEXADECIMAIS:\n"
         DadosCount = 0
         TesteZero = 0
         for Byte in DadosByte:
            TesteZero = (TesteZero | Byte)
            EntradaLog += "{:02X} ".format(Byte)
            DadosCount += 1
            if DadosCount % 26 == 0:
               EntradaLog += "\n"
         # sinalizar todos os dados zerados como dados ruins.
         if TesteZero == 0:
            DadosRuinsFlag = True
            EntradaLog += "! DADOS RUINS REJEITADOS (ZERO) !"

         # Dados decodificados recebidos por "single bit run" = 0, "double bit run" = 1.
         EntradaLog += "\n\nDADOS HEXADECIMAIS ALTERNATIVOS:\n"
         AssinaturaRxCount = TAMANHO_ASSINATURA_RX
         AssinaturaRx = ""
         DadosCount = 0
         TesteZero = 0
         for Byte in AltDadosByte:
            TesteZero = (TesteZero | Byte)
            EntradaLog += "{:02X} ".format(Byte)
            if AssinaturaRxCount > 0:
               AssinaturaRxCount -= 1
               AssinaturaRx += "{:02X} ".format(Byte)
            DadosCount += 1
            if DadosCount % 26 == 0:
               EntradaLog += "\n"
         EntradaLog += "\n\nASSINATURA RX: {:s}".format(AssinaturaRx)
         # sinalizar dados da assinatura ruins como dados ruins.
         if AssinaturaRxCount > 0:
            DadosRuinsFlag = True
            EntradaLog += "! DADOS RUINS REJEITADOS (ASSINATURA) !"
         
         # sinalizar todos os dados zerados como dados ruins.
         if TesteZero == 0:
            DadosRuinsFlag = True
            EntradaLog += "! DADOS RUINS REJEITADOS (ZERO) !"

#/* -------------------------------------------------------------------------------------------------------------------- */

         # Exibindo os dados de byte em formato de byte (*eu acho)
         EntradaLog += "\n\nDADOS BYTE:\n"
         DadosCount = 0
         for Byte in AltDadosByte:
            EntradaLog += "{:3d} ".format(Byte)
            DadosCount += 1
            if DadosCount % 19 == 0:
               EntradaLog += "\n"


         # Exibindo pares dos dados de byte como palavras de 16 bits em formato decimal.
         EntradaLog += "\n\nDESVIO DE DADOS DE PALAVRA 0:\n"
         DadosPalavra = 0
         DadosCount = 0
         for Byte in AltDadosByte:
            if DadosCount % 2 == 0:
               DadosPalavra = Byte
            else:
               DadosPalavra = (DadosPalavra << 8) + Byte
               EntradaLog += "{:6d} ".format(DadosPalavra)

            DadosCount += 1
            if DadosCount % 20 == 0:
               EntradaLog += "\n"


         # Exibindo pares dos dados de byte como palavras de 16 bits em formato decimal, desviando (offset) os dados por um bit.
         EntradaLog += "\n\nDESVIO DE DADOS DE PALAVRA 1:\n"
         DadosPalavra = 0
         DadosCount = 0
         for Byte in AltDadosByte:
            if DadosCount % 2 == 1:
               DadosPalavra = Byte
            else:
               DadosPalavra = (DadosPalavra << 8) + Byte
               EntradaLog += "{:6d} ".format(DadosPalavra)

            DadosCount += 1
            if DadosCount % 20 == 0:
               EntradaLog += "\n"


         # Exibindo os dados de byte em formato ASCII.
         EntradaLog += "\n\nDADOS CARACTERES:\n"
         for Byte in AltDadosByte:
            EntradaLog += "{:s}".format(chr(Byte))


#/* -------------------------------------------------------------------------------------------------------------------- */

      # Resetando dados prontos para receber os próximos dados Rx.
      EntradaLog += "\n\n\n"

      if DadosRuinsFlag == True:
         RuidoCount += 1

      if DadosRuinsFlag == False or (DadosRuinsFlag == True and REGISTRAR_DADOS_RUINS == True):
         # Abrindo um arquivo log diário.
         ArquivoLog = open("LOG/{:s}_433MHz.log".format(Agora.strftime("%Y-%m-%d")), 'a', 0)
         EscreveLinhaLog(ArquivoLog, EntradaLog)
         sys.stdout.flush()
         ArquivoLog.close()

      # Inicializando uma nova captura de pacote de dados.
      DataInit(EstePacoteRx)


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */
