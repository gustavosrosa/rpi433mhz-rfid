#!/usr/bin/python
# /\ este comentário acima é necessário para o interpretador do raspberry.

#/************************************************************************************************************************/
#/* Pi433MHzTx - Script para transmitir dados fornecidos através de um modulo 433MHz.                                    */
#/* -------------------------------------------------------------------------------------------------------------------- */
#/* Exemplo do tipo de estrutura de dados recomendada para transmitissão:                                                */
#/* ASSINATURA [4 bytes] -  Identificador unico para ser enviado junto com o pacote de dados.                            */
#/* COMPRIMENTO DADOS [1 byte] -  Número total de bytes do tamanho da mensagem sendo transmitida.                        */
#/* DADOS [1-255 bytes] -  Uma lista com os dados que são enviados encriptados. (*só pode ter 255 bytes??)               */
#/* CHECKSUM [1 byte] -  Um valor de checksum dos dados enviados para verificar integridade.                             */
#/************************************************************************************************************************/
# Sobre os dados só terem 255 bytes, provavelmente pq o campo comprimento de dados só comporta 1 byte para representar o tamanho
# Então só pode ser representado por um número até 255 para caber em 1 byte (MAS esse campo de comprimento de dados só comporta 1 byte mesmo?)
# *Edit: Provavelmente só comporta 1 byte mesmo, já que na recepção de dados ele é interpretado como sendo exatamente o 5º byte a ser recebido,
# não teria como avisar o programa se o próximo byte ainda representa o "tamanho dos dados" ou se já começa a representar os "dados", então por padrão
# o programa presume que serão os dados já, limitando a 1 byte para a representação do "tamanho dos dados".
# *Obs.: Não é impossível modificar o programa para esperar 2 bytes representando o tamanho dos dados, a questão é se seria relevante fazer isso.


import os
import sys
import math # *Precisa mesmo de todas essas bibliotecas sendo importadas sem uso aqui?
import time
import hashlib
import datetime
import RPi.GPIO


#/* -------------------------------------------------------------------------------------------------------------------- */
# Definição das constantes (*elas devem basicamente ser sincronizadas com as do programa receptor.)
#/* -------------------------------------------------------------------------------------------------------------------- */

# Define o pino GPIO conectado ao receptor 433MHz.
PINO_GPIO_RX = 26
# Define o pino GPIO conectado ao transmissor 433MHz.
PINO_GPIO_TX = 19


# ** Essas constantes estão invertidas pelo possível uso de um NPN, caso não usar, inverte-las.**
# Nível GPIO para desligar o transmissor.
NIVEL_TX_OFF = 1
# Nível GPIO para ligar o transmissor.
NIVEL_TX_ON = 0


# Período de sleep (em segundos) para considerar o fim da mensagem de dados Tx.
# *vai receber aproximadamente 10 períodos com o transmissor desligado,
# assim identificando que acabou a transmissão???
PERIODO_FIM_TX = 0.01
# Período de cada nível único (em segundos), ![um período é um "0" binário, dois períodos são um "1" binário].
PERIODO_NIVEL_TX = 0.002


# Quantidade de vezes fazendo a transmissão de bits iniciais para considerar o começo da transmissão.
# **(pelo q entendi é o quanto de vezes é para transmitir um bit pelo período TX LEVEL PERIOD
# para o programa identificar o começo da transmissão, não há necessidade de modificar aparentemente,
# e provavelmente está relacionado com uma variável de mesmo valor no script de recepção, por propósitos de sincronia).
BITS_INICIAIS_TX = 1


# Numero de parâmetros esperados na linha de comando (o EXE.py e os DADOS).
PARAMETROS_COUNT = 2
# A posição deste executável.py escrito na linha de comando chamando o programa.
PARAMETRO_EXECUTAVEL = 0
# A posição dos dados escritos na linha de comando chamando o programa.
PARAMETRO_DADOS = 1


