# AutoClicker Pro

Um aplicativo de autoclicker completo para Windows com interface gráfica amigável.

## 📋 Funcionalidades

- ✅ **Clicks de Mouse**: Configure a posição, o botão (esquerdo, direito, meio) e por quanto tempo segurá-lo
- ⌨️ **Ações de Teclado**: Pressione teclas individuais ou segure-as por um tempo determinado
- ⏱️ **Delays Configuráveis**: Adicione esperas entre ações
- 🔄 **Repetições**: Execute a sequência múltiplas vezes com delay entre repetições
- 💾 **Salvar/Carregar**: Salve suas configurações em JSON para reutilizar depois
- 🎮 **Atalhos de Teclado**: F6 para iniciar, F7 para parar, ESC para cancelar

## 🚀 Como Usar

### Instalação

Para instalar no Windows 64 bits, execute `Instalador\AutoClickerPro-Instalador.exe` e siga o assistente. Python não precisa estar instalado. O programa pode ser removido pelas configurações de aplicativos do Windows. O Windows pode avisar que o instalador não tem assinatura digital.

Na versão instalada, as configurações são salvas em `%APPDATA%\AutoClicker Pro\autoclick_config.json` e são mantidas ao desinstalar. Para usar uma configuração criada com a versão Python, copie seu `autoclick_config.json` anterior para essa pasta.

Para executar a partir do código-fonte:

1. **Abrir a pasta do projeto**
   ```
   cd C:\Dev\testes\Autoclick
   ```

2. **Instalar dependências**
   ```
   python -m pip install -r requirements.txt
   ```

3. **Executar o aplicativo**
   ```
   python autoclicker.py
   ```

   Ou simplesmente execute o arquivo `run.bat`

Para gerar o instalador novamente, instale as dependências do projeto, o PyInstaller (`python -m pip install pyinstaller`) e o Inno Setup 6; depois execute `powershell -ExecutionPolicy Bypass -File .\criar_instalador.ps1` nesta pasta.

### Uso do Aplicativo

#### Adicionando Ações

1. **Adicionar Click**
   - Clique em "Adicionar Click"
   - Clique em "Mover Janela", arraste a área verde ou a barra de título até o alvo ficar no local desejado e clique em "Salvar posição". O centro da cruz indica onde ocorrerá o clique.
   - Ou use a posição atual do mouse ou digite as coordenadas (X, Y)
   - Selecione o botão do mouse (esquerdo, direito, meio)
   - Configure **Segurar botão (ms)**: 0 para clique rápido ou, por exemplo, 2000 para segurar por 2 segundos
   - Configure **Quantidade de cliques** (1 por padrão) e o **Intervalo entre cliques** em milissegundos
   - Configure o delay após todos os cliques em milissegundos
   - Clique OK

2. **Adicionar Tecla**
   - Clique em "Adicionar Tecla"
   - Digite a tecla (exemplos: 'a', 'enter', 'space', 'shift', 'ctrl', 'alt', 'tab')
   - Configure o tempo de hold (0 = pressão rápida)
   - Configure o delay após a ação
   - Clique OK

3. **Adicionar Delay**
   - Clique em "Adicionar Delay"
   - Configure o tempo de espera em milissegundos
   - Clique OK

#### Removendo Ações

- Selecione uma ação na lista
- Clique "Remover Ação" ou use "Limpar Tudo" para remover tudo

#### Configurações Gerais

- **Repetições**: Quantas vezes executar toda a sequência, na ordem da lista.
- **Repetir até parar (F7)**: Ignora o número de repetições e continua até pressionar F7 ou clicar em Parar.
- **Espera entre repetições**: Tempo em milissegundos após a última ação, antes de voltar à primeira. Ele se soma ao delay após a última ação ou a um Delay separado.

Exemplo: segurar por 1100 ms, esperar 4000 ms, dar vários cliques rápidos e recomeçar:

1. Adicione um clique com **Segurar botão = 1100 ms**, **Quantidade = 1** e **Delay após todos os cliques = 4000 ms**.
2. Adicione outro clique com **Segurar botão = 0 ms**, **Quantidade = 10**, **Intervalo = 50 ms** e **Delay após todos os cliques = 0 ms**. Ajuste a quantidade e o intervalo como preferir.
3. Configure **Espera entre repetições = 0 ms** para recomeçar logo após a sequência e marque **Repetir até parar**.
4. Selecione a janela de destino e pressione F6. A sequência será: segurar por 1,1 segundo, soltar, esperar 4 segundos, clicar 10 vezes com intervalo de 50 ms e recomeçar. Pressione F7 para parar.

Você também pode usar **Adicionar Delay** entre as ações em vez do delay após o clique. Se usar os dois, as esperas se somam; não é necessário adicionar um Delay separado para a espera já configurada no clique.
O intervalo é aplicado apenas entre os cliques, não após o último. Se o hold for maior que zero, cada clique da quantidade terá esse tempo de hold. Configurações antigas sem quantidade continuam com um clique.

#### Executando

