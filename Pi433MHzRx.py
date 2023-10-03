#!/usr/bin/python
# /\ este comentário acima é necessário para o interpretador do raspberry.

#/************************************************************************************************************************/
#/* Pi433MHzRx - Script para receber dados fornecidos em um modulo 433MHz.                                               */
#/* -------------------------------------------------------------------------------------------------------------------- */
#/* Exemplo do tipo de estrutura de dados recomendada para recepção:                                                     */
#/* ASSINATURA [4 bytes] -  Identificador unico para ser enviado junto com o pacote de dados.                            */
#/* COMPRIMENTO DADOS [1 byte] -  Número total de bytes do tamanho da mensagem sendo transmitida.                        */
#/* DADOS [1-255 bytes] -  Uma lista com os dados que são enviados encriptados. (*só pode ter 255 bytes??)               */ # provavelmente pq o comprimento só comporta 1 byte de tamanho
#/* CHECKSUM [1 byte] -  Um valor de checksum dos dados enviados para verificar integridade.                             */
#/************************************************************************************************************************/


import os
import sys
import math # *Precisa mesmo de todas essas bibliotecas sendo importadas sem uso aqui?
import time
import datetime
import RPi.GPIO


#/* -------------------------------------------------------------------------------------------------------------------- */
# Definição das constantes (*elas devem basicamente ser sincronizadas com as do programa transmissor.)
#/* -------------------------------------------------------------------------------------------------------------------- */

# Define o pino GPIO conectado ao receptor 433MHz.
PINO_GPIO_RX = 26
# Define o pino GPIO conectado ao transmissor 433MHz.
PINO_GPIO_TX = 19


# Nível GPIO para desligar o transmissor. (*está invertido pelo possível uso de um NPN, caso não usar, inverte-lo)
NIVEL_TX_OFF = 1


# Período de cada nível único (em segundos), ![um período é um "0" binário, dois períodos são um "1" binário].
# *Por que é um valor de período binário diferente do código Tx, não deveria ser igual?
# *Caralho adivinha, essa porra de valor também não foi utilizada no código abaixo,
# aparentemente o programa identifica automaticamente qual o período de transmissão, então pra que essa porra tá aqui??
PERIODO_NIVEL_RX = 0.000500
# Período de sleep (em segundos) para considerar o fim da mensagem de dados Rx.
PERIODO_FIM_RX = 0.01
# Menor período de sinal alto ou baixo para considerar como ruído.
#  ao invés de dados, e sinalizar como dados ruins.
PERIODO_REJEITAR_RX = 0.000005


# Quantidade de vezes fazendo a transmissão de bits iniciais para considerar o começo da transmissão.
# *Essa porra de variável nem é usada nessa versão de código de Rx, por que tá aqui?
BITS_INICIAIS_RX = 1
# Número mínimo de bytes de dados recebidos para serem considerados dados válidos.
MINIMO_BYTES_RX = 4


# Chave de encriptação de dados. (Usada no método de encriptação aplicado aqui,
# pode ser modificada ou trocada de acordo com nossa vontade ou necessidade, só precisa combinar com a do programa Tx)
CHAVE_CRIPTOGRAFIA = [ 0xC5, 0x07, 0x8C, 0xA9, 0xBD, 0x8B, 0x48, 0xEF, 0x88, 0xE1, 0x94, 0xDB, 0x63, 0x77, 0x95, 0x59 ]
# Assinatura de identificação do pacote de dados (*só precisa combinar com a do programa Tx).
# São os 4 primeiros bytes a serem recebidos para serem reconhecidos como uma mensagem
ASSINATURA_PACOTE = [ 0x63, 0xF9, 0x5C, 0x1B ] # Aparentemente são só caracteres hexadecimais aleatórios ("c", "ù", "\", "ESC")


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */

# Uma função provisória de des/encriptação extremamente básica, apenas por propósitos demonstrativos.
# *Utiliza a chave para modificar os caracteres diretamente na lista com os dados que entra nessa função (PacoteDados["DADOS"]).
# *Fato curioso, nessa função não precisa declarar a variável externa como global para modificar ela,
# pois ela é uma lista nesse caso, e as variáveis listas são referências à memória que é diretamente modificada, não só sua instância.
def Descriptografa(Dados):
   ChaveCount = 0
   TamanhoChave = len(CHAVE_CRIPTOGRAFIA)
   for count in range(len(Dados)):
      Dados[count] ^= CHAVE_CRIPTOGRAFIA[ChaveCount]
      if ChaveCount >= TamanhoChave:
         ChaveCount = 0


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */

# Configuração das interfaces GPIO do Raspberry.
RPi.GPIO.setwarnings(False)
RPi.GPIO.setmode(RPi.GPIO.BCM)
RPi.GPIO.setup(PINO_GPIO_RX, RPi.GPIO.IN, pull_up_down=RPi.GPIO.PUD_UP)
RPi.GPIO.setup(PINO_GPIO_TX, RPi.GPIO.OUT, initial=NIVEL_TX_OFF)


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */

# Inicializando os dados em variáveis.
BuscaBitsIniciais = True
EstePeriodo = PERIODO_FIM_RX
PeriodoBitInicial = PERIODO_FIM_RX
PeriodoBitPassado = PERIODO_FIM_RX
NivelGpioPassado = 1
BitCount = 0
DadosByteCount = 0
DadosByte = []

# Definição do pacote de dados [em formato de dicionário] para recepção.
# Está em ordem lógica que deve chegar no receptor, primeiro a assinatura para identificar que é uma mensagem,
# depois o tamanho dos dados para se preparar, então os dados em si, e por fim o checksum para confirmação de integridade dos dados.
PacoteDados = {
   "ASSINATURA": [],
   "COMPRIMENTO_DADOS": 0,
   "DADOS": [],
   "CHECKSUM": 0,
}


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */

