---
title: "Jailbreaking o sistema de navegação do carro só pra ajustar o relógio: um tutorial técnico sobre hacking de hardware em veículos"
date: "2026-11-04"
category: "tutorial"
tags: ["hardware", "hacking", "automotivo", "linux", "reverse-engineering"]
excerpt: "Você liga o carro, o rádio acende e a tela mostra um horário que você não vê desde os dias em que a Internet ainda precisava de linha discada. O ajuste automático via GPS."
cover: "https://raw.githubusercontent.com/ismaeldouglasdev/blog-content/main/posts/covers/2026-11-04-jailbreaking-o-sistema-de-navegacao-do-carro-so-pra-ajustar.jpg"
lang: "pt"
---

Você liga o carro, o rádio acende e a tela mostra um horário que você não vê desde os dias em que a Internet ainda precisava de linha discada. O ajuste automático via GPS falha, o menu do veículo não tem opção manual, e a única saída oficial é uma visita à concessionária que custa um terço do valor do reparo.

O desespero não é só pela hora errada, é pelo que ela representa: uma máquina que você possui, mas não controla. A vontade de pegar uma chave de fenda começa a parecer mais racional do que tentar navegar em menus bloqueados.

Nesse cenário, a ideia de desmontar o painel para ter acesso ao sistema operacional embarcado deixa de ser um hobby de nicho e vira uma questão de praticidade. O que você faria se descobrisse que por trás da interface minimalista do seu carro roda um Linux completo, e que o problema de sincronização de horário é causado por um simples script de configuração?

## Investigando o Inimigo: O Hardware do Sistema de Entretenimento

O alvo é um sistema multimídia de um Renault. O primeiro passo é entender o que há por trás do plástico. Um pouco de pesquisa online em fóruns de proprietários revela que muitas unidades são, na verdade, dispositivos Android genéricos, mas algumas linhas mais antigas utilizam soluções embarcadas proprietárias.

A investigação começa pelo modelo. O número da peça, geralmente encontrado em uma etiqueta atrás da unidade ou no manual, é o caminho para o datasheet. No caso de equipamentos automotivos, esses documentos raramente são públicos, mas comunidades dedicadas ao *right-to-repair* frequentemente os compilam. Fóruns como o XDA-Developers ou o /r/CarHacking no Reddit são pontos de partida inestimáveis. A pista crucial: se o sistema tem uma entrada para cartão SD ou USB que permite atualizações de firmware, é quase certo que há um computador com um sistema operacional por dentro.

Encontrei a confirmação para o modelo em questão: uma unidade baseada em um SoC (System-on-a-Chip) MIPS rodando um kernel Linux 2.6. A arquitetura MIPS é comum em eletrônicos embarcados pela sua eficiência energética. Saber isso muda tudo. Não estamos lidando com um firmware mágico, mas com um computador que dá boot, carrega drivers e executa processos, processos que podemos interceptar.

## O Acesso Físico: Encontrando a Porta dos Fundos

Com a unidade fora do painel, um processo que exige ferramentas de plástico para destravar as presilhas e evitar arranhões, o hardware é exposto. A placa principal é uma paisagem de componentes de superfície (SMD), conectores e, o mais importante, conjuntos de pinos não populados.

Esses conjuntos, frequentemente rotulados como J1, J2, ou simplesmente com siglas como TX, RX, GND, são as portas UART (Universal Asynchronous Receiver/Transmitter). Elas são deixadas pelos fabricantes para debug durante o desenvolvimento e, muitas vezes, não são removidas na produção. São nosso serial console.

Identificar os pinos corretos requer um multímetro. Com a unidade energizada (usando uma fonte 12V externa, simulando a bateria do carro), procure por um pino com tensão constante de 3.3V ou 5V (VCC). O GND (terra) é facilmente encontrado pela continuidade com o metal do chassi. Os pinos TX (Transmit) e RX (Receive) são descobertos por tentativa e erro: conecte o RX do seu adaptador a um pino candidato; se caracteres legíveis aparecerem no terminal quando o sistema der boot, você achou o TX do dispositivo.

## Conectando os Pontos: USB para UART e o Primeiro Bootlog

Para a ponte entre o computador e a UART do carro, uso um adaptador USB-to-TTL Serial como o popular CP2102 ou FT232RL. A configuração é direta:
- Conecte o GND do adaptador ao GND da placa.
- Conecte o RX do adaptador ao TX da placa (os dados que a placa *transmite* você quer *receber*).
- O TX do adaptador vai para o RX da placa, para enviar comandos.