# Chave de encriptação de dados. (Usada no método de encriptação aplicado aqui,
# pode ser modificada ou trocada de acordo com nossa vontade ou necessidade, só precisa combinar com a do programa Rx)
CHAVE_CRIPTOGRAFIA = [ 0xC5, 0x07, 0x8C, 0xA9, 0xBD, 0x8B, 0x48, 0xEF, 0x88, 0xE1, 0x94, 0xDB, 0x63, 0x77, 0x95, 0x59 ]
# Assinatura de identificação do pacote de dados (*só precisa combinar com a do programa Rx).
# São os 4 primeiros bytes a serem enviados para serem reconhecidos como uma mensagem
ASSINATURA_PADRAO = [ 0x63, 0xF9, 0x5C, 0x1B ] # Aparentemente são só caracteres hexadecimais aleatórios ("c", "ù", "\", "ESC")


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */

# Transmite um byte inteiro de dados por vez pelo módulo 433MHz (apenas funciona, melhor não querer mexer).
def TransmiteByte433(Byte):
   global NivelAtualTx # *Fato curioso, no python, se quiser modificar uma variável externa dentro do contexto da função precisa declará-la como global aqui dentro. 

   BitMask = (1 << 7)
   for BitCount in range(8):
      # Pega o próximo bit dentro do byte para transmitir.
      Bit = (Byte & BitMask)
      BitMask = int(BitMask / 2)

      # Troca o nível GPIO.
      # (essa parte só inverte o sinal de ON pra OFF, então pelo que eu entendi os sinais de nível
      # HIGH e LOW são transmitidos através de "períodos" de mesmo sinal antes que ele mude,
      # seja com o sinal ligado ou desligado no transmissor, e não através de "sinal ON = high, OFF = low", por exemplo)
      if NivelAtualTx == NIVEL_TX_OFF:
         NivelAtualTx = NIVEL_TX_ON

      else:
         NivelAtualTx = NIVEL_TX_OFF
      RPi.GPIO.output(PINO_GPIO_TX, NivelAtualTx)
      
      # Período de transmissão padrão para bit nível 0. (como explicado ali em cima, [1 período de mesmo sinal = 0 binário])
      time.sleep(PERIODO_NIVEL_TX)

      # Período adicional para bit nível 1. ([2 períodos de mesmo sinal = 1 binário])
      if Bit > 0:
         time.sleep(PERIODO_NIVEL_TX)


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */

# Uma função provisória de des/encriptação extremamente básica, apenas por propósitos demonstrativos.
# *Utiliza a chave para modificar os caracteres diretamente na lista com os dados que entra nessa função (PacoteDados["DADOS"]).
# *Fato curioso 2, nessa função não precisa declarar a variável externa como global para modificar ela, pois ela é uma lista nesse caso,
# e as variáveis listas [no python] são referências à memória que é diretamente modificada, não só sua instância.
# *Obs.: Eu não compreendi plenamente o funcionamento dessa des/criptografia então não tenho o que explicar.
def DesCriptografa(Dados):
   ChaveCount = 0
   TamanhoChave = len(CHAVE_CRIPTOGRAFIA)
   for count in range(len(Dados)):
      Dados[count] ^= CHAVE_CRIPTOGRAFIA[ChaveCount]
      if ChaveCount >= TamanhoChave:
         ChaveCount = 0


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */

# Definição do pacote de dados [em formato de dicionário] para transmissão.
# Está em ordem lógica que deve chegar no receptor, primeiro a assinatura para identificar que é uma mensagem,
# depois o tamanho dos dados para se preparar, então os dados em si, e por fim o checksum para confirmação de integridade dos dados.
PacoteDados = {
   "ASSINATURA": ASSINATURA_PADRAO,
   "COMPRIMENTO_DADOS": 0,
   "DADOS": [],
   "CHECKSUM": 0,
}


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */

# Configuração das interfaces GPIO do Raspberry.
RPi.GPIO.setwarnings(False)
RPi.GPIO.setmode(RPi.GPIO.BCM)
RPi.GPIO.setup(PINO_GPIO_RX, RPi.GPIO.IN, pull_up_down=RPi.GPIO.PUD_UP)
RPi.GPIO.setup(PINO_GPIO_TX, RPi.GPIO.OUT, initial=NIVEL_TX_OFF)


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */

# -- PROGRAMA "PRINCIPAL":

