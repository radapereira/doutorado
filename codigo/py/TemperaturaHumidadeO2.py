from flask import Flask, render_template, send_file
import matplotlib
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
from datetime import datetime
from pymongo import MongoClient

matplotlib.use('Agg')  # Necessário para servidores sem interface gráfica

# Configuração Flask
app = Flask(__name__)

# Configuração MongoDB
mongo_url='mongodb://179.124.146.5:27017/'
client = MongoClient(mongo_url)
db = client['Doutorado']  # Nome do banco de dados
collection = db['Sensores']  # Coleção com os dados dos sensores

# Mapeamento de sensores conforme datasheets fornecidos
sensor_map = {
    '124b002e845ca0_Temp': ('Temperatura', '°C', lambda x: max(-45, (x * 170 / 100) - 45)),
    '124b002e845ca0_Hum': ('Humidade', '%', lambda x: max(0, x)),
    '124b002e845ca0_O2': ('O2', '%', lambda x: max(0, 25 * (1.5 - x) / 1.5)),
#    '124b002e846087_CO2': ('CO2', 'ppm', lambda x: x * 5000),  # Conversão baseada no datasheet
#    '124b002e845ca0_CH4': ('CH4', '%', lambda x: x * 10)  # Conversão CH4
}

# Função para atualizar os dados a partir do MongoDB
def atualizar_dados():
    cursor = collection.find()
    df = pd.DataFrame(columns=['Sensor Name', 'Timestamp', 'Converted Value'])

    # Processar novos dados
    for document in cursor:
        status = document.get('status', {})
        timestamp = status.get('timestamp')
        if timestamp:
            formatted_timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

            # Iterar sobre os sensores no status
            for sensor in status.get('sensors', []):
                sensor_name, unit, conversion_func = sensor_map.get(sensor['id'], ('Unknown Sensor', '', lambda x: x))
                converted_value = conversion_func(sensor['data'])

                new_row = pd.DataFrame([{
                    'Sensor Name': sensor_name,
                    'Timestamp': formatted_timestamp,
                    'Converted Value': converted_value
                }])
                df = pd.concat([df, new_row], ignore_index=True)

    # Salvar dados no CSV
    df.to_csv("sensor_data_real_time.csv", index=False, encoding='utf-8-sig')
    return df

# Função para gerar o gráfico
@app.route('/grafico.png')
def gerar_grafico():
    df = atualizar_dados()  # Atualiza os dados antes de gerar o gráfico

    fig, axs = plt.subplots(3, 1, figsize=(10, 10))

    for ax, (sensor_name, unit) in zip(axs, sensor_map.values()):
        sensor_df = df[df['Sensor Name'] == sensor_name]

        if sensor_df.empty:
            continue
        
        ax.plot(pd.to_datetime(sensor_df['Timestamp']), sensor_df['Converted Value'], label=f'{sensor_name} ({unit})')
        ax.set_title(f'{sensor_name}')
        ax.set_xlabel('Data e Hora')
        ax.set_ylabel(f'Valor Convertido ({unit})')
        ax.grid(True)

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y\n%H:%M'))
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
        ax.legend()

    plt.tight_layout()
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close(fig)
    return send_file(img, mimetype='image/png')

# Rota principal que exibe o gráfico
@app.route('/')
def index():
    return render_template('index.html')

# Inicializar o servidor Flask
if __name__ == '__main__':
    app.run(debug=True)

