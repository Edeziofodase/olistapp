import streamlit as st
import folium
import pandas as pd
import os
from folium.plugins import FastMarkerCluster
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import st_folium
from folium import FeatureGroup, LayerControl
import kagglehub


# ======== COLE SEU TOKEN AQUI ========
KAGGLE_USERNAME = "edezio"      # Exemplo: "joaosilva"
KAGGLE_KEY = "KGAT_6b3c39cf692d9cfe6dbdf5ce9f431574"             # Chave de 40 caracteres
# =====================================

# Configura ambiente Kaggle
os.environ['KAGGLE_USERNAME'] = KAGGLE_USERNAME
os.environ['KAGGLE_KEY'] = KAGGLE_KEY


# Configuração da página
st.set_page_config(layout="wide")
st.title('📊 Análise Geral - Olist E-commerce')

# ========== FUNÇÃO PARA CARREGAR DADOS ==========
@st.cache_data
def load_olist_data():
    """
    Carrega todos os datasets do Olist do Kaggle
    Retorna: (dataset_path, dataframes_dict)
    """
    dataset_path = "olistbr/brazilian-ecommerce"
    
    try:
        # Baixar dataset do Kaggle
        st.info("📥 Baixando dataset do Kaggle...")
        path = kagglehub.dataset_download(dataset_path)
        
        # Dicionário para armazenar DataFrames
        dataframes = {}
        
        # Lista todos os arquivos no diretório
        for file_name in os.listdir(path):
            if file_name.endswith('.csv'):
                file_path = os.path.join(path, file_name)
                
                # Carrega o CSV
                df = pd.read_csv(file_path, encoding='utf-8')
                
                # Armazena no dicionário
                dataframes[file_name] = df
        
        st.success(f"✅ {len(dataframes)} arquivos carregados com sucesso!")
        return path, dataframes
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        return None, {}

# ========== CARREGAR DADOS ==========
if 'data_loaded' not in st.session_state:
    with st.spinner("Carregando dados do Kaggle (pode levar alguns minutos)..."):
        dataset_path, dfs = load_olist_data()
        
        if dfs:
            st.session_state.data_loaded = True
            st.session_state.dataset_path = dataset_path
            st.session_state.dfs = dfs
            st.success("🎉 Dados carregados com sucesso!")
        else:
            st.error("Não foi possível carregar os dados")
            st.stop()
else:
    dataset_path = st.session_state.dataset_path
    dfs = st.session_state.dfs

# ========== ACESSAR OS DATAFRAMES ==========
customers_df = dfs.get('olist_customers_dataset.csv')
geolocation_df = dfs.get('olist_geolocation_dataset.csv')
orders_df = dfs.get('olist_orders_dataset.csv')
order_items_df = dfs.get('olist_order_items_dataset.csv')
payments_df = dfs.get('olist_order_payments_dataset.csv')
reviews_df = dfs.get('olist_order_reviews_dataset.csv')
products_df = dfs.get('olist_products_dataset.csv')
sellers_df = dfs.get('olist_sellers_dataset.csv')

# ========== MOSTRAR RESUMO ==========
st.subheader("📋 Resumo do Dataset")

# KPIs
col1, col2, col3, col4 = st.columns(4)

with col1:
    if customers_df is not None:
        st.metric("Clientes", f"{len(customers_df):,}")
    else:
        st.metric("Clientes", "N/A")

with col2:
    if orders_df is not None:
        st.metric("Pedidos", f"{len(orders_df):,}")
    else:
        st.metric("Pedidos", "N/A")

with col3:
    if products_df is not None:
        st.metric("Produtos", f"{len(products_df):,}")
    else:
        st.metric("Produtos", "N/A")

with col4:
    if sellers_df is not None:
        st.metric("Vendedores", f"{len(sellers_df):,}")
    else:
        st.metric("Vendedores", "N/A")

# ========== TABELA DE ARQUIVOS ==========
st.subheader("📁 Arquivos Carregados")

