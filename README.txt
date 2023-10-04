/* -------------------------------------------------------------------------------- */
/* -------------------------------------------------------------------------------- */
/.   TRANSMITINDO E RECEBENDO DADOS ATRAVÉS DO MÓDULO RF 433 MHZ COM RASPBERRY PI   ./
/* -------------------------------------------------------------------------------- */
/* -------------------------------------------------------------------------------- */

-- VIDEOS DESTE PROJETO E CÓDIGO FONTE NO GITHUB (*NO FINAL DESTE TEXTO!*)

/* -------------------------------------------------------------------------------- */
/* -------------------------------------------------------------------------------- */

-- Aplicações
==============

*ATENÇÃO* - Sumário geral sobre as aplicações contidas aqui e quais são mais relevantes:

 -- Pi433MHz.py = Versão obsoleta do código que utiliza desnecessariamente POO e fica
                    recebendo sinais de RF do ambiente com possível relevância.
                    (Obs.1: pode ser usado para monitorar nossos dados enviados e
                    exibi-los em vários formatos, por propósitos de teste, já
                    que adicionalmente também monitora a quantidade de ruído.)
                    (Obs.2: pessoalmente, esse arquivo é muito grande e bagunçado
                    comparado aos outros, então [exceto por propósitos de teste]
                    eu recomendo não trabalharmos muito em cima dele.)

 -- Pi433MHzRxMatch.py = Recebe dados assim como o "...Rx.py", mas no final tem um tratamento
                    para verificar um possível "match" dos dados recebidos e então executar
                    algum comando ou outra aplicação.
                    (p.s: Essa parte do código pode ser facilmente implementada para o
                    "...Rx.py", caso seja necessário, caso contrário esse arquivo é dispensável)
                    
        - Pi433MHzRxMatch.ini = Define os caminhos de arquivos ".sh" em caso de um "match".
        - Pi433MHzRxMatch1.sh = Arquivo de exemplo ".sh" indicando a execução de um "match".
        - Pi433MHzRxMatch2.sh = Arquivo de exemplo ".sh" indicando a execução de outro "match".

 -- LogSignatures.sh = Aparentemente é um log de assinaturas recebidas no "Pi433MHz.py",
                    mas não está sendo utilizado em nenhum código então não tenho certeza.

 -- Pi433MHzTx.py = Programa principal que envia dados a 433MHz, *relevante para o nosso uso!
 -- Pi433MHzRx.py = Programa principal que recebe dados a 433MHz, *relevante para o nosso uso!


*A seguir a descrição mais detalhada sobre a funcionalidade dessas aplicações*


/* -------------------------------------------------------------------------------- */

./Pi433MHz.py

- Monitora e loga dados. Proporciona várias visualizações dos dados sendo recebidos.
Permite a análise e identificação de dados requeridos transmitidos através de 433MHz.
Também apresenta um contador de ruído, o qual indica quanta interferência de RF
(RFI) há no local, proporcionando um método para encontrar uma região com baixa 
interferência para localizar uma transmissão, melhorando assim a confiabilidade da
recepção de dados.


/* -------------------------------------------------------------------------------- */

./Pi433MHzRxMatch.py

- Uma aplicação de exemplo que identifica dados específicos sendo transmitidos e
permite rodar uma aplicação dependendo de qual série de assinaturas de dados
correspondentes identificadas. Dados de configuração em formato de uma lista de
assinaturas de dados e comandos a serem executados estão no arquivo Pi433MHzRxMatch.ini.


/* -------------------------------------------------------------------------------- */

./LogSignatures.sh

- Sumário das assinaturas recebidas e logadas com a aplicação Pi433MHz.py.
Juntamente com o número de ocorrências, como uma assistência para identificar
dados requeridos sendo recebidos.


/* -------------------------------------------------------------------------------- */

./Pi433MHzTx.py

- Uma aplicação de exemplo para pegar uma string em ASCII como parâmetro de linha
de comando, a qual será então transmitida por 433MHz como parte de um pacote de
dados. O pacote permite que os dados sejam checados por integridade na recepção
no caso de ocorrer a corrupção durante a transmissão(checksum). Demonstra também uma
encriptação básica dos dados para transmissão. A aplicação Pi433MHzRx.py pode
ser usada para receber e exibir esses dados desencriptados.

- Exemplo de uso no prompt de comando:
./Pi433MHzTx.py 'test message'


/* -------------------------------------------------------------------------------- */

./Pi433MHzRx.py

- Uma aplicação de exemplo para receber, validar, desencriptar e exibir um pacote de
dados transmitido pela aplicação Pi433MHzTx.py.


/* -------------------------------------------------------------------------------- */
/* -------------------------------------------------------------------------------- */

-- Antena (explorar mais afundo sobre o cálculo da antena)
===========================================================
"17cm 'wound', 5mm diâmetro espaçado para 20mm de fio de cobre esmaltado 0.5mm."
Com um fio de aterramento no centro através da bobina.

*Obs.: Eu sei que parece que não faz sentido o que eu escrevi aqui, eu só traduzi
diretamente cada palavra que estava escrita em inglês, então também não sei exatamente.


/* -------------------------------------------------------------------------------- */
/* -------------------------------------------------------------------------------- */
/* -------------------------------------------------------------------------------- */

-- Vídeos:
===========

= Sending Data Between Two Raspberry Pi on 433MHz with a Python Script:
https://www.youtube.com/watch?v=qpavpA3zjis

= Reading Data Transmitted From Keyfobs At 433MHz With A Raspberry Pi:
https://www.youtube.com/watch?v=8B582TMMSNY



= Raspberry Pi 433MHz/315MHz Removing Signal Noise For Better Reception:
https://www.youtube.com/watch?v=vxF1N9asjts

= Explicação boa sobre ASK e OOK, e cálculo para a antena nos módulos(~5:00):
https://www.youtube.com/watch?v=w6V9NyXwohI

= Modelos diferentes de transceptores RF:
https://www.youtube.com/watch?v=nP6YuwNVoPU


/* -------------------------------------------------------------------------------- */

-- Código Fonte no GitHub:
https://github.com/BirchJD/RPi_433MHz


/* -------------------------------------------------------------------------------- */
/* -------------------------------------------------------------------------------- */
/* -------------------------------------------------------------------------------- */