No computador, um terminal serial como o `screen` (no Linux/macOS) ou o PuTTY (no Windows) é aberto. A velocidade de comunicação (baud rate) é o primeiro desafio. Valores comuns são 115200, 9600, 38400 ou 57600 bps. Testar cada um deles durante o boot do sistema é a forma mais rápida. Quando a taxa estiver correta, o log de inicialização, antes invisível, começa a fluir na tela.

```
...
Booting Linux on physical CPU 0
Linux version 2.6.32.9 (build@factory) #1 SMP PREEMPT Tue Mar 15 12:00:00 UTC 2016
CPU: MIPS 24Kc V0.0
...
Mounting root filesystem from squashfs image...
...
Starting system services: dhcpcd, ntpd, media_server
...
```

Esse log é o mapa do tesouro. Ele confirma o kernel Linux, o sistema de arquivos raiz (squashfs, uma imagem compactada e somente leitura) e, crucialmente, os serviços que são iniciados. O `ntpd` (Network Time Protocol daemon) está lá. Ele é o responsável por sincronizar o relógio do sistema, e o provável culpado do horário congelado.

## Explorando o Sistema de Arquivos: A Gaiola de Squashfs

Um sistema de arquivos squashfs é montado como somente leitura. Isso é um obstáculo, mas não um bloqueio total. Ele contém todos os binários, bibliotecas e scripts do sistema. Para explorá-lo, precisamos de um shell.

Geralmente, em dispositivos embarcados, um terminal serial oferece um prompt de login após o boot. Tentativas com credenciais padrão como `root`/`root`, `admin`/`admin`, ou mesmo sem senha, são o próximo passo. No caso em questão, o login `root` não exigia senha, uma prática comum e insegura em dispositivos de consumo, mas uma brecha para nós.

Dentro do shell, o sistema de arquivos se revela. Comandos como `ps` listam os processos em execução, confirmando o `ntpd`. `find / -name "*ntp*"` localiza os arquivos relacionados.

```
/usr/sbin/ntpd
/etc/init.d/ntpd
/etc/config/ntp.conf
```

O arquivo de configuração `/etc/config/ntp.conf` é a chave. Seu conteúdo normalmente aponta para servidores NTP (`pool.ntp.org`). O problema? Se a unidade não tem uma conexão de dados ativa (apenas o GPS, que neste modelo não fornece horário via NTP), o serviço falha silenciosamente e o relógio nunca é atualizado.

## A Modificação: Contornando a Falha de Sincronização

A solução mais limpa não é hackear o binário do `ntpd`, mas impedir que ele trave o sistema. Uma abordagem é desabilitar o serviço ntp e criar um script que permita o ajuste manual ou use uma fonte alternativa de tempo.

Primeiro, pare o serviço:
```bash
/etc/init.d/ntpd stop
/etc/init.d/ntpd disable
```

Agora, precisamos modificar algo na memória ou criar um script em uma partição de armazenamento que seja gravável (como `/var` ou `/tmp`, que geralmente são montados como tmpfs em RAM). A ideia é interceptar a chamada que define o horário no sistema.

Criei um script em `/var/set_time.sh`:
```bash
#!/bin/sh
# Script para definir o horário manualmente via serial console
echo "Current system time: $(date)"
echo "Enter new date and time (format: YYYY-MM-DD HH:MM:SS):"
read -r new_datetime
date -s "$new_datetime"
hwclock -w # Escreve no relógio de hardware, se existir
echo "Time set to: $(date)"
```

Para tornar essa funcionalidade acessível, é possível modificar o serviço que controla a interface de usuário no rádio, ou, de forma mais direta, criar um atalho. Como a UI é um processo binário fechado, a alternativa é usar a própria porta serial como interface de backup. Adicionei uma linha ao `/etc/rc.local` (um script executado no final do boot) para imprimir as instruções no console serial:

```bash
echo "--- To set time manually, run: /var/set_time.sh" > /dev/console
```

Assim, sempre que o sistema der boot, a mensagem aparecerá no log serial, lembrando o usuário (no caso, eu) de como ajustar o horário se necessário.

## Testes e Reassemblagem: A Prova de Fogo

Com o serviço ntpd desativado e o script de ajuste manual criado, é hora do teste. Reinicio a unidade pelo console com `reboot`. O bootlog rola novamente, e no final, a nova mensagem aparece. Conectando o adaptador serial ao laptop, executo o script `/var/set_time.sh`, defino a hora correta e confirmo com `date`.

A prova final: a tela do rádio no carro. Ao religar a unidade no veículo e dar a ignição, os mostradores digitais refletem, pela primeira vez em meses, o horário preciso.

Reinstalar a unidade no painel é o reverso da remoção. O silêncio dentro do carro é quebrado apenas pelo rádio, agora funcionando como deveria, e com um backdoor técnico que eu mesmo instalei.