# Checagem pelo parâmetro na linha de comando, caso não esteja como esperado.
if len(sys.argv) < PARAMETROS_COUNT:
   sys.stdout.write("\n" + sys.argv[PARAMETRO_EXECUTAVEL] + " [INSERIR DADOS]\n\n")

# (*colaboração minha) Checando se foram inseridos mais parâmetros além do esperado no comando.
elif len(sys.argv) > PARAMETROS_COUNT:
   sys.stdout.write("\n" + sys.argv[PARAMETRO_EXECUTAVEL] + " [ENTRADA INVALIDA]\n\n")

#/* -------------------------------------------------------------------------------------------------------------------- */

# Se o parâmetro estiver correto, colocar os dados dentro do pacote e definir os valores do pacote.
else:
   # Registrando o tamanho dos dados a serem enviados (quantidade de bytes).
   PacoteDados["COMPRIMENTO_DADOS"] = len(sys.argv[PARAMETRO_DADOS])


   # Tokenizando e encriptando os dados a serem enviados.
   # **Para sanar nossa dúvida anterior eu testei essa função de "list(sys.argv)" e confirmo que ela devolve
   # os dados com cada caractére devidamente separado e pronto na lista, simples assim, por isso já é uma lista.
   PacoteDados["DADOS"] = list(sys.argv[PARAMETRO_DADOS])   
   # *SUGESTÃO: Pode valer a pena colocar uma conversão para string aqui caso o input não seja excplicitamente declarado como string?
   # *Ex: list(str(sys.argv[PARAMETRO_DADOS]))

   # Faz a encriptação dos dados em PacoteDados["DADOS"].
   # **A função "ord" retorna o valor numérico de um caractére no seu lugar, para propósitos de operação com caractéres.
   for count in range(len(PacoteDados["DADOS"])):
      PacoteDados["DADOS"][count] = ord(PacoteDados["DADOS"][count])
   # Pega a lista com os valores numéricos dos caractéres e criptografa eles usando a função de criptografia.
   DesCriptografa(PacoteDados["DADOS"])


   # Cálculo do valor de checksum dos dados para validação da transmissão.
   PacoteDados["CHECKSUM"] = 0
   for Byte in PacoteDados["DADOS"]:
      PacoteDados["CHECKSUM"] ^= Byte

#/* -------------------------------------------------------------------------------------------------------------------- */

   # *A partir daqui a lógica está toda pronta e o pacote será apenas enviado.
   # Exibe no console o pacote de dados sendo enviado.
   sys.stdout.write("\nENVIANDO PACOTE:\n")
   sys.stdout.write(str(PacoteDados) + "\n\n")


   # Liga o transmissor 433MHz.
   NivelAtualTx = NIVEL_TX_ON
   RPi.GPIO.output(PINO_GPIO_TX, NivelAtualTx)
   

   # Espera pelo número de bits iniciais.
   for count in range(BITS_INICIAIS_TX):
      time.sleep(PERIODO_NIVEL_TX)


   # Transmite a assinatura de identificação do pacote de dados, byte por byte.
   for Byte in PacoteDados["ASSINATURA"]:
      TransmiteByte433(Byte)

   # Transmite o número do comprimento dos dados no pacote de dados, byte por byte.
   TransmiteByte433(PacoteDados["COMPRIMENTO_DADOS"])

   # Transmite os dados encriptados do pacote de dados, byte por byte.
   for Byte in PacoteDados["DADOS"]:
      TransmiteByte433(Byte)

   # Transmite o valor de checksum dos dados do pacote de dados, byte por byte.
   TransmiteByte433(PacoteDados["CHECKSUM"])

   # Desliga o transmissor 433MHz.
   NivelAtualTx = NIVEL_TX_OFF
   RPi.GPIO.output(PINO_GPIO_TX, NivelAtualTx)


   # *Apenas exibe no console que o pacote de dados foi enviado.
   sys.stdout.write("\n[PACOTE ENVIADO]\n")

   # Fim do período de transmissão e do programa.
   time.sleep(PERIODO_FIM_TX)


#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */
#/* -------------------------------------------------------------------------------------------------------------------- */