# -- PROGRAMA "PRINCIPAL":

# Loop infinito para a aplicação.
sys.stdout.write("\nAGUARDANDO RECEBIMENTO DE DADOS...\n\n")
sys.stdout.flush()
ExitFlag = False
while ExitFlag == False:
   # Checagem se algum dado está atualmente sendo recebido.
   EstePeriodo = time.time()
   DiferencaPeriodo = EstePeriodo - PeriodoBitPassado

#/* -------------------------------------------------------------------------------------------------------------------- */

   # *Parte do programa principal que roda procurando uma transmissão e captura quando achar.
   # *Enquanto não completar uma transmissão fica em loop nessa parte "if" do código, quando acabar cai no "elif".
   # Quando o nível de dados mudar, decodificar como "long period" = 1 binário, "short period" = 0 binário.
   NivelGpio = RPi.GPIO.input(PINO_GPIO_RX)
   if NivelGpio != NivelGpioPassado:

      # Ignorar ruído, desconsiderando variações extremamente rápidas e curtas entre os períodos.
      if DiferencaPeriodo > PERIODO_REJEITAR_RX:

         # Eperando pelo início da comunicação.
         # Enquanto BuscaBitsIniciais for TRUE ele estará buscando os dados, quando encontrar ele passará para FALSE
         if BuscaBitsIniciais == True:
            # Calculando o período de bit inicial, considerando como o período de bit para todos os bits seguintes.
            if PeriodoBitInicial == PERIODO_FIM_RX:
               PeriodoBitInicial = EstePeriodo
            else:
               PeriodoBitInicial = (EstePeriodo - PeriodoBitInicial) * 0.90
               BuscaBitsIniciais = False
         
         # A recepção de dados foi identificada e eles serão recebidos.
         else:
            if DiferencaPeriodo < PeriodoBitInicial:
               PeriodoBitInicial = DiferencaPeriodo

            # Recebendo um nível de dado, convertendo em um bit de dado.
            Bits = int(round(DiferencaPeriodo / PeriodoBitInicial))

            # *Fazendo toda a captura e armazenamento dos bits de dados em "DadosByte", desse jeito aí sei lá como, apenas funciona.
            # *Com a contagem de bytes em "DadosByteCount", que depois é passada para a "DadosCount" na parte "elif" do código.
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
   
   # *Parte do programa que se for True e cair nesse "elif" é o fim da recepção de dados.
   elif DiferencaPeriodo > PERIODO_FIM_RX:
      # "if" dados NÃO foram insuficientes ou rejeitados, continuar.
      if DadosByteCount >= MINIMO_BYTES_RX and PeriodoBitInicial > PERIODO_REJEITAR_RX:

         # Validando a assinatura (identificador) do pacote de dados.
         DadosCount = 0
         ValidadeAssinatura = True
         for count in range(len(ASSINATURA_PACOTE)):
            PacoteDados["ASSINATURA"].append(DadosByte[DadosCount])
            if PacoteDados["ASSINATURA"][DadosCount] != ASSINATURA_PACOTE[count]:
               ValidadeAssinatura = False
               break
            DadosCount += 1


         # Confirmando se a assinatura era válida ou não, cai no "if" caso não seja.
         if ValidadeAssinatura == False:
            sys.stdout.write("ASSINATURA DE PACOTE INVALIDA\n")

         # Caso seja válida, prosseguir neste "else" com o tratamento dos dados recebidos.
         else:
            # Registrando o comprimento da mensagem de dados.
            PacoteDados["COMPRIMENTO_DADOS"] = DadosByte[DadosCount]
            DadosCount += 1
            for count in range(PacoteDados["COMPRIMENTO_DADOS"]):
               PacoteDados["DADOS"].append(DadosByte[DadosCount])
               DadosCount += 1
            
            # Fazendo o cálculo do valor de checksum dos dados.
            PacoteDados["CHECKSUM"] = DadosByte[DadosCount]
            DadosCount += 1
            sys.stdout.write("PACOTE RECEBIDO: " + str(PacoteDados) + "\n")

            # Validando o checksum do pacote de dados.
            Checksum = 0
            for Byte in PacoteDados["DADOS"]:
               Checksum ^= Byte
            
            if Checksum != PacoteDados["CHECKSUM"]:
               sys.stdout.write("CHECKSUM DE PACOTE INVALIDO\n")
            else:
               # Caso o checksum se prove como correto, então desencriptar e exibir os dados.
               Descriptografa(PacoteDados["DADOS"])

               # Coloca os dados descriptografados em uma string e por fim exibe-os.
               Dados = ""
               for count in range(PacoteDados["COMPRIMENTO_DADOS"]):
                  Dados += chr(PacoteDados["DADOS"][count])
               sys.stdout.write("DADOS DESCRIPTOGRAFADOS: {:s}\n".format(Dados))

         sys.stdout.write("\n")
         sys.stdout.flush()

#/* -------------------------------------------------------------------------------------------------------------------- */

      # Após o fim de uma recepção de dados, resetar as variáveis e o
      # pacote de dados para iniciar um novo período de monitoramento.
      BuscaBitsIniciais = True
      PeriodoBitInicial = PERIODO_FIM_RX
      BitCount = 0
      DadosByteCount = 0
      DadosByte = []
      
      PacoteDados = {
         "ASSINATURA": [],
         "COMPRIMENTO_DADOS": 0,
         "DADOS": [],
         "CHECKSUM": 0,
      }


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */
