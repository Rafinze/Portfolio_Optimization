
# Otimização de Portfólio (MIQP) com Restrições de Cardinalidade e Setoriais

Este repositório contém um pipeline completo em Python para otimização de carteiras de investimento, implementando restrições do mundo real (cardinalidade, limites de alocação e regras setoriais) através de um modelo de **Programa Quadrático Inteiro-Misto (MIQP)**.

O projeto utiliza a linguagem de modelagem `amplpy` e o solver `Gurobi` para encontrar a fronteira eficiente de portfólios, indo desde a limpeza e preparação de dados brutos até a validação formal do modelo contra benchmarks acadêmicos.



---

## 🛠️ Ferramentas e Metodologia

* **Linguagem:** Python 3.x
* **Análise de Dados:** `pandas`, `numpy`
* **Aquisição de Dados:** `requests`, `yfinance`, `lxml`
* **Modelagem:** `amplpy` (Python API para AMPL)
* **Solver:** Gurobi Optimizer
* **Visualização:** `matplotlib`, `seaborn`
* **Metodologia:** O problema é formulado como um MIQP (Mixed-Integer Quadratic Program) para minimizar a variância da carteira (risco) sujeito a um retorno alvo (`R_target`) e um conjunto de restrições de cardinalidade (`m`), alocação (`W_min`, `W_max`) e regras lógicas de negócio (setoriais). O solver Gurobi utiliza um algoritmo **Branch-and-Cut** para encontrar a solução ótima.

---

## 📂 Estrutura do Projeto e Fluxo de Trabalho

O projeto é dividido em dois fluxos de trabalho principais, cada um com seus próprios scripts.

### Fluxo 1: Análise de Mercado (Dados do Mundo Real)

Este é o fluxo principal para analisar dados de mercado (ex: S&P 500) com regras de negócio complexas.

**Arquivos Envolvidos:**
* `Limpa dados.py` (Script de Preparação)
* `gerar_classificacao.py` (Script de Preparação)
* `menu_otimizacao_ampl.py` (Script Principal de Análise)
* `precos_fechamento_3_anos.csv` (Dados Brutos de Entrada)
* `vetor_retornos_calculado.csv` (Dados Processados de Saída)
* `matriz_covariancia_calculada.csv` (Dados Processados de Saída)
* `mapeamento_setores.csv` (Dados Processados de Saída)

**Passos para Execução:**

1.  **Fornecer Dados Brutos:** Adicione seu arquivo de preços de fechamento diários (ex: `precos_fechamento_3_anos.csv`) ao repositório.
2.  **Preparar Dados de Classificação:**
    ```bash
    # Busca os setores de mercado (ex: S&P 500 da Wikipedia) e salva 'mapeamento_setores.csv'
    python gerar_classificacao.py
    ```
3.  **Preparar Dados Financeiros:**
    ```bash
    # Lê 'precos_fechamento_3_anos.csv', calcula mu e Sigma, e salva os arquivos CSV processados
    python "Limpa dados.py"
    ```
4.  **Executar Análise Principal:**
    ```bash
    # Consome os 3 arquivos CSV gerados e executa a análise da Fronteira Eficiente
    python menu_otimizacao_ampl.py
    ```

---

### Fluxo 2: Validação Acadêmica (Benchmark)

Este fluxo é usado para **validar a corretude** do modelo matemático central contra os benchmarks clássicos da literatura (OR-Library de Beasley).

**Arquivos Envolvidos:**
* `benchmark.py` (Script de Validação)

**Passo Único para Execução:**
Este script é **auto-contido**. Ele ignora todos os arquivos CSV locais.