files_info = []
for file_name, df in dfs.items():
    files_info.append({
        'Arquivo': file_name,
        'Linhas': f"{df.shape[0]:,}",
        'Colunas': df.shape[1],
        'Tamanho': f"{(df.memory_usage(deep=True).sum() / (1024*1024)):.2f} MB"
    })

files_df = pd.DataFrame(files_info)
st.dataframe(files_df, use_container_width=True, hide_index=True)

# ========== MAPA DE GEOLOCALIZAÇÃO ==========
st.markdown("---")
st.subheader("🗺️ Comunidade Olist")

if geolocation_df is not None:
    # Limpar dados
    geolocation_clean = geolocation_df.dropna(subset=['geolocation_lat', 'geolocation_lng'])
    
    if len(geolocation_clean) > 0:
        # Criar mapa
        mapa = folium.Map(
            location=[geolocation_clean['geolocation_lat'].mean(), 
                     geolocation_clean['geolocation_lng'].mean()],
            zoom_start=5,
            tiles='CartoDB dark_matter',
            width='100%'
        )
        
        # Adicionar clusters
        data = list(zip(
            geolocation_clean['geolocation_lat'].astype(float),
            geolocation_clean['geolocation_lng'].astype(float)
        ))
        
        FastMarkerCluster(data).add_to(mapa)
        
        # Exibir mapa
        try:
            st_folium(mapa, width=1200, height=600)
        except:
            # Método alternativo se st_folium falhar
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as f:
                mapa.save(f.name)
                with open(f.name, 'r', encoding='utf-8') as html_file:
                    html_content = html_file.read()
                os.unlink(f.name)
            
            st.components.v1.html(html_content, width=1200, height=600)
        
        st.info(f"📍 {len(data):,} localizações no mapa")
    else:
        st.warning("Nenhum dado de geolocalização válido encontrado")
else:
    st.warning("Arquivo de geolocalização não encontrado")

# ========== ANÁLISE DE PEDIDOS ==========
st.markdown("---")
st.subheader("📦 Análise de Pedidos")

if orders_df is not None:
    # Status dos pedidos
    st.write("**Status dos Pedidos:**")
    
    if 'order_status' in orders_df.columns:
        status_counts = orders_df['order_status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Quantidade']
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Gráfico de barras simples
            st.bar_chart(status_counts.set_index('Status'))
        
        with col2:
            st.dataframe(status_counts, use_container_width=True)


# ========== ANÁLISE DE TEMPO DE ENTREGA ==========
st.markdown("---")
st.subheader("⏱️ Análise de Tempo de Entrega")

