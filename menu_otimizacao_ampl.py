import pandas as pd
from amplpy import AMPL, Environment
import numpy as np
import time
import os
import seaborn as sns
import matplotlib.pyplot as plt

MODELO_AMPL_STRING = """
# --- 1. CONJUNTOS ---
set ATIVOS;
set SETORES;

set Ativos_Por_Setor {SETORES} within ATIVOS;

set SETORES_FINANCEIROS within SETORES;
set SETORES_DEFENSIVOS within SETORES;
set SETORES_CICLICOS within SETORES;
set SETORES_COMMODITIES within SETORES;
set SETOR_SIDERURGIA within SETORES;
set SETOR_CONSTRUCAO_CIVIL within SETORES;
set SETOR_TECNOLOGIA within SETORES;
set SETOR_ENERGIA_ELETRICA within SETORES;
set SETORES_ESCOLHIDOS within SETORES;
set SETORES_SENSIVEIS_JUROS within SETORES;

# --- 2. PARÂMETROS ---
param m; 
param W_max;
param R_target;
param mu {ATIVOS};
param Sigma {ATIVOS, ATIVOS};

# --- 3. VARIÁVEIS DE DECISÃO ---
var w {ATIVOS} >= 0; #peso do ativo i na carteira
var b {ATIVOS} binary; #flag para ativos selecionados
var y {SETORES} binary; # flag para setores selecionados

# --- 4. FUNÇÃO OBJETIVO ---
minimize Risco_Portfolio:
    sum {i in ATIVOS, j in ATIVOS} w[i] * Sigma[i,j] * w[j];

# --- 5. RESTRIÇÕES ---
subject to
    Soma_Pesos: sum {i in ATIVOS} w[i] = 1; #soma dos pesos igual a 100% (garante que todo o capital será alocado)
    Retorno_Alvo: sum {i in ATIVOS} mu[i] * w[i] >= R_target; #retorno de cada ativo vezes peso deve ser no minimo igual ao retorno esperado
    Cardinalidade: sum {i in ATIVOS} b[i] = m; # quantidade de ativos selecionados deve ser igual ao valor dado na entrada
    Aporte_Maximo {i in ATIVOS}: w[i] <= W_max * b[i]; #peso de cada ativo indicado pela flag

    Conecta_b_y_Inferior {s in SETORES}:
        y[s] <= sum {i in Ativos_Por_Setor[s]} b[i]; # se um setor for selecionado, existe pelo menos um ativo selecionado nele (força a inclusão de um ativo quando o setor é ativado)
    Conecta_b_y_Superior {s in SETORES}:
        sum {i in Ativos_Por_Setor[s]} b[i] <= card(Ativos_Por_Setor[s]) * y[s]; # se um ativo de um setor for selecionado, o setor deve ser marcado como selecionado

        #as restrições acima garante a sincronia entre as flags de setores e ativos

    # --- RESTRIÇÕES LÓGICAS ---
    # Se o conjunto estiver vazio, a soma será 0 e a restrição não terá efeito.
    
    Condicional_Tec_Energia:
        sum {s in SETOR_TECNOLOGIA} y[s] <= sum {s in SETOR_ENERGIA_ELETRICA} y[s]; # so pode escolher tecnologia se escolher energia

    Min_Diversificacao_Defensivo:
        sum {s in SETORES_DEFENSIVOS} y[s] >= 1; # pelo menos 1 ativo defensivo

    Min_Diversificacao_Ciclico:
        sum {s in SETORES_CICLICOS} y[s] >= 1; # pelo menos 1 ativo cíclico 

    Controle_Commodities:
        sum {s in SETORES_COMMODITIES} y[s] <= 1; # no máximo 1 ativo de commodities

    Minima_Diversificacao_Ampla:
        sum {s in SETORES} y[s] >= 4; # pelo menos 4 setores diferentes na carteira

    Limite_Exposicao_Juros:
    sum {s in SETORES_SENSIVEIS_JUROS} y[s] <= 2; # no máximo 2 setores sensíveis a juros
;
"""


