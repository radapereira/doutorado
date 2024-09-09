from pymongo import MongoClient
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import time

# Mapeamento dos IDs dos nodos para seus sensores e variáveis correspondentes
sensor_map = {
    '124b002281ff46': 'H2S',       # ppm
    '124b002e845ca0': 'CH4',       # %
    '124b002f40ce97': 'NH3',       # ppm
    '124b002e845ca0_Temp': 'Temperatura',  # °C
    '124b002e845ca0_Hum': 'Humidade',      # %
    '124b002e846087': 'CO2',       # ppm
    '124b002e845f31': 'NO2'        # ppm
}

# Funções de conversão de sinal para unidades apropriadas com base nos datasheets
def convert_signal(sensor_name, signal):
    if sensor_name == 'H2S':
        return max(0, (signal - 0.6) / 2.4 * 100)  # Conversão H2S com base no datasheet&#8203;:contentReference[oaicite:0]{index=0}
    elif sensor_name == 'NH3':
        return max(0, (signal - 0.6) / 2.4 * 100)  # Conversão NH3 com base no datasheet&#8203;:contentReference[oaicite:1]{index=1}
    elif sensor_name == 'NO2':
        return max(0, (2 - signal) / 2 * 20)  # Conversão NO2 com base no datasheet&#8203;:contentReference[oaicite:2]{index=2}
    elif sensor_name == 'CO2':
        return max(0, signal / 2 * 5000)  # Conversão CO2 com base no datasheet&#8203;:contentReference[oaicite:3]{index=3}
    elif sensor_name == 'CH4':
        return max(0, (signal - 0.4) / 1.6 * 10)  # Conversão CH4 com base no datasheet&#8203;:contentReference[oaicite:4]{index=4}
    elif sensor_name == 'Temperatura':
        return max(-45, (signal * 170 / 100) - 45)  # Conversão de temperatura&#8203;:contentReference[oaicite:5]{index=5}
    elif sensor_name == 'Humidade':
        return max(0, signal)  # Humidade vai de 0 a 100%&#8203;:contentReference[oaicite:6]{index=6}
    else:
        return signal

# URL de conexão ao MongoDB
mongo_url = "mongodb://179.124.146.5:27017/"

# Conectar ao MongoDB
client = MongoClient(mongo_url)

# Acessar o banco de dados "Doutorado"
db = client["Doutorado"]

# Acessar a coleção "Sensores"
collection = db["Sensores"]

# Criar DataFrame inicial
df = pd.DataFrame(columns=['ID', 'Sensor Name', 'Timestamp', 'Converted Value'])

# Função para buscar o último registro inserido
def get_latest_record():
    return collection.find().sort([("_id", -1)]).limit(1)

# Função para buscar registros após o último registro lido
def get_next_records(last_timestamp):
    return collection.find({"status.timestamp": {"$gt": last_timestamp}}).sort("status.timestamp", 1)

# Função para atualizar gráficos
def update_plots(df):
    unique_sensors = df['Sensor Name'].unique()
    num_sensors = len(unique_sensors)
    
    # Cria subplots, com um gráfico por sensor
    fig, axs = plt.subplots(num_sensors, 1, figsize=(10, 5 * num_sensors))  # Aumenta o tamanho para acomodar todos os gráficos

    if num_sensors == 1:
        axs = [axs]  # Garantir que seja iterável se houver apenas um gráfico
    
    # Para cada sensor, cria um gráfico separado
    for ax, sensor in zip(axs, unique_sensors):
        sensor_df = df[df['Sensor Name'] == sensor]
        ax.plot(sensor_df['Timestamp'], sensor_df['Converted Value'], label=sensor)
        
        # Ajusta título e rótulos de eixos
        ax.set_title(f'{sensor} - Evolução ao Longo do Tempo')
        ax.set_xlabel('Tempo')
        ax.set_ylabel('Valor Convertido')
        ax.legend()
        ax.grid(True)
        plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    plt.show()

# Loop de leitura contínua
try:
    # Ler o último registro inicial
    last_record = get_latest_record()
    last_timestamp = last_record[0]['status'][-1]['timestamp']

    while True:
        # Buscar registros após o último timestamp
        new_records = get_next_records(last_timestamp)

        new_data = []
        for document in new_records:
            sensor_name = sensor_map.get(document.get('id'), 'Unknown Sensor')
            for status in document.get('status', []):
                converted_signal = convert_signal(sensor_name, status['signal'])
                formatted_record = {
                    'ID': document.get('id'),
                    'Sensor Name': sensor_name,
                    'Timestamp': datetime.fromtimestamp(status['timestamp']).strftime('%d/%m/%Y %H:%M:%S'),
                    'Converted Value': converted_signal
                }
                new_data.append(formatted_record)
                last_timestamp = status['timestamp']  # Atualizar o timestamp para o próximo ciclo

        # Adicionar novos dados ao DataFrame e salvar no CSV
        if new_data:
            df = pd.concat([df, pd.DataFrame(new_data)], ignore_index=True)
            df.to_csv("sensoresDataset_converted.csv", index=False, encoding='utf-8-sig')

            # Atualizar os gráficos com os dados atuais
            update_plots(df)
        
        time.sleep(2)  # Aguardar um pouco antes da próxima leitura

except KeyboardInterrupt:
    print("Interrompido pelo usuário.")
finally:
    plt.show()