if orders_df is not None:
    # Verificar se as colunas de data existem
    colunas_data = ['order_purchase_timestamp', 'order_delivered_customer_date', 
                    'order_estimated_delivery_date']
    
    colunas_existentes = [col for col in colunas_data if col in orders_df.columns]
    
    if len(colunas_existentes) >= 3:
        # Converter colunas para datetime
        orders_clean = orders_df.copy()
        for col in colunas_existentes:
            orders_clean[col] = pd.to_datetime(orders_clean[col], errors='coerce')
        
        # Filtrar apenas pedidos entregues
        pedidos_entregues = orders_clean[
            (orders_clean['order_status'] == 'delivered') & 
            (orders_clean['order_delivered_customer_date'].notna())
        ].copy()
        
        if len(pedidos_entregues) > 0:
            # Calcular tempo real de entrega (dias)
            pedidos_entregues['tempo_real_dias'] = (
                pedidos_entregues['order_delivered_customer_date'] - 
                pedidos_entregues['order_purchase_timestamp']
            ).dt.total_seconds() / (24 * 3600)
            
            # Calcular tempo estimado (dias)
            pedidos_entregues['tempo_estimado_dias'] = (
                pedidos_entregues['order_estimated_delivery_date'] - 
                pedidos_entregues['order_purchase_timestamp']
            ).dt.total_seconds() / (24 * 3600)
            
            # Calcular diferença (positiva = atraso, negativa = adiantado)
            pedidos_entregues['diferenca_dias'] = (
                pedidos_entregues['tempo_real_dias'] - 
                pedidos_entregues['tempo_estimado_dias']
            )
            
            # KPIs principais
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                tempo_medio_real = pedidos_entregues['tempo_real_dias'].mean()
                st.metric("⏳ Tempo Médio Real", f"{tempo_medio_real:.1f} dias")
            
            with col2:
                tempo_medio_estimado = pedidos_entregues['tempo_estimado_dias'].mean()
                st.metric("📅 Tempo Médio Estimado", f"{tempo_medio_estimado:.1f} dias")
            
            with col3:
                diferenca_media = pedidos_entregues['diferenca_dias'].mean()
                st.metric("📊 Diferença Média", 
                         f"{diferenca_media:+.1f} dias",
                         delta=f"{diferenca_media:+.1f} dias")
            
            with col4:
                percentual_no_prazo = (pedidos_entregues['diferenca_dias'] <= 0).mean() * 100
                st.metric("✅ Entregas no Prazo", f"{percentual_no_prazo:.1f}%")
            
            # Tabela detalhada
            st.write("**📋 Estatísticas Detalhadas de Entrega:**")
            
            estatisticas = {
                'Métrica': [
                    'Tempo Mínimo de Entrega (dias)',
                    'Tempo Máximo de Entrega (dias)',
                    'Mediana de Entrega (dias)',
                    'Desvio Padrão (dias)',
                    'Entregas Antecipadas (< -1 dia)',
                    'Entregas Atrasadas (> +1 dia)',
                    'Entregas Pontuais (± 1 dia)'
                ],
                'Valor': [
                    f"{pedidos_entregues['tempo_real_dias'].min():.1f}",
                    f"{pedidos_entregues['tempo_real_dias'].max():.1f}",
                    f"{pedidos_entregues['tempo_real_dias'].median():.1f}",
                    f"{pedidos_entregues['tempo_real_dias'].std():.1f}",
                    f"{(pedidos_entregues['diferenca_dias'] < -1).sum():,}",
                    f"{(pedidos_entregues['diferenca_dias'] > 1).sum():,}",
                    f"{(abs(pedidos_entregues['diferenca_dias']) <= 1).sum():,}"
                ],
                'Porcentagem': [
                    "-",
                    "-",
                    "-",
                    "-",
                    f"{(pedidos_entregues['diferenca_dias'] < -1).mean() * 100:.1f}%",
                    f"{(pedidos_entregues['diferenca_dias'] > 1).mean() * 100:.1f}%",
                    f"{(abs(pedidos_entregues['diferenca_dias']) <= 1).mean() * 100:.1f}%"
                ]
            }
            
            estatisticas_df = pd.DataFrame(estatisticas)
            st.dataframe(estatisticas_df, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            
                    # Distribuição da diferença
            st.write("**📈 Distribuição da Diferença entre Real e Estimado:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Dois boxplots lado a lado
                fig = go.Figure()
                
                # Boxplot do tempo real
                fig.add_trace(go.Box(
                    y=pedidos_entregues['tempo_real_dias'],
                    name='Tempo Real',
                    marker_color='#2E86AB',
                    boxmean=True  # Mostra a média
                ))
                
                # Boxplot do tempo estimado
                fig.add_trace(go.Box(
                    y=pedidos_entregues['tempo_estimado_dias'],
                    name='Tempo Estimado',
                    marker_color='#A23B72',
                    boxmean=True
                ))
                
                fig.update_layout(
                    title='Comparação: Tempo Real vs Tempo Estimado',
                    yaxis_title='Dias',
                    height=500,
                    boxmode='group'  # Coloca os boxplots lado a lado
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Categorização das entregas
                categorias = pd.cut(
                    pedidos_entregues['diferenca_dias'],
                    bins=[-float('inf'), -3, -1, 1, 3, float('inf')],
                    labels=['Muito Adiantada (-3+ dias)', 'Adiantada (1-3 dias)', 
                           'Pontual (±1 dia)', 'Atrasada (1-3 dias)', 
                           'Muito Atrasada (3+ dias)']
                )
                
                categoria_counts = categorias.value_counts().reset_index()
                categoria_counts.columns = ['Categoria', 'Quantidade']
                categoria_counts['Porcentagem'] = (
                    categoria_counts['Quantidade'] / len(pedidos_entregues) * 100
                ).round(1)
                
                st.write("**Categorização das Entregas:**")
                st.dataframe(categoria_counts, use_container_width=True, hide_index=True)
            
            # Análise mensal
            st.subheader("**📅 Tendência Mensal de Tempos de Entrega:**")
            
            pedidos_entregues['mes_ano'] = pedidos_entregues['order_purchase_timestamp'].dt.to_period('M')
            tendencia_mensal = pedidos_entregues.groupby('mes_ano').agg({
                'tempo_real_dias': 'mean',
                'tempo_estimado_dias': 'mean',
                'diferenca_dias': 'mean'
            }).reset_index()
            tendencia_mensal['mes_ano'] = tendencia_mensal['mes_ano'].astype(str)
            
            # Gráfico de linha
            fig_tendencia = px.line(
                tendencia_mensal,
                x='mes_ano',
                y=['tempo_real_dias', 'tempo_estimado_dias'],
                title='Evolução dos Tempos de Entrega',
                labels={'value': 'Dias', 'variable': 'Tipo', 'mes_ano': 'Mês'},
                markers=True
            )
            fig_tendencia.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_tendencia, use_container_width=True)
            
            # Amostra de dados
            with st.expander("🔍 Ver Amostra dos Dados Calculados"):
                amostra = pedidos_entregues[[
                    'order_id', 'order_purchase_timestamp', 
                    'order_delivered_customer_date', 'order_estimated_delivery_date',
                    'tempo_real_dias', 'tempo_estimado_dias', 'diferenca_dias'
                ]].head(10)
                st.dataframe(amostra, use_container_width=True)
            
        else:
            st.warning("Nenhum pedido entregue encontrado para análise de tempo.")
    else:
        colunas_faltando = [col for col in colunas_data if col not in orders_df.columns]
        st.warning(f"Colunas necessárias não encontradas: {', '.join(colunas_faltando)}")
else:
    st.warning("Dataset de pedidos não disponível para análise de tempo de entrega.")

# ========== PREPARAR DADOS DE LOCALIZAÇÃO ==========
# Adicione APÓS a seção "ACESSAR OS DATAFRAMES"

def preparar_localizacao_clientes():
    """Junta dados de clientes com geolocalização"""
    if customers_df is not None and geolocation_df is not None:
        clientes_com_geo = pd.merge(
            customers_df,
            geolocation_df,
            left_on='customer_zip_code_prefix',
            right_on='geolocation_zip_code_prefix',
            how='left'
        )
        clientes_com_geo = clientes_com_geo.drop_duplicates(subset=['customer_id'])
        return clientes_com_geo
    return None

def preparar_localizacao_vendedores():
    """Junta dados de vendedores com geolocalização"""
    if sellers_df is not None and geolocation_df is not None:
        vendedores_com_geo = pd.merge(
            sellers_df,
            geolocation_df,
            left_on='seller_zip_code_prefix',
            right_on='geolocation_zip_code_prefix',
            how='left'
        )
        vendedores_com_geo = vendedores_com_geo.drop_duplicates(subset=['seller_id'])
        return vendedores_com_geo
    return None

# Preparar os dados
clientes_com_localizacao = preparar_localizacao_clientes()
vendedores_com_localizacao = preparar_localizacao_vendedores()

# ========== MAPA COMPARATIVO: VENDEDORES vs CLIENTES ==========
# Adicione APÓS a seção "TABELA DE ARQUIVOS"

st.markdown("---")
st.subheader("🗺️ Mapa Comparativo: Vendedores vs Clientes")

if vendedores_com_localizacao is not None and clientes_com_localizacao is not None:
    # Filtrar registros com coordenadas válidas
    vendedores_validos = vendedores_com_localizacao.dropna(
        subset=['geolocation_lat', 'geolocation_lng']
    )
    clientes_validos = clientes_com_localizacao.dropna(
        subset=['geolocation_lat', 'geolocation_lng']
    )
    
    # Sliders para controle
    amostra_vendedores = st.slider(
        "Número de vendedores:", 
        min_value=100, 
        max_value=min(2000, len(vendedores_validos)),
        value=min(500, len(vendedores_validos)),
        step=100
    )
    
    amostra_clientes = st.slider(
        "Número de clientes:", 
        min_value=100, 
        max_value=min(2000, len(clientes_validos)),
        value=min(500, len(clientes_validos)),
        step=100
    )
    
    vendedores_amostra = vendedores_validos.sample(
        n=min(amostra_vendedores, len(vendedores_validos)), 
        random_state=42
    )
    clientes_amostra = clientes_validos.sample(
        n=min(amostra_clientes, len(clientes_validos)), 
        random_state=42
    )
    
    # Criar mapa
    from folium import FeatureGroup, LayerControl
    
    mapa_comparativo = folium.Map(
        location=[-15, -55],
        zoom_start=4,
        tiles='CartoDB positron',
        width='100%'
    )
    
    # Grupos separados
    vendedores_group = FeatureGroup(name='🏪 Vendedores', show=True)
    clientes_group = FeatureGroup(name='👥 Clientes', show=True)
    
    # Adicionar vendedores (vermelho)
    for idx, row in vendedores_amostra.iterrows():
        folium.CircleMarker(
            location=[row['geolocation_lat'], row['geolocation_lng']],
            radius=5,
            popup=f"<b>Vendedor</b><br>{row.get('seller_city', '')}, {row.get('seller_state', '')}",
            color='#FF0000',
            fill=True,
            fill_color='#FF0000',
            fill_opacity=0.7
        ).add_to(vendedores_group)
    
    # Adicionar clientes (azul)
    for idx, row in clientes_amostra.iterrows():
        folium.CircleMarker(
            location=[row['geolocation_lat'], row['geolocation_lng']],
            radius=4,
            popup=f"<b>Cliente</b><br>{row.get('customer_city', '')}, {row.get('customer_state', '')}",
            color='#1E90FF',
            fill=True,
            fill_color='#1E90FF',
            fill_opacity=0.6
        ).add_to(clientes_group)
    
    # Adicionar ao mapa
    vendedores_group.add_to(mapa_comparativo)
    clientes_group.add_to(mapa_comparativo)
    LayerControl().add_to(mapa_comparativo)
    
    # Exibir
    try:
        st_folium(mapa_comparativo, width=1200, height=600)
    except:
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as f:
            mapa_comparativo.save(f.name)
            with open(f.name, 'r', encoding='utf-8') as html_file:
                html_content = html_file.read()
            os.unlink(f.name)
        st.components.v1.html(html_content, width=1200, height=600)
    
    # Estatísticas rápidas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Vendedores", len(vendedores_amostra))
    with col2:
        st.metric("Clientes", len(clientes_amostra))
    with col3:
        st.metric("Total", len(vendedores_amostra) + len(clientes_amostra))
    
    st.info("Use o controle no canto superior direito para mostrar/esconder cada grupo")
else:
    st.warning("Dados de localização insuficientes para o mapa comparativo")

# ========== BOTÃO PARA RECARREGAR ==========
if st.button("🔄 Recarregar Dados"):
    st.cache_data.clear()
    st.session_state.clear()
    st.rerun()