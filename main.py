import json
import os
import time
from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from flask_cors import CORS 
from datetime import datetime

app = Flask(__name__)
CORS(app)
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

# Inicialización del cliente OpenAI
client = OpenAI(api_key= OPENAI_API_KEY)

# ID del asistente
assistant_id = os.environ['ASSIST_ID']

# Archivo para almacenar las respuestas
response_file = 'respuestas_entrevista.txt'
  

@app.route('/start', methods=['POST'])
def start_conversation():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'error': 'Mensaje no proporcionado'}), 400

    # Usa directamente user_message como contenido
    message_content = user_message

    if "asesoria" in message_content.lower():
        thread = client.beta.threads.create(messages=[{"role": "user", "content": user_message}])
        return jsonify({'thread_id': thread.id, 'message': 'Hilo de entrevista creado exitosamente'})

    return jsonify({'error': 'No se detectó una entrevista en el mensaje'}), 400


@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    thread_id = data.get('thread_id')
    user_input = data.get('message', '')

    if not thread_id:
        return jsonify({"error": "Missing thread_id"}), 400
    client.beta.threads.messages.create(thread_id=thread_id, role="user", content=user_input)
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id)
    return jsonify({"run_id": run.id})
  
  
@app.route('/check', methods=['POST'])
def check_run_status():
    data = request.json
    thread_id = data.get('thread_id')
    run_id = data.get('run_id')
    user_response = data.get('user_response')

    print("Datos recibidos en /check:", {
        "thread_id": thread_id,
        "run_id": run_id,
        "user_response": user_response
    })

    if not thread_id or not run_id:
        return jsonify({"response": "error"})
    start_time = time.time()
    while time.time() - start_time < 8:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        
        if run_status.status == 'completed':
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            # Extraemos directamente el valor del contenido
            message_content = messages.data[0].content[0].text.value  # Cambio aquí
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if user_response:
                print("Guardando interacción...")
                print("Respuesta del usuario:", user_response)
                
                with open(response_file, 'a', encoding='utf-8') as file:                     
                    file.write(f"Usuario: {user_response}\n")  # respuesta del usuario
                    file.write(f"\n=== Nueva interacción ({timestamp}) ===\n")
                    file.write(f"Asistente: {message_content}\n")   # respuesta del asistente
            else:
                print("No se recibió una respuesta del usuario")
                with open(response_file, 'a', encoding='utf-8') as file:
                    file.write(f"Asistente: {message_content}\n")
            
            return jsonify({
                "response": message_content,  # Ya no necesitamos str() aquí
                "status": "completed"
            })
    return jsonify({"response": "timeout"})  
  
if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8080)