# ===================================================================
# 2. FUNÇÕES DO MODELO
# ===================================================================


def carregar_dados():
    """Carrega todos os arquivos de dados necessários."""
    try:
        print("Carregando arquivos de dados...")
        mu = pd.read_csv("C:/Users/Cliente/Desktop/Dados IPO/vetor_retornos_calculado.csv",
                         index_col=0).squeeze('columns')
        Sigma = pd.read_csv('C:/Users/Cliente/Desktop/Dados IPO/matriz_covariancia_calculada.csv', index_col=0)
        df_mapeamento = pd.read_csv('C:/Users/Cliente/Desktop/Dados IPO/mapeamento_setores.csv')
        print("Dados carregados com sucesso.")
        return mu, Sigma, df_mapeamento

    except FileNotFoundError as e:
        print(f"ERRO: Arquivo de dados não encontrado: {e.filename}")
        return None, None, None


def resolver_com_ampl(params, data, ampl_env):
    mu, Sigma, df_mapeamento = data
    m, W_max, R_target = params['m'], params['W_max'], params['R_target']

    try:
        ampl = AMPL(ampl_env)
        ampl.reset()
        ampl.eval(MODELO_AMPL_STRING)

        print("\nConfigurando o modelo AMPL com os parâmetros da estratégia")
        ativos = Sigma.columns.tolist()
        mapeamento_filtrado = df_mapeamento[df_mapeamento['Ticker'].isin(
            ativos)].set_index('Ticker')['Setor'].to_dict()
        setores_unicos = sorted(list(set(mapeamento_filtrado.values())))

        ampl.set['ATIVOS'] = ativos
        ampl.set['SETORES'] = setores_unicos

        print(f"Setores encontrados nos dados: {setores_unicos}")

        grupos = {
            'SETORES_FINANCEIROS': ['Financials'],
            'SETORES_DEFENSIVOS': ['Consumer Staples', 'Health Care', 'Utilities'],
            'SETORES_CICLICOS': ['Consumer Discretionary', 'Financials', 'Industrials', 'Real Estate', 'Information Technology', 'Communication Services'],
            'SETORES_COMMODITIES': ['Energy', 'Materials'],
            'SETORES_SENSIVEIS_JUROS': ['Financials', 'Utilities', 'Real Estate']
        }

        for nome_grupo, lista_setores in grupos.items():
            setores_existentes_no_grupo = [
                s for s in lista_setores if s in setores_unicos]
            if setores_existentes_no_grupo:
                ampl.get_set(nome_grupo).set_values(
                    setores_existentes_no_grupo)

        setores_regras = {
            'SETOR_SIDERURGIA': 'Siderurgia',
            'SETOR_CONSTRUCAO_CIVIL': 'Construcao_Civil',
            'SETOR_TECNOLOGIA': 'Information Technology',
            'SETOR_ENERGIA_ELETRICA': 'Utilities'
        }

        for nome_conjunto_ampl, nome_setor in setores_regras.items():
            if nome_setor in setores_unicos:
                # se o setor existe, define o conjunto com seu nome
                ampl.get_set(nome_conjunto_ampl).set_values([nome_setor])
            else:
                # se  não existe, define o conjunto como VAZIO
                ampl.get_set(nome_conjunto_ampl).set_values([])
        # -----------------------------------------------------------

        for setor in setores_unicos:
            tickers_do_setor = [
                t for t, s in mapeamento_filtrado.items() if s == setor]
            ampl.get_set('Ativos_Por_Setor')[
                setor].set_values(tickers_do_setor)

        ampl.param['m'] = m
        ampl.param['W_max'] = W_max
        ampl.param['R_target'] = R_target
        ampl.param['mu'].set_values(mu)
        ampl.param['Sigma'].set_values(Sigma)

        ampl.option['solver'] = 'gurobi'
        # faz tipo o print model, para voltar,basta fazer outlev=0, já o mipgap serve para parar quando o gap for menor que 1%
        ampl.option['gurobi_options'] = 'outlev=1 mipgap=0.01 timelimit=60'

        print("Iniciando o solver Gurobi via AMPL...")
        start_time = time.time()
        ampl.solve()
        solve_time = time.time() - start_time

        return ampl, solve_time

    except Exception as e:
        print(f"Ocorreu um erro durante a execução do AMPL: {e}")
        return None, None