```bash
# Baixa os dados 'port1', 'portef1' e 'portc1' da web,
# executa o modelo com e sem restrições, e plota um gráfico
# de validação comparando seus resultados com o gabarito.
python benchmark.py
````

-----

## 📄 Descrição Detalhada dos Arquivos

### Scripts de Preparação

  * **`Limpa dados.py`**:

      * **Entrada:** `precos_fechamento_3_anos.csv`
      * **O que faz:** Lê os preços brutos, calcula os retornos diários (`.pct_change()`), anualiza o retorno médio (`.mean() * 252`) e a matriz de covariância (`.cov() * 252`).
      * **Saída:** `vetor_retornos_calculado.csv` (`mu`) e `matriz_covariancia_calculada.csv` (`Sigma`).

  * **`gerar_classificacao.py`**:

      * **Entrada:** Nenhuma (busca dados da web - S\&P 500 da Wikipedia).
      * **O que faz:** Raspa a web para obter a lista de tickers do S\&P 500 e sua classificação setorial (GICS).
      * **Saída:** `mapeamento_setores.csv`.

### Scripts de Otimização

  * **`menu_otimizacao_ampl.py`**:

      * **Entrada:** `vetor_retornos_calculado.csv`, `matriz_covariancia_calculada.csv`, `mapeamento_setores.csv`.
      * **O que faz:** Script principal para análise de mercado. Carrega os dados processados, aplica o modelo MIQP completo (incluindo regras de setores como `Min_Diversificacao_Defensivo`, `Limite_Exposicao_Juros`, etc.) e executa uma **Análise de Sensibilidade** (mapeamento da Fronteira Eficiente), variando `R_target` e `W_max`.
      * **Saída:** Gráficos da Fronteira Eficiente e tabelas no console com as carteiras de maior Índice de Sharpe.

  * **`benchmark.py`**:

      * **Entrada:** Nenhuma (baixa dados da web).
      * **O que faz:** Valida o modelo-base. Roda uma versão simplificada do modelo (sem setores) com e sem as restrições de cardinalidade (`m`) e aporte mínimo (`W_min`) e compara os resultados com os gabaritos acadêmicos (`portef1` e `portc1`).
      * **Saída:** Salva os gráficos de validação (ex: `validacao_benchmark_port1.png`) em uma pasta (ex: `Graficos_Benchmark`).

### Arquivos de Dados (`.csv`)

  * `precos_fechamento_3_anos.csv`: **(Dado de Entrada)**. Seu arquivo de preços brutos.
  * `vetor_retornos_calculado.csv`: **(Dado Processado)**. O vetor `mu` (retornos esperados) anualizado.
  * `matriz_covariancia_calculada.csv`: **(Dado Processado)**. A matriz `Sigma` (covariância) anualizada.
  * `mapeamento_setores.csv`: **(Dado Processado)**. Mapeamento de `Ticker` para `Setor`.

-----

## 🏁 Como Rodar o Projeto (Guia Rápido)

### 1\. Requisitos

**Software Essencial:**

  * Python 3.8+
  * Uma instalação funcional do **AMPL**
  * Um solver de otimização, como **Gurobi** (com uma licença válida)

**Bibliotecas Python:**
(Crie um arquivo `requirements.txt` com este conteúdo)

```
pandas
numpy
amplpy
matplotlib
seaborn
requests
lxml
yfinance
```

E instale com:

```bash
pip install -r requirements.txt
```

### 2\. Configuração do AMPL/Gurobi

Este é o passo mais crítico. O script Python precisa saber onde encontrar os executáveis do AMPL.

1.  Em **ambos** os scripts (`benchmark.py` e `menu_otimizacao_ampl.py`), encontre o bloco `if __name__ == '__main__':`.

2.  Localize a linha `caminho_ampl = "..."` e **substitua o caminho** pelo diretório exato onde o seu `ampl.exe` está instalado.

    **Exemplo de alteração:**

    ```python
    # Bloco 'try...except' para encontrar o AMPL
    try:
        ampl_env = Environment() # Tenta encontrar no PATH do sistema
    except Exception:
        try:
            # --- EDITE ESTA LINHA ---
            caminho_ampl = r"C:\ampl_mswin64" # Coloque o caminho da SUA instalação
            ampl_env = Environment(caminho_ampl)
        except Exception as e:
            print(f"ERRO CRÍTICO: Não foi possível encontrar os executáveis do AMPL.")
            exit()
    ```

### 3\. Passo a Passo da Execução

#### Passo A: Validar o Modelo (Recomendado)

Primeiro, confirme que seu ambiente e seu modelo-base estão corretos.

```bash
python benchmark.py
```

  * **O que esperar:** O script irá baixar os 5 benchmarks, rodar a validação completa (pode levar vários minutos) e salvar 5 gráficos de validação na pasta `Graficos_Benchmark`. Verifique se os pontos vermelhos e verdes se sobrepõem nos gráficos.

#### Passo B: Preparar Dados de Mercado

Forneça seu arquivo `precos_fechamento_3_anos.csv`.

1.  **Gere `mu` e `Sigma`:**
    ```bash
    python "Limpa dados.py"
    ```
2.  **Gere o mapeamento de setores:**
    ```bash
    python gerar_classificacao.py
    ```

#### Passo C: Executar a Análise de Mercado

Com os três arquivos (`vetor...`, `matriz...`, `mapeamento...`) prontos, rode a análise principal.

```bash
python menu_otimizacao_ampl.py
```

  * **O que esperar:** O script iniciará a Análise de Sensibilidade, mostrando o log do Gurobi para cada execução e, ao final, exibirá o gráfico da Fronteira Eficiente para os seus dados.

<!-- end list -->

```

(Fim do `README.md`)
```
