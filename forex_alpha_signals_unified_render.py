#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import logging
import time
import os

# Configuração do Logging
log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Adiciona um handler para exibir logs no console
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

# Variáveis de ambiente (ou padrão)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID")
ANALYSIS_INTERVAL_MINUTES = int(os.environ.get("ANALYSIS_INTERVAL_MINUTES", 10))
DEFAULT_TIMEFRAME = os.environ.get("DEFAULT_TIMEFRAME", "15m")
DEFAULT_STOP_DEV = float(os.environ.get("DEFAULT_STOP_DEV", 0.003))
DEFAULT_TAKE_DEV = float(os.environ.get("DEFAULT_TAKE_DEV", 0.003))

# Dicionário de ativos
ativos = {
    "Câmbio (Forex)": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"],
    "Criptomoedas": ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"],
    "Ações": ["AAPL", "MSFT", "AMZN", "PETR4.SA", "VALE3.SA"],
    "Commodities": ["GC=F", "CL=F", "SI=F"]
}

# Função para enviar mensagem via Telegram (simulada, pois não temos a biblioteca real)
def send_telegram_message(message):
    logger.info(f"Enviando mensagem para Telegram: {message}")
    # Aqui iria a lógica real de envio via API do Telegram
    # Exemplo: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={'chat_id': TELEGRAM_CHAT_ID, 'text': message})
    print(f"Mensagem para Telegram (simulado): {message}")

# Funções de análise (adaptadas para rodar no mesmo processo)
def obter_dados(ticker, tf):
    logger.info(f"Obtendo dados para {ticker} com timeframe {tf}")
    try:
        data = yf.download(ticker, period="60d" if tf in ["15m", "30m"] else "2y", interval=tf)
        if data.empty:
            logger.warning(f"Nenhum dado retornado para {ticker} com timeframe {tf}")
            return None
        data.dropna(inplace=True)
        return data
    except Exception as e:
        logger.error(f"Erro ao obter dados para {ticker}: {e}")
        return None

def analisar_ativo(df, ativo_nome, mercado_nome, stop_dev, take_dev):
    logger.info(f"Analisando {ativo_nome} do mercado {mercado_nome}")
    if df is None or len(df) < 21: # Mínimo para alguns indicadores
        logger.warning(f"Dados insuficientes para análise de {ativo_nome}")
        return None

    try:
        # Calcula indicadores
        df['EMA9'] = EMAIndicator(df['Close'], window=9).ema_indicator()
        df['EMA21'] = EMAIndicator(df['Close'], window=21).ema_indicator()
        df['MACD'] = MACD(df['Close']).macd()
        df['RSI'] = RSIIndicator(df['Close']).rsi()
        bollinger = BollingerBands(df['Close'], window=20, window_dev=2)
        df['BB_High'] = bollinger.bollinger_hband()
        df['BB_Low'] = bollinger.bollinger_lband()
        df.dropna(inplace=True)

        if df.empty:
            logger.warning(f"Dados insuficientes para {ativo_nome} após cálculo de indicadores.")
            return None

        # Lógica de decisão (simplificada para exemplo)
        last_row = df.iloc[-1]
        sinal = "Neutro"
        if last_row['Close'] > last_row['EMA9'] and last_row['RSI'] < 30:
            sinal = "Compra"
        elif last_row['Close'] < last_row['EMA9'] and last_row['RSI'] > 70:
            sinal = "Venda"

        if sinal != "Neutro":
            mensagem = f"Sinal para {ativo_nome} ({mercado_nome}): {sinal} @ {last_row['Close']:.4f}"
            send_telegram_message(mensagem)
            return {
                "ativo": ativo_nome,
                "sinal": sinal,
                "preco_entrada": last_row['Close'],
                "stop_loss": last_row['Close'] * (1 - stop_dev) if sinal == "Compra" else last_row['Close'] * (1 + stop_dev),
                "take_profit": last_row['Close'] * (1 + take_dev) if sinal == "Compra" else last_row['Close'] * (1 - stop_dev),
                "mensagem": mensagem
            }
        return None
    except Exception as e:
        logger.error(f"Erro ao analisar {ativo_nome}: {e}")
        return None

def run_analysis():
    logger.info("Iniciando ciclo de análise...")
    timeframe = DEFAULT_TIMEFRAME
    stop_dev = DEFAULT_STOP_DEV
    take_dev = DEFAULT_TAKE_DEV

    for mercado, lista_ativos in ativos.items():
        logger.info(f"Analisando mercado: {mercado}")
        for ativo_ticker in lista_ativos:
            dados_ativo = obter_dados(ativo_ticker, timeframe)
            if dados_ativo is not None:
                resultado_analise = analisar_ativo(dados_ativo, ativo_ticker, mercado, stop_dev, take_dev)
                if resultado_analise:
                    logger.info(f"Sinal gerado: {resultado_analise}")
            time.sleep(5) # Pausa para não sobrecarregar a API
    logger.info("Ciclo de análise concluído.")

# --- Interface Streamlit ---
st.set_page_config(layout="wide", page_title="Forex Alpha Signals Dashboard")
st.title("Forex Alpha Signals Dashboard")

# Botão para iniciar a análise (apenas para demonstração, idealmente seria um loop contínuo)
if st.button("Iniciar Análise Manual"):
    st.info("Iniciando análise... Verifique os logs do console para detalhes.")
    run_analysis()
    st.success("Análise concluída!")

# Loop principal para manter a aplicação rodando e realizar análises periódicas
# Esta parte é conceitual, pois o Streamlit não é ideal para tarefas de fundo de longa duração.
# Para produção, considere separar o worker e usar um agendador.

if 'running' not in st.session_state:
    st.session_state.running = False

if st.sidebar.button("Iniciar Análise Contínua"):
    st.session_state.running = True
    st.sidebar.success("Análise contínua iniciada!")

if st.sidebar.button("Parar Análise Contínua"):
    st.session_state.running = False
    st.sidebar.warning("Análise contínua parada.")

if st.session_state.running:
    st.sidebar.write("Status: Rodando análise...")
    # Este loop é apenas para demonstração e pode não ser ideal para produção em Streamlit.
    # Em um cenário real, você usaria um agendador externo ou um serviço de background.
    while st.session_state.running:
        run_analysis()
        # Espera o intervalo definido antes da próxima execução
        # É importante adicionar um pequeno delay para evitar sobrecarga da CPU
        # e permitir que o Streamlit processe outras interações, se houver.
        time.sleep(ANALYSIS_INTERVAL_MINUTES * 60)
else:
    st.sidebar.write("Status: Parado")

# Exibição de logs (simples)
st.subheader("Logs da Análise")
log_placeholder = st.empty()

# Para este exemplo, vamos apenas simular a escrita de logs.
# Em uma aplicação real, você leria de um arquivo de log ou de um sistema de logging.
log_placeholder.text_area("Logs", "Aguardando logs...", height=300)

# Nota: Para uma aplicação real com tarefas de fundo, especialmente com Streamlit,
# é altamente recomendável usar bibliotecas como Celery com Redis/RabbitMQ,
# ou serviços como APScheduler, e possivelmente um banco de dados para armazenar os resultados
# de forma persistente e desacoplada da interface do usuário.
# Este exemplo é uma simplificação para ilustrar a estrutura básica.