def exibir_resultados_ampl(ampl, solve_time, capital_total):
    """Formata e exibe os resultados obtidos do AMPL."""
    solve_result = ampl.get_value('solve_result')
    if solve_result == 'solved':
        print("\n--- Solução Ótima Encontrada ---")
        pesos_otimos_df = ampl.get_variable('w').to_pandas()
        portfolio_selecionado = pesos_otimos_df[pesos_otimos_df['w'] > 0.0001].sort_values(
            by='w', ascending=False)

        print("\n--- Alocação Recomendada ---")
        for ticker, row in portfolio_selecionado.iterrows():
            peso = row['w']
            valor = capital_total * peso
            print(f"{ticker:<10}: {peso:>6.2%} (R$ {valor:,.2f})")

        objetivo_val = ampl.get_objective('Risco_Portfolio').value()
        retorno_val = ampl.get_value('sum {i in ATIVOS} mu[i] * w[i]')

        print("\n--- Resumo do Portfólio ---")
        print(f"Retorno Anual Esperado: {retorno_val*100:.2f}%")
        print(f"Risco Anual (Volatilidade): {np.sqrt(objetivo_val)*100:.2f}%")
        print(f"Tempo de Resolução do Solver: {solve_time:.4f} segundos")
    else:
        print(
            f"\nNão foi possível encontrar uma solução ótima. Status do AMPL: {solve_result}")


def executar_analise_sensibilidade(dados_carregados, ampl_env, m_fixo, range_R_target, range_W_max, taxa_livre_risco):
    """
    Executa o modelo de otimização várias vezes para diferentes valores de R_target e W_max,
    gerando dados para a Fronteira Eficiente e análise do Índice de Sharpe.
    Retornaum DataFrame com os resultados de cada simulação.
    """
    print("\n" + "="*60)
    print(" INICIANDO ANÁLISE DE SENSIBILIDADE ")
    print("="*60)

    resultados_analise = []
    total_runs = len(range_W_max) * len(range_R_target)
    run_count = 0

    # Loop principal para testar cada combinação de parâmetros
    for w_max in range_W_max:
        for r_target in range_R_target:
            run_count += 1
            print(
                f"\n[Execução {run_count}/{total_runs}] Testando W_max = {w_max:.2%} | R_target = {r_target:.2%}")

            params = {'m': m_fixo, 'W_max': w_max, 'R_target': r_target}

            # Reutiliza a sua função de resolução
            ampl, solve_time = resolver_com_ampl(
                params, dados_carregados, ampl_env)

            resultado_simulacao = {
                'W_max': w_max,
                'R_target': r_target,
                'm': m_fixo
            }

            status_sucesso = ['solved', 'limit']

            if ampl and ampl.get_value('solve_result') in status_sucesso:
                risco_portfolio = np.sqrt(
                    ampl.get_objective('Risco_Portfolio').value())
                retorno_portfolio = ampl.get_value(
                    'sum {i in ATIVOS} mu[i] * w[i]')
                sharpe_ratio = (retorno_portfolio -
                                taxa_livre_risco) / risco_portfolio

                resultado_simulacao.update({
                    'Status': 'Solucionado',
                    'Risco': risco_portfolio,
                    'Retorno': retorno_portfolio,
                    'Sharpe': sharpe_ratio
                })
                print(
                    f"--> Solução encontrada! Risco: {risco_portfolio:.2%}, Retorno: {retorno_portfolio:.2%}, Sharpe: {sharpe_ratio:.2f}")
            else:
                status = ampl.get_value('solve_result') if ampl else 'Erro'
                resultado_simulacao.update({
                    'Status': status,
                    'Risco': None,
                    'Retorno': None,
                    'Sharpe': None
                })
                print(
                    f"--> Não foi encontrada uma solução viável. Status: {status}")

            resultados_analise.append(resultado_simulacao)

    print("\n" + "="*60)
    print(" ANÁLISE DE SENSIBILIDADE CONCLUÍDA")
    print("="*60)

    return pd.DataFrame(resultados_analise)