## Reflexões Técnicas e Éticas sobre o Right-to-Repair

Esse processo vai muito além de ajustar um relógio. Ele é um microcosmo do movimento *right-to-repair* e expõe as camadas de abstração que separam os usuários de seus dispositivos.

Do ponto de vista técnico, a descoberta mais significativa é a ubiquidade do Linux. Sistemas que imaginamos como "caixas pretas", televisores, roteadores, termostatos e, claro, sistemas automotivos, são, frequentemente, computadores de propósito geral rodando um kernel monolítico. A barreira não é a complexidade, mas o acesso. Portas de debug como UARTs são um padrão da indústria porque são necessárias para o desenvolvimento; sua remoção seria um custo extra.

A experiência de operar um ponto de venda (PDV) open source como o OSPOS me familiarizou com a ideia de que o software que controla um negócio crítico pode, e deve, ser inspecionável e modificável. A migração de um banco de dados com milhares de produtos entre sistemas é uma tarefa de alto risco que exige compreensão profunda dos dois lados da interface. Esse mesmo raciocínio aplica-se ao carro: se um serviço de sincronização de horário falha, a capacidade de diagnosticar e contornar a falha não deveria ser um segredo guardado a sete chaves pela concessionária.

A questão de segurança é inevitável. Um terminal root acessível via UART é uma falha grave. Em um veículo moderno conectado, tal brecha poderia ser o primeiro passo de uma cadeia de exploração. No entanto, a segurança por obscuridade, esconder a vulnerabilidade atrás de um painel plástico, não é segurança de verdade. A transparência leva a sistemas mais robustos. Projetos open source de grande escala, como aquele em que contribuí, seguem esse princípio: cada linha de código que escrevi para melhorar scanners de segurança e detecção de conflitos parte do pressuposto de que a visibilidade é a base da confiança.

Por fim, o aprendizado é palpável. Esse tipo de projeto força você a lidar com camadas baixas do sistema: comunicação serial, bootloaders, sistemas de arquivos embarcados e scripts de inicialização. São conhecimentos que, em um contexto mais tradicional de desenvolvimento web ou aplicações, permanecem abstraídos. Dominá-los expande seu entendimento sobre como as coisas realmente funcionam, de um sensor em um carro a um servidor na nuvem.

### Takeaways Práticos

- **A UART é sua amiga**: Conjuntos de pinos não populados em placas eletrônicas são, frequentemente, portas seriais de debug. Um adaptador USB-to-TTL de R$ 30 é uma ferramenta de diagnóstico poderosa.
- **Linux está em todo lugar**: Não assuma que um dispositivo com interface simples é "burro". Use comandos como `ps`, `mount` e `cat /proc/cpuinfo` para mapear o sistema.
- **Squashfs é somente leitura, mas não intransponível**: A estratégia é trabalhar com diretórios graváveis (como `/var` ou `/tmp`) ou modificar scripts de inicialização que são executados antes da montagem da imagem principal.
- **Documente e compartilhe**: Fóruns e comunidades são construídos com base na documentação de procedimentos como este. Sua solução para um modelo específico pode salvar horas de dezenas de outras pessoas.
- **Pense na segurança**: Ao criar um backdoor para si mesmo, esteja ciente das implicações. Nunca deixe credenciais padrão ou serviços expostos em um dispositivo conectado à Internet.
- **O direito ao conserto é técnico**: A capacidade de reparar seu próprio equipamento passa, cada vez mais, pela capacidade de entender e modificar seu software. Aprender essas habilidades é uma forma de empoderamento.

## Fontes

- [Kernel.org Documentation](https://www.kernel.org/doc/html/latest/) - Documentação oficial do kernel Linux.
- [Serial Console HOWTO - The Linux Documentation Project](https://tldp.org/HOWTO/Serial-HOWTO.html) - Guia detalhado sobre configuração e uso de consoles seriais.
- [OWASP Embedded Application Security](https://owasp.org/www-project-embedded-application-security/) - Recursos sobre segurança em aplicações embarcadas.
- [BusyBox: The Swiss Army Knife of Embedded Linux](https://busybox.net/) - Site do BusyBox, conjunto de utilitários Unix essenciais para sistemas embarcados.
- [Right to Repair Movement - Repair.org](https://repair.org/) - Site do movimento que defende o direito dos consumidores a consertar seus próprios dispositivos.
- [GitHub - car-hacking/awesome-car-hacking](https://github.com/car-hacking/awesome-car-hacking) - Uma lista curada de recursos, ferramentas e pesquisas sobre hacking automotivo.