- **Iniciar**: pressione F6 ou clique "Iniciar (F6)"
- **Parar**: pressione F7 ou clique "Parar (F7)"; um botão segurado é solto ao parar
- **Cancelar e fechar**: ESC
- F6 e F7 são globais e funcionam com outra janela em foco; ESC funciona com o AutoClicker em foco. Enquanto o AutoClicker estiver aberto, essas teclas ficam reservadas para os controles e podem não chegar ao outro aplicativo. Não as inclua nas ações.
- Configure as ações, selecione a janela de destino e pressione F6. O aplicativo informa o estado na própria janela, sem abrir uma mensagem ao concluir ou parar.
- Se não conseguir registrar os atalhos, o programa mostrará um erro. Alguns jogos ou aplicativos podem bloquear atalhos globais; verifique permissões e, se necessário, execute ambos com o mesmo nível de permissão.

Os tempos são em milissegundos: 1000 ms = 1 segundo. O tempo real depende do Windows e do aplicativo de destino; 1 ms não garante precisão de 1 ms. Não há mais a pausa automática de 100 ms do PyAutoGUI.

O hold do mouse usa eventos `SendInput` do Windows. Alguns jogos podem ignorar eventos simulados; o recebimento no aplicativo de destino não é garantido. Se o Windows recusar o envio, confira se o destino está executando como administrador e inicie o AutoClicker com o mesmo nível de permissão.

#### Salvando/Carregando

- **Salvar Configuração**: Salva em `autoclick_config.json`, na pasta de execução em modo Python ou na pasta do usuário na versão instalada.
- **Carregar Configuração**: Carrega do mesmo local usado para salvar.
- A opção de repetir até parar também é salva. Configurações anteriores sem essa opção continuam usando o número de repetições.

## 📝 Exemplos

### Exemplo 1: Clicar em 3 posições diferentes

1. Adicionar Click → X: 100, Y: 200, Botão: left, Hold: 0 ms, Delay: 500 ms
2. Adicionar Click → X: 300, Y: 400, Botão: left, Hold: 0 ms, Delay: 500 ms
3. Adicionar Click → X: 500, Y: 600, Botão: left, Hold: 0 ms, Delay: 500 ms
4. Pressione F6 para iniciar

### Exemplo 2: Digitar um texto

1. Adicionar Tecla → 'a', Hold: 0 ms, Delay: 100 ms
2. Adicionar Tecla → 'b', Hold: 0 ms, Delay: 100 ms
3. Adicionar Tecla → 'c', Hold: 0 ms, Delay: 100 ms
4. Resultado: digita "abc"

### Exemplo 3: Segurar uma tecla

1. Adicionar Tecla → 'shift', Hold: 2000 ms, Delay: 500 ms
2. Resultado: mantém Shift pressionado por 2 segundos

### Exemplo 4: Sequência completa

1. Adicionar Delay → 2000 ms (espera 2 segundos antes de começar)
2. Adicionar Click → Posição do botão
3. Adicionar Delay → 500 ms
4. Adicionar Tecla → 'enter', Hold: 0 ms, Delay: 100 ms
5. Repetições: 5 (repete 5 vezes)
6. Pressione F6

## ⚙️ Teclas Suportadas

Algumas teclas comuns:
- Letras: 'a', 'b', 'c', ... 'z'
- Números: '0', '1', ... '9'
- Especiais: 'enter', 'space', 'tab', 'backspace', 'delete'
- Modificadores: 'shift', 'ctrl', 'alt'
- Setas: 'up', 'down', 'left', 'right'
- Função: 'f1', 'f2', ... 'f12'

Para uma lista completa, consulte a documentação da biblioteca `keyboard`.

## ⚠️ Aviso de Segurança

- **Failsafe**: Mova o mouse para o canto superior esquerdo da tela para parar a execução de emergência
- **Sempre teste** com repetições baixas primeiro
- **Cuidado** com configurações que podem danificar arquivos ou dados
- **Não use** em ambientes de produção sem devida aprovação

## 🐛 Solução de Problemas

### "ModuleNotFoundError: No module named 'pyautogui'"
- Execute: `pip install pyautogui`

### "ModuleNotFoundError: No module named 'keyboard'"
- Execute: `pip install keyboard`
- No Windows, pode precisar rodar como administrador

### Os cliques não aparecem estar funcionando
- Verifique se as coordenadas X, Y estão corretas
- Use a função "Capturar Posição" ao adicionar clicks

### As teclas não estão sendo digitadas
- Certifique-se que a janela de destino está em foco
- Use "Adicionar Delay" se necessário para dar tempo para a janela reagir

## 📄 Arquivo de Configuração

As configurações são salvas em `autoclick_config.json`:

```json
{
  "actions": [
    {
      "type": "click",
      "x": 100,
      "y": 200,
      "button": "left",
      "hold": 2000,
      "delay": 500
    },
    {
      "type": "key",
      "key": "enter",
      "hold": 0,
      "delay": 100
    },
    {
      "type": "delay",
      "time": 2000
    }
  ],
  "repetitions": 1,
  "repeat_delay": 1000
}
```

Os valores de tempo do JSON são em milissegundos. Cliques salvos sem o campo `hold` continuam sendo cliques rápidos. Arquivos muito antigos, criados quando os campos eram em segundos, precisam ter seus tempos ajustados manualmente.

## 📦 Dependências

- Python 3.6+
- pyautogui: Para controlar o mouse
- keyboard: Para controlar o teclado

## 📜 Licença

Uso pessoal e educacional

---

**Desenvolvido com ❤️**