if __name__ == '__main__':
    print("Coomeca otimização aqui")

    try:
        ampl_env = Environment()
    except Exception:
        try:
            caminho_ampl = "C:/Users/Cliente/AMPL"
            ampl_env = Environment(caminho_ampl)
        except Exception as e:
            print(
                f"ERRO CRÍTICO: Não foi possível encontrar os executáveis do AMPL. Verifique a instalação.")
            exit()

    dados = carregar_dados()
    if dados[0] is None:
        exit()

    # numero fixo de ativos para a análise
    m_analise = 15
    # Gera 20 metas de retorno entre 12% e 30%
    targets_de_retorno = np.linspace(0.12, 0.30, 20)
    # Testa 3 níveis de peso máximo
    pesos_maximos = [0.10, 0.15, 0.20]
    # Taxa de juros livre de risco (Selic em 21/10/2025)
    taxa_livre_risco = 0.105

    df_resultados = executar_analise_sensibilidade(
        dados_carregados=dados,
        ampl_env=ampl_env,
        m_fixo=m_analise,
        range_R_target=targets_de_retorno,
        range_W_max=pesos_maximos,
        taxa_livre_risco=taxa_livre_risco
    )

    if not df_resultados.empty:
        df_solucionados = df_resultados[df_resultados['Status'] == 'Solucionado'].copy(
        )

        if not df_solucionados.empty:
            print("\n--- TABELA DE RESULTADOS DA ANÁLISE ---")
            print(df_solucionados.to_string())

            idx_melhor_sharpe = df_solucionados.groupby('W_max')[
                'Sharpe'].idxmax()
            melhores_carteiras = df_solucionados.loc[idx_melhor_sharpe]

            print("\n--- MELHORES CARTEIRAS (MAIOR SHARPE) ENCONTRADAS ---")
            print(melhores_carteiras)

            # PLOTANDO A FRONTEIRA EFICIENTE
            print("\nGerando gráfico da Fronteira Eficiente...")
            plt.figure(figsize=(12, 8))

            sns.scatterplot(
                data=df_solucionados,
                x='Risco', y='Retorno', hue='W_max', size='Sharpe',
                sizes=(40, 250), palette='viridis', style='W_max', legend='full'
            )
            sns.scatterplot(
                data=melhores_carteiras, x='Risco', y='Retorno',
                color='red', marker='*', s=500, label='Ótimo Sharpe'
            )

            plt.title(
                'Fronteira Eficiente - Análise de Sensibilidade', fontsize=16)
            plt.xlabel('Risco Anual (Volatilidade)', fontsize=12)
            plt.ylabel('Retorno Anual Esperado', fontsize=12)
            plt.gca().yaxis.set_major_formatter(
                plt.FuncFormatter(lambda y, _: f'{y:.1%}'))
            plt.gca().xaxis.set_major_formatter(
                plt.FuncFormatter(lambda x, _: f'{x:.1%}'))
            plt.legend(title='W_max / Sharpe')
            plt.grid(True, linestyle='--', alpha=0.6)
            plt.show()
        else:
            print(
                "\nAnálise concluída, mas nenhuma solução viável foi encontrada com os parâmetros fornecidos.")
            print(
                "Tente usar uma meta de retorno (R_target) mais baixa ou aumentar o número de ativos (m).")
